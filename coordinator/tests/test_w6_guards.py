"""Crew identity and question bounds matter during a busy shoot day."""
from pathlib import Path

from coordinator.commands import parse_command
from coordinator.tests.test_w4_workflow import runtime, initial, change, options
from coordinator.constraints import Constraints
from coordinator.ripple import ripple_holds
from coordinator.render_props import call_times


def test_kit_shorthand_normalizes_to_authority_checked_status() -> None:
    parsed=parse_command('/change capability sound_recorder unavailable','camera','kit-1')
    assert parsed.command and parsed.command.field=='status' and parsed.command.value=='unavailable'


async def test_held_release_cannot_be_confirmed(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop,entity='person',target='dev',field='available',value='15:40',reporter='ad')
    assert not await rt.loop.confirm('dev','r1')
    assert rt.ledger.snapshot_state()['releases'][0]['acks']['confirmed']==[]
    await rt.close()


async def test_unauthorized_replacement_is_bounded_to_one_and_original_deadline(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    q=await options(rt.loop)
    expiry=q['expires_at']
    for _ in range(3):
        q=rt.loop.workflow['question']
        assert not await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='intruder',candidate_id='stairs'))
    replacement=rt.loop.workflow['question']
    assert replacement['expires_at']==expiry
    assert replacement['status']=='rejected_unauthorized'
    assert len(rt.ledger.snapshot_state()['releases'])==1
    assert any('Unauthorized' in e['payload'].get('body','') for e in rt.ledger.pending_effects() if e['kind']=='message')
    await rt.close()


def test_ripple_uses_adjacent_travel_not_a_skipped_route() -> None:
    plans={str(i):dict(scene_id=str(i),location=loc,people=['dev'],setup_min=0,wrap_min=0,
        start=f'2026-11-06T09:{minute:02}:00+05:30',end=f'2026-11-06T09:{minute+10:02}:00+05:30')
        for i,loc,minute in ((1,'a',0),(2,'b',20),(3,'c',40))}
    facts=Constraints(timezone='Asia/Kolkata',travel_min={'a->b':10,'b->c':10,'a->c':120})
    assert ripple_holds(plans,facts)==set()


def test_equal_call_instants_do_not_force_confirmation_for_offset_spelling() -> None:
    local=dict(scene_id='s1',start='2026-11-06T15:00:00+05:30',setup_min=15,people=['dev'])
    utc=dict(local,start='2026-11-06T09:30:00+00:00')
    assert call_times(dict(scenes=[utc]))==call_times(dict(scenes=[local]))
