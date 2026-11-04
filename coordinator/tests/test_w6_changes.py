"""W6 facts, scoped replans and release audience use the production transitions."""
from copy import deepcopy
from pathlib import Path

import pytest

from coordinator.checker import check_manifest
from coordinator.constraints import Constraints, Manifest
from coordinator.render_props import release_text
from coordinator.tests.test_w4_workflow import runtime, initial, change, reply, manifest


@pytest.mark.parametrize('entity,target,field,value,actor', [
    ('person','dev','late_by','40','ad'),
    ('person','dev','available','15:40','ad'),
    ('capability','sound_recorder','status','unavailable','ad'),
    ('capability','sound_recorder','status','unavailable','camera'),
    ('location','park','light_until','17:20','producer'),
    ('location','courtyard','window','14:00-16:30','producer'),
    ('scene','s1','overrun','25','ad'),
    ('scene','s1','overrun','25','script-human'),
])
async def test_authority_and_impostor(tmp_path: Path, entity: str, target: str,
                                     field: str, value: str, actor: str) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    rt.loop.authorities.update(capability_verification=['ad','camera'], overrun_confirmation=['ad','script-human'])
    args = dict(entity=entity,target=target,field=field,value=value)
    before = rt.loop.constraints.model_dump()
    denied = await change(rt.loop,**args,reporter='intruder')
    assert denied.status == 'pending_confirmation'
    assert rt.loop.constraints.model_dump() == before
    result = await change(rt.loop,**args,reporter=actor)
    assert result.status == 'recorded', result.reason
    await rt.close()


async def test_late_actor_holds_every_early_scene_and_preserves_later_work(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop,entity='person',target='dev',field='late_by',value='40',reporter='ad')
    assert rt.loop.workflow['unresolved'] == ['s1','s2']
    assert rt.ledger.snapshot_state()['scenes'][2]['validity'] == 'valid'
    assert rt.loop.constraints.people[1].available[0].start.isoformat() == '2026-11-06T15:40:00+05:30'
    await reply(rt.loop,must_keep=['Keep reviewed dialogue'])
    await reply(rt.loop,candidates=[dict(candidate_id='late',label='Shift early work',story_cost='Later calls',
        manifests=[manifest('s1','stairwell','15:40','15:55',2),manifest('s2','courtyard','16:05','16:15',2)])])
    assert rt.loop.workflow['question']
    assert rt.loop.workflow['question']['candidates'][0]['check']['result'] == 'pass'
    await rt.close()


async def test_kit_replacement_requires_reviewed_alternative_and_confirmation(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    rt.loop.authorities['capability_verification']=['ad']
    assert (await change(rt.loop,entity='capability',target='sound_recorder',field='status',value='unavailable',reporter='ad')).status == 'recorded'
    assert rt.loop.workflow['unresolved'] == ['s1','s2','s3']
    facts = rt.loop.constraints.model_dump(mode='json')
    m = manifest(revision=2)
    assert check_manifest(Manifest.model_validate(m),rt.loop.constraints).result == 'fail'
    m['capabilities'] = []
    assert check_manifest(Manifest.model_validate(m),rt.loop.constraints).result == 'fail'
    facts['scenes'][2]['capability_alternatives']={'sound_recorder':[['lav']]}
    facts['capabilities']['lav']='unknown'
    m['capabilities']=['lav']
    assert check_manifest(Manifest.model_validate(m),Constraints.model_validate(facts)).result == 'needs_verification'
    facts['capabilities']['lav']='confirmed'
    assert check_manifest(Manifest.model_validate(m),Constraints.model_validate(facts)).result == 'pass'
    await rt.close()


@pytest.mark.parametrize('field,value', [('light_until','17:20'),('window','14:00-16:30')])
async def test_light_and_window_rules_keep_interiors_usable(tmp_path: Path, field: str, value: str) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    assert (await change(rt.loop,target='park',field=field,value=value)).status == 'recorded'
    outdoor=manifest(location='park',revision=2)
    outdoor['requires_light']=True
    assert check_manifest(Manifest.model_validate(outdoor),rt.loop.constraints).result == 'fail'
    indoor=manifest(location='stairwell',revision=2)
    assert check_manifest(Manifest.model_validate(indoor),rt.loop.constraints).result == 'pass'
    await rt.close()


async def test_overrun_ripples_without_touching_distant_scene_and_cannot_shrink(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    rt.loop.authorities['overrun_confirmation']=['ad']
    result=await change(rt.loop,entity='scene',target='s1',field='overrun',value='25',reporter='ad')
    assert result.status=='recorded'
    assert rt.loop.workflow['unresolved']==['s1','s2']
    assert rt.ledger.snapshot_state()['scenes'][2]['validity']=='valid'
    m=manifest('s1','stairwell','15:00','15:15',2)
    assert check_manifest(Manifest.model_validate(m),rt.loop.constraints).result=='fail'
    m['end']='2026-11-06T15:40:00+05:30'
    assert check_manifest(Manifest.model_validate(m),rt.loop.constraints).result=='pass'
    await reply(rt.loop,must_keep=['Keep dialogue and travel time'])
    await reply(rt.loop,candidates=[dict(candidate_id='ripple',label='Move the promise',story_cost='Later meeting',
        manifests=[m,manifest('s2','courtyard','15:50','16:00',2)])])
    q=rt.loop.workflow['question']
    assert q
    assert await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='ripple'))
    release=rt.loop.workflow['releases']['r2']['envelope']
    assert rt.ledger.snapshot_state()['releases'][0]['acks']['expected']==['maya','dev','leela']
    text=release_text(release)
    assert 'moved' in text and '15:25–15:35 → 15:50–16:00' in text
    assert 'Maya 15:25 → 15:50' in text
    await rt.loop.publication_result('r2','production','sent')
    # Repeated total overrun reports anchor to the original observation, not r2.
    await change(rt.loop,entity='scene',target='s1',field='overrun',value='25',reporter='ad')
    assert rt.loop.constraints.scenes[0].overrun_end.isoformat()=='2026-11-06T15:15:00+05:30'
    await rt.close()


async def test_new_change_closes_question_and_replans_union(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    await reply(rt.loop,must_keep=['Keep confession private'])
    await reply(rt.loop,candidates=[dict(candidate_id='stairs',label='Stairs',story_cost='No sunset',
        manifest=manifest(location='stairwell',revision=2))])
    q=deepcopy(rt.loop.workflow['question'])
    await change(rt.loop,entity='person',target='dev',field='available',value='15:40',reporter='ad')
    assert rt.loop.workflow['unresolved']==['s1','s2','s3']
    assert rt.ledger.snapshot_state()['decision']['status']=='closed_outdated'
    assert not await rt.loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='stairs'))
    assert len(rt.ledger.snapshot_state()['releases'])==1
    await rt.close()
