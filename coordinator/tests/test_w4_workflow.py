from pathlib import Path
from typing import Any
from copy import deepcopy
from datetime import datetime, timedelta
import json

import pytest

from coordinator.runtime import Runtime
from coordinator.config import Settings
from coordinator.ui_models import ChangeCommand


def runtime(tmp_path: Path) -> Runtime:
    return Runtime(Settings(_env_file=None, take_two_db=tmp_path/'ledger.sqlite',
        take_two_identity=tmp_path/'identity.json', take_two_director_id='director',
        take_two_producer_id='producer', take_two_ad_id='ad', switch_crew_room_ids='production',
        switch_production_room_id='production'))


def manifest(scene: str='s3', location: str='rooftop', start: str='16:45', end: str='18:15', revision: int=1) -> dict[str,Any]:
    return dict(scene_id=scene, location=location, start=f'2026-11-06T{start}:00+05:30',
        end=f'2026-11-06T{end}:00+05:30', setup_min=0, wrap_min=0,
        people=['dev','leela'] if scene=='s1' else ['maya','dev','leela'],
        shots=['wide','two-shot'], capabilities=['sound_recorder'], script_rev=1, constraints_rev=revision)


async def reply(loop: Any, **fields: Any) -> None:
    job = loop.workflow['jobs'][-1]
    data = dict(job_id=job['job_id'], script_rev=1, constraints_rev=loop.constraints.constraints_rev, **fields)
    assert await loop.handle_worker_reply('@take-two-coordinator Here is my answer:\n```json\n'+json.dumps(data)+'\n```')


async def initial(loop: Any) -> None:
    loop.renderer = None
    assert await loop.request_plan('day-1', 'director', 'plan-1')
    await reply(loop, must_keep=['Keep the reviewed story requirements'])
    await reply(loop, candidates=[dict(candidate_id='initial', label='Initial three-scene schedule', story_cost='Reviewed script',
        manifests=[manifest('s1','stairwell','15:00','15:15'),manifest('s2','courtyard','15:25','15:35'),manifest()])])
    q = loop.workflow['question']
    assert q
    assert await loop.handle_outcome(dict(session_id=q['session_id'], request_id=q['request_id'],
        answered_by='director', candidate_id='initial'))
    await loop.publication_result('r1','production','sent')


async def change(loop: Any, **kw: Any) -> Any:
    args = dict(entity='location', target='rooftop', field='permission', value='refused', reporter='producer')
    args.update(kw)
    return await loop.handle_change(ChangeCommand(**args), source='mattermost')


async def options(loop: Any, revision: int=2) -> dict[str,Any] | None:
    await reply(loop, must_keep=['Keep the confession private'])
    await reply(loop, candidates=[dict(candidate_id='stairs',label='Stairwell, reduced coverage',story_cost='Loses sunset',
        manifest=manifest(location='stairwell', start='16:30', end='17:15',revision=revision))])
    return loop.workflow['question']


async def test_one_initial_approval_commits_complete_r1_and_repeat_command_is_deduped(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    assert not await rt.loop.request_plan('day-1','intruder','bad')
    await initial(rt.loop)
    state = rt.ledger.snapshot_state()
    assert len(state['releases']) == 1
    assert all(s['validity']=='valid' for s in state['scenes'])
    envelope = rt.loop.workflow['releases']['r1']['envelope']
    assert len(envelope['manifest']['scenes']) == 3
    assert all('shots' in s and 'capabilities' in s for s in envelope['manifest']['scenes'])
    assert not await rt.loop.request_plan('day-1','director','plan-1')
    await rt.close()


async def test_hard_stop_does_not_hold_scene2_and_unresolved_scope_survives(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    await options(rt.loop)
    await change(rt.loop, entity='person',target='maya',field='hard_stop',value='18:00',reporter='ad')
    scenes = rt.ledger.snapshot_state()['scenes']
    assert scenes[1]['validity']=='valid'
    assert rt.loop.workflow['jobs'][-1]['context']['scene_ids']==['s3']
    await change(rt.loop,target='stairwell')
    assert set(rt.loop.workflow['jobs'][-1]['context']['scene_ids'])=={'s1','s3'}
    await rt.close()


async def test_trusted_cast_and_kit_cannot_be_omitted(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    await reply(rt.loop,must_keep=['Keep confession private'])
    m = manifest(location='stairwell', revision=2)
    m.update(people=['dev'],capabilities=[])
    await reply(rt.loop,candidates=[dict(candidate_id='omit',label='Omitted cast',story_cost='None',manifest=m)])
    c = rt.loop.workflow['candidates'][0]
    assert c['check']['result']=='fail'
    assert any('maya' in r.lower() for r in c['check']['reasons'])
    assert any('sound_recorder' in r for r in c['check']['reasons'])
    assert any(e['kind']=='message' and 'No feasible' in e['payload']['body'] for e in rt.ledger.pending_effects())
    await rt.close()


async def test_timely_server_answer_after_local_expiry_is_honoured(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    q = await options(rt.loop)
    expiry = datetime.fromisoformat(q['expires_at'])
    await rt.loop.tick(expiry+timedelta(seconds=1))
    rt.loop.clock = lambda: expiry+timedelta(seconds=2)
    assert await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],
        state='answered',answered_at=(expiry-timedelta(seconds=1)).isoformat(),answered_by='director',candidate_id='stairs'))
    assert rt.ledger.snapshot_state()['releases'][0]['release_id']=='r2'
    assert 'Keep the confession private' in rt.ledger.snapshot_state()['decision']['must_keep']
    await rt.close()


async def test_browser_refusal_holds_and_cannot_confirm_or_clear(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    result = await rt.handle_ui_change(ChangeCommand(entity='location',target='rooftop',field='permission',value='refused',reporter='producer'))
    assert result['status']=='pending_confirmation'
    assert rt.loop.constraints.locations[0].permission=='unknown'
    assert rt.ledger.snapshot_state()['scenes'][2]['validity']=='held'
    await rt.handle_ui_change(ChangeCommand(entity='location',target='rooftop',field='permission',value='confirmed',reporter='producer'))
    assert rt.loop.constraints.locations[0].permission=='unknown'
    await rt.handle_ui_change(ChangeCommand(entity='scene',target='s3',field='safety',value='hold',reporter='director'))
    await rt.handle_ui_change(ChangeCommand(entity='scene',target='s3',field='safety',value='clear',reporter='director'))
    assert 's3' in rt.loop.workflow['holds']
    await rt.close()


async def test_expired_server_outcome_never_reissues_and_is_visible(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    q=await options(rt.loop)
    rt.loop.clock=lambda:datetime.fromisoformat(q['expires_at'])+timedelta(seconds=1)
    assert not await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],state='expired'))
    assert rt.loop.workflow['question']['request_id']==q['request_id']
    assert any(t['kind']=='decision' and 'expired' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
    assert any(e['kind']=='message' and 'expired' in e['payload']['body'] for e in rt.ledger.pending_effects())
    await rt.close()


async def test_unrelated_safety_hold_is_preserved_in_release(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop,entity='scene',target='s1',field='safety',value='hold',reporter='anyone')
    await change(rt.loop)
    await reply(rt.loop,must_keep=['Keep confession private'])
    await reply(rt.loop,candidates=[dict(candidate_id='stairs',label='Stairwell',story_cost='Loses sunset',
        manifest=manifest(location='stairwell',revision=3,start='16:30',end='17:15'))])
    q=rt.loop.workflow['question']
    assert await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='stairs'))
    assert rt.loop.workflow['releases']['r2']['envelope']['manifest']['scenes'][0]['validity']=='held'
    assert 's1' in rt.loop.workflow['holds']
    await rt.close()


async def test_answered_question_stays_answered_in_ledger_after_change(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    q=rt.loop.workflow['question']
    row=rt.ledger.connection.execute('SELECT status FROM questions WHERE id=?',(q['request_id'],)).fetchone()
    assert row['status']=='answered'
    await change(rt.loop)
    row=rt.ledger.connection.execute('SELECT status FROM questions WHERE id=?',(q['request_id'],)).fetchone()
    assert row['status']=='answered'
    assert not any(e['kind']=='close_question' and e['payload']['request_id']==q['request_id'] for e in rt.ledger.pending_effects())
    await rt.close()
