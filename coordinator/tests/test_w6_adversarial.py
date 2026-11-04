"""Adverse bounds, restart replay, retained work and downstream constraints."""
from copy import deepcopy
from pathlib import Path

import pytest

from coordinator.checker import check_manifest
from coordinator.constraints import Constraints, Manifest
from coordinator.ui_models import ChangeCommand
from coordinator.tests.test_w4_workflow import runtime, initial, change, reply, manifest


@pytest.mark.parametrize('field,value', [('late_by','-1'),('late_by','1441'),('late_by','1.5'),
    ('available','25:99'),('overrun','-1'),('overrun','1441'),('overrun','2.5')])
async def test_invalid_delay_never_mutates_facts(tmp_path: Path, field: str, value: str) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    before=rt.loop.constraints.model_dump()
    result=await change(rt.loop,entity='scene' if field=='overrun' else 'person',target='s1' if field=='overrun' else 'dev',
        field=field,value=value,reporter='ad')
    assert result.status in ('rejected','pending_confirmation')
    assert rt.loop.constraints.model_dump()==before
    assert any(e['kind']=='message' and 'Change ' in e['payload']['body'] for e in rt.ledger.pending_effects())
    await rt.close()


async def test_overrun_replay_restart_is_total_and_cannot_release_twice(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    rt.loop.authorities['overrun_confirmation']=['ad']
    command=ChangeCommand(entity='scene',target='s1',field='overrun',value='25',reporter='ad')
    first=await rt.loop.handle_change(command,source='mattermost',source_message_id='overrun-1')
    await rt.close()
    rt=runtime(tmp_path)
    rt.loop.renderer=None
    rt.loop.authorities['overrun_confirmation']=['ad']
    assert (await rt.loop.handle_change(command,source='mattermost',source_message_id='overrun-1')).model_dump()==first.model_dump()
    assert rt.loop.constraints.constraints_rev==2
    await reply(rt.loop,must_keep=['Retain dialogue'])
    await reply(rt.loop,candidates=[dict(candidate_id='ripple',label='Shift after overrun',story_cost='Later calls',
        manifests=[manifest('s1','stairwell','15:00','15:40',2),manifest('s2','courtyard','15:40','15:50',2)])])
    q=rt.loop.workflow['question']
    outcome=dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='ripple')
    assert await rt.loop.handle_outcome(outcome)
    assert not await rt.loop.handle_outcome(outcome)
    await rt.close()
    rt=runtime(tmp_path)
    assert not await rt.loop.handle_outcome(outcome)
    assert [r['number'] for r in rt.ledger.snapshot_state()['releases']]==[2,1]
    assert rt.loop.constraints.scenes[0].overrun==25
    await rt.close()


async def test_overrun_checks_hard_stop_window_light_and_travel(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    rt.loop.authorities['overrun_confirmation']=['ad']
    await change(rt.loop,entity='scene',target='s1',field='overrun',value='25',reporter='ad')
    m=manifest('s1','stairwell','15:00','15:40',2)
    facts=rt.loop.constraints.model_dump(mode='json')
    facts['people'][1]['hard_stop']='2026-11-06T15:30:00+05:30'
    assert any('hard stop' in reason for reason in check_manifest(Manifest.model_validate(m),Constraints.model_validate(facts)).reasons)
    facts=rt.loop.constraints.model_dump(mode='json')
    stairs=next(p for p in facts['locations'] if p['id']=='stairwell')
    stairs['windows']=['2026-11-06T14:00:00+05:30/2026-11-06T15:30:00+05:30']
    assert any('permission window' in reason for reason in check_manifest(Manifest.model_validate(m),Constraints.model_validate(facts)).reasons)
    stairs['windows']=['2026-11-06T14:00:00+05:30/2026-11-06T20:00:00+05:30']
    stairs['light_until']='2026-11-06T15:30:00+05:30'
    m['requires_light']=True
    assert any('light ends' in reason for reason in check_manifest(Manifest.model_validate(m),Constraints.model_validate(facts)).reasons)
    facts=rt.loop.constraints.model_dump(mode='json')
    facts['travel_min']['stairwell->courtyard']=15
    rt.loop.constraints=Constraints.model_validate(facts)
    candidate=dict(manifests=[manifest('s1','stairwell','15:00','15:40',2),manifest('s2','courtyard','15:45','15:55',2)])
    assert any('travel time' in r for r in rt.loop._candidate_check(candidate,rt.ledger.snapshot_state()).reasons)
    await rt.close()


async def test_light_change_runs_delegate_check_decide_release_and_confirm(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop,field='light_until',value='17:20')
    assert rt.loop.workflow['unresolved']==['s3']
    assert all(s['validity']=='valid' for s in rt.ledger.snapshot_state()['scenes'][:2])
    await reply(rt.loop,must_keep=['Intelligible and confidential confession'])
    outside=manifest(revision=2)
    # A worker cannot evade trusted exterior light by omitting requires_light.
    assert outside.get('requires_light',False) is False
    await reply(rt.loop,candidates=[dict(candidate_id='dark',label='Rooftop after cutoff',story_cost='No light',manifest=outside),
        dict(candidate_id='inside',label='Interior confession',story_cost='No sunset',manifest=manifest(location='stairwell',revision=2))])
    q=rt.loop.workflow['question']
    assert [c['check']['result'] for c in q['candidates']]==['fail','pass']
    assert not any(o['id']=='dark' for o in q['payload']['questions'][0]['options'])
    assert await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='inside'))
    await rt.loop.publication_result('r2','production','sent')
    state=rt.ledger.snapshot_state()
    assert all(s['validity']=='valid' for s in state['scenes'])
    assert state['releases'][0]['acks']['expected']==['maya','dev','leela']
    assert not await rt.loop.confirm('intruder','r2')
    assert await rt.loop.confirm('maya','r2')
    assert state['releases'][0]['acks']['confirmed']==[]
    await rt.close()


async def test_held_scope_cannot_touch_valid_scene(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    before=deepcopy(rt.loop.workflow['plans']['s1'])
    await change(rt.loop)
    await reply(rt.loop,must_keep=['Keep confession'])
    job=rt.loop.workflow['jobs'][-1]
    payload=dict(job_id=job['job_id'],script_rev=1,constraints_rev=2,candidates=[dict(candidate_id='too-much',label='Unnecessary shift',story_cost='None',
        manifests=[manifest('s1','stairwell','15:10','15:25',2),manifest(location='stairwell',revision=2)])])
    assert not await rt.loop.handle_worker_reply(payload)
    assert job['attempt']==1
    assert not await rt.loop.handle_worker_reply(payload)
    assert job['status']=='failed'
    assert rt.loop.workflow['plans']['s1']==before
    await rt.close()
