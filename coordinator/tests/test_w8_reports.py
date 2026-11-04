"""Model extraction proposes facts; only authenticated authorities record them."""
from pathlib import Path
from typing import Any

import pytest

from coordinator.runtime import ChatEvent, ChatPayload
from coordinator.tests.test_w4_workflow import runtime, initial
from coordinator.tests.test_w8_cards import outcome


async def report(rt: Any, text: str = 'I have to leave at 6') -> dict:
    await rt.pending_report(ChatEvent(room_id='production', payload=ChatPayload(
        sender='maya', body=text, message_id='report-1')), 'mattermost')
    jobs = [j for j in rt.loop.workflow['jobs'] if j['context'].get('task') == 'extract_change']
    assert len(jobs) == 1
    job = jobs[0]
    assert job['role'] == 'first-ad'
    assert job['context']['sender_id'] == 'maya'
    assert job['context']['production_date'] == '2026-11-06'
    return job


async def extract(rt: Any, job: dict, **fields: Any) -> bool:
    value = dict(entity='person', target='maya', field='hard_stop', value='18:00', confidence=0.98)
    value.update(fields)
    return await rt.loop.handle_worker_reply(dict(job_id=job['job_id'], script_rev=1,
        constraints_rev=rt.loop.constraints.constraints_rev, **value))


def proposal(rt: Any) -> dict:
    return next(q for q in rt.loop.workflow.get('cards', {}).values() if q['kind'] == 'proposal' and q['status'] == 'open')


async def test_report_record_card_uses_authority_change_path_once_across_restart(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    job = await report(rt)
    assert await extract(rt, job)
    q = proposal(rt)
    assert "Record Maya: hard stop 18:00?" in q['prompt']
    assert q['authorized_answerers'] == ['ad']
    assert rt.loop.constraints.constraints_rev == 1
    assert await rt.loop.handle_outcome(outcome(q, 'ad', 'record'))
    assert rt.loop.constraints.people[0].hard_stop.hour == 18
    assert rt.loop.constraints.constraints_rev == 2
    assert rt.ledger.snapshot_state()['changes'][0]['reporter'] == 'ad'
    assert rt.ledger.snapshot_state()['changes'][1]['resolution'] == 'recorded'
    recorded, source = rt.ledger.snapshot_state()['changes'][:2]
    assert source['status'] == 'pending_confirmation'
    assert source['resolved_by_change'] == recorded['id']
    assert source['resolved_at'] == recorded['recorded_at']
    resolved = dict(source)
    await rt.close()
    rt = runtime(tmp_path)
    assert not await rt.loop.handle_outcome(outcome(q, 'ad', 'record'))
    assert rt.loop.constraints.constraints_rev == 2
    assert rt.ledger.snapshot_state()['changes'][1] == resolved
    await rt.close()


@pytest.mark.parametrize('fields,text', [
    (dict(target='nobody'), 'I have to leave at 6'),
    (dict(field='salary'), 'I have to leave at 6'),
    (dict(entity='capability', target='unknown', field='status', value='unavailable'), 'recorder battery dead'),
    (dict(confidence=0.5), 'I have to leave at 6'),
    (dict(value='18:00'), 'I have to leave sometime'),
    (dict(value='18:00'), 'I might leave at 5 or 6'),
    (dict(value='17:00'), 'I have to leave at 6'),
    (dict(value='18:00'), 'I have to leave at 6-7 pm'),
    (dict(value='18:30'), 'I have to leave at 6:30:45 pm'),
    (dict(value='18:00'), 'I have to leave at 6 pm UTC'),
    (dict(value='18:00'), 'I have to leave on November 7 at 6 pm'),
    (dict(entity='location', target='rooftop', field='window', value='14:00-16:00'), 'Rooftop permission available 14:00-17:00'),
])
async def test_unknown_low_confidence_or_ambiguous_stays_pending(tmp_path: Path, fields: dict, text: str) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    job = await report(rt, text)
    await extract(rt, job, **fields)
    assert not [q for q in rt.loop.workflow.get('cards', {}).values() if q['kind'] == 'proposal']
    assert rt.loop.constraints.constraints_rev == 1
    assert rt.ledger.snapshot_state()['changes'][0]['status'] == 'pending_confirmation'
    await rt.close()


async def test_ignore_and_wrong_authority_never_record(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await extract(rt, await report(rt))
    q = proposal(rt)
    assert not await rt.loop.handle_outcome(outcome(q, 'director', 'record'))
    q = proposal(rt)
    assert await rt.loop.handle_outcome(outcome(q, 'ad', 'ignore'))
    source = rt.ledger.snapshot_state()['changes'][0]
    assert source['resolution'] == 'ignored'
    assert source['resolved_at'].endswith('+05:30')
    assert not source.get('resolved_by_change')
    assert rt.loop.constraints.constraints_rev == 1
    await rt.close()


async def test_bad_extraction_schema_retries_once_then_visible_failure(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    job = await report(rt)
    for _ in range(2):
        assert not await rt.loop.handle_worker_reply(dict(job_id=job['job_id'], script_rev=1,
            constraints_rev=1, entity='person', target='maya', field='hard_stop', value='18:00',
            confidence=0.99, reporter='ad'))
    assert job['status'] == 'failed' and job['attempt'] == 1
    assert any(t['kind'] == 'error' and 'one retry' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
    assert any(e['kind'] == 'message' and 'failed after one retry' in e['payload']['body'] for e in rt.ledger.pending_effects())
    assert rt.loop.constraints.constraints_rev == 1
    await rt.close()


async def test_proposal_stale_after_revision_change_cannot_record(tmp_path: Path) -> None:
    from coordinator.tests.test_w4_workflow import change
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await extract(rt, await report(rt))
    q = proposal(rt)
    await change(rt.loop)
    assert not await rt.loop.handle_outcome(outcome(q, 'ad', 'record'))
    assert rt.loop.constraints.people[0].hard_stop.hour == 20
    assert rt.loop.constraints.constraints_rev == 2
    await rt.close()


async def test_unknown_availability_cannot_crash_time_extraction(tmp_path: Path) -> None:
    from coordinator.constraints import Constraints
    rt = runtime(tmp_path)
    await initial(rt.loop)
    data = rt.loop.constraints.model_dump(mode='json')
    data['people'][0]['available'] = 'unknown'
    rt.loop.constraints = Constraints.model_validate(data)
    await extract(rt, await report(rt))
    assert rt.ledger.snapshot_state()['changes'][0]['status'] == 'pending_confirmation'
    assert not [q for q in rt.loop.workflow.get('cards', {}).values() if q['kind'] == 'proposal']
    await rt.close()


async def test_truncated_source_cannot_hide_ambiguity_and_open_proposal(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    text = 'I have to leave at 6 ' + 'context ' * 80 + 'or 7'
    await rt.pending_report(ChatEvent(room_id='production', payload=ChatPayload(
        sender='maya', body=text, message_id='long-report')), 'mattermost')
    assert not any(j['context'].get('task') == 'extract_change' for j in rt.loop.workflow['jobs'])
    assert rt.ledger.snapshot_state()['changes'][0]['status'] == 'pending_confirmation'
    await rt.close()


async def test_bad_json_with_multiple_worker_jobs_gets_bounded_visible_retries(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    rt.loop.worker_ids = {'first-ad': 'ad-worker'}
    for number in range(2):
        await rt.pending_report(ChatEvent(room_id='production', payload=ChatPayload(
            sender='maya', body='I have to leave at 6', message_id=f'concurrent-{number}')), 'mattermost')
    jobs = [j for j in rt.loop.workflow['jobs'] if j['context'].get('task') == 'extract_change']
    for _ in range(2):
        assert not await rt.loop.handle_worker_reply('bad JSON', sender_id='ad-worker')
    assert all(j['attempt'] == 1 and j['status'] == 'failed' for j in jobs)
    assert any(e['kind'] == 'message' and 'failed after one retry' in e['payload']['body'] for e in rt.ledger.pending_effects())
    await rt.close()


async def test_dismissed_preplan_report_does_not_block_initial_planning(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await extract(rt, await report(rt))
    assert await rt.loop.handle_outcome(outcome(proposal(rt), 'ad', 'ignore'))
    await initial(rt.loop)
    assert rt.ledger.snapshot_state()['releases'][0]['status'] == 'published'
    await rt.close()
