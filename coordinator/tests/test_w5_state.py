"""Crew-facing projection keeps identities separate from trusted display labels."""
from pathlib import Path

import pytest

from coordinator.tests.test_w4_workflow import runtime, initial, change


async def test_decision_change_release_and_roles_have_trusted_names(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        state = rt.ledger.snapshot_state()
        assert state['decision']['authority_name'] == 'Arun'
        assert state['decision']['answer']['answered_by_name'] == 'Arun'
        assert state['releases'][0]['publications'][0]['room_name'] == '#production'
        assert [p['role_label'] for p in state['crew']] == ['Actor', 'Actor', 'Camera / sound']
        await change(rt.loop)
        state = rt.ledger.snapshot_state()
        assert state['changes'][0]['reporter_name'] == 'Nila'
        assert any(t['text'].startswith('Nila (Producer):') for t in state['timeline'])
        assert not any('@switch-' in t['text'] for t in state['timeline'])
    finally:
        await rt.close()


@pytest.mark.parametrize('entity,target,field,value,expected', [
    ('person', 'maya', 'hard_stop', '18:00', '2026-11-06T18:00:00+05:30'),
    ('location', 'park', 'light_until', '18:20', '2026-11-06T18:20:00+05:30'),
    ('person', 'maya', 'hard_stop', '2026-11-06T12:30:00Z', '2026-11-06T18:00:00+05:30'),
])
async def test_time_change_exposes_checker_time_and_keeps_typed_value(tmp_path: Path,
        entity: str, target: str, field: str, value: str, expected: str) -> None:
    rt = runtime(tmp_path)
    try:
        response = await change(rt.loop, entity=entity, target=target, field=field,
            value=value, reporter='ad' if entity == 'person' else 'producer')
        assert response.status == 'recorded'
        c = rt.ledger.snapshot_state()['changes'][0]
        assert c['value'] == value
        assert c['at'] == expected
        assert c['recorded_at'] != expected
    finally:
        await rt.close()


async def test_malformed_worker_selects_sender_role_before_newest_job(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        rt.loop.worker_ids = {'script-supervisor': 'supervisor', 'first-ad': 'ad-worker'}
        await change(rt.loop)
        supervisor = rt.loop.workflow['jobs'][-1]
        # Sequential work means the Supervisor is already done when the AD is running.
        await rt.loop.handle_worker_reply(dict(job_id=supervisor['job_id'], script_rev=1,
            constraints_rev=2, must_keep=['Keep privacy']), sender_id='supervisor')
        ad = rt.loop.workflow['jobs'][-1]
        await rt.loop.handle_worker_reply('not JSON', sender_id='supervisor')
        assert ad['attempt'] == 0
        assert supervisor['attempt'] == 0
        await rt.loop.handle_worker_reply('not JSON', sender_id='ad-worker')
        assert ad['attempt'] == 1
        await rt.loop.handle_worker_reply('still not JSON', sender_id='ad-worker')
        assert ad['status'] == 'failed'
    finally:
        await rt.close()


async def test_role_selection_with_two_active_jobs_cannot_retry_another_worker(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        rt.loop.worker_ids = {'script-supervisor': 'supervisor', 'first-ad': 'ad-worker'}
        await change(rt.loop)
        with rt.ledger.transaction():
            state = rt.loop._state()
            rt.loop._job(state, 'first-ad', dict(scene_ids=['s3']))
            rt.loop._save(state)
        await rt.loop.handle_worker_reply('bad', sender_id='supervisor')
        assert [j['attempt'] for j in rt.loop.workflow['jobs']] == [1, 0]
    finally:
        await rt.close()
