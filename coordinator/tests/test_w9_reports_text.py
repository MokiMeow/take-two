"""Resolution and presentation regressions at the persisted state/card boundary."""
from pathlib import Path

from coordinator.tests.test_w4_workflow import runtime, initial, change
from coordinator.tests.test_w8_cards import card, outcome
from coordinator.tests.test_w8_reports import extract, proposal, report


async def test_cannot_report_resolves_only_through_authority_record(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        await rt.loop.handle_outcome(outcome(card(rt, 'dev'), 'dev', 'cannot', note='Running 40 min late'))
        job = rt.loop.workflow['jobs'][-1]
        await extract(rt, job, target='dev', field='late_by', value='40')
        q = proposal(rt)
        assert not rt.ledger.snapshot_state()['changes'][0].get('resolution')
        assert not await rt.loop.handle_outcome(outcome(q, 'director', 'record'))
        assert not rt.ledger.snapshot_state()['changes'][0].get('resolution')
        assert await rt.loop.handle_outcome(outcome(proposal(rt), 'ad', 'record'))
        recorded, source = rt.ledger.snapshot_state()['changes'][:2]
        assert source['resolution'] == 'recorded'
        assert source['resolved_by_change'] == recorded['id']
        assert source['resolved_at'] == recorded['recorded_at']
        assert recorded['status'] == 'recorded' and not recorded.get('resolution')
    finally:
        await rt.close()


async def test_report_without_proposal_survives_unrelated_record(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        await report(rt, 'I have to leave sometime')
        await change(rt.loop)
        source = rt.ledger.snapshot_state()['changes'][1]
        assert source['status'] == 'pending_confirmation'
        assert not source.get('resolution') and not source.get('resolved_at')
    finally:
        await rt.close()


async def test_first_release_uses_human_labels_and_no_empty_or_previous_call(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        state = rt.ledger.snapshot_state()
        changes = state['releases'][0]['duty_changes']
        assert changes['maya'][0] == 'Scene 2: Courtyard, 15:25–15:35; Actor'
        assert changes['maya'][-1] == 'Call 15:25'
        assert changes['leela'][0] == 'Scene 1: Stairwell, 15:00–15:15; Camera / sound; kit sound recorder'
        prompt = card(rt, 'leela')['payload']['questions'][0]['prompt']
        assert 'Camera / sound; kit sound recorder' in prompt
        assert 'camera_sound' not in prompt and 'unconfirmed' not in prompt
        assert next(p for p in state['crew'] if p['id'] == 'maya')['since_confirmed'] == changes['maya']
        description = rt.loop.workflow['question']['payload']['questions'][0]['options'][0]['description']
        assert 'people: Dev, Leela' in description
        assert 'kit sound recorder' in description and 'sound_recorder' not in description
    finally:
        await rt.close()
