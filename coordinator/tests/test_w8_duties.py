"""Duty audiences must follow what each person actually confirmed."""
from pathlib import Path

from coordinator.tests.test_w4_workflow import runtime, initial, change, reply, manifest


async def release_stairs(rt: object, *, start: str = '16:45') -> None:
    loop = rt.loop
    await change(loop)
    await reply(loop, must_keep=['Keep dialogue'])
    await reply(loop, candidates=[dict(candidate_id='stairs', label='Stairs', story_cost='No sunset',
        manifest=manifest(location='stairwell', start=start, end='18:00', revision=loop.constraints.constraints_rev))])
    q = loop.workflow['question']
    assert await loop.handle_outcome(dict(session_id=q['session_id'], request_id=q['request_id'],
        answered_by='director', candidate_id='stairs'))
    await loop.publication_result('r2', 'production', 'sent')


async def test_location_same_call_needs_all_scene_people(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    for person in ('maya', 'dev', 'leela'):
        assert await rt.loop.confirm(person, 'r1')
    await release_stairs(rt)
    r = rt.ledger.snapshot_state()['releases'][0]
    assert r['acks']['expected'] == ['maya', 'dev', 'leela']
    assert 'Scene 3: Rooftop → Stairwell' in r['duty_changes']['maya']
    assert not any(line.startswith('Call ') for line in r['duty_changes']['maya'])
    await rt.close()


async def test_kit_change_only_sound_owner_needs_confirmation(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    for person in ('maya', 'dev', 'leela'):
        await rt.loop.confirm(person, 'r1')
    rt.loop.authorities['capability_verification'] = ['ad']
    await change(rt.loop, entity='capability', target='sound_recorder', field='status', value='unavailable', reporter='ad')
    await reply(rt.loop, must_keep=['Keep audio'])
    rows = [manifest('s1', 'stairwell', '15:00', '15:15', 2),
        manifest('s2', 'courtyard', '15:25', '15:35', 2), manifest(revision=2)]
    for row in rows:
        row['capabilities'] = ['lav']
    await reply(rt.loop, candidates=[dict(candidate_id='lav', label='Lav', story_cost='Same schedule', manifests=rows)])
    q = rt.loop.workflow['question']
    assert await rt.loop.handle_outcome(dict(session_id=q['session_id'], request_id=q['request_id'], answered_by='director', candidate_id='lav'))
    r = rt.ledger.snapshot_state()['releases'][0]
    assert r['acks']['expected'] == ['leela']
    assert 'Scene 1: kit sound recorder → lav mic' in r['duty_changes']['leela']
    assert not any(line.startswith('Call ') for line in r['duty_changes']['leela'])
    await rt.close()


async def test_since_confirmed_uses_personal_nonlatest_baseline(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    for person in ('maya', 'dev', 'leela'):
        await rt.loop.confirm(person, 'r1')
    await release_stairs(rt)
    await rt.loop.confirm('dev', 'r2')
    # Maya misses r2. A later release only changes audio: her r1 location
    # remains outstanding, while Dev has no new duties.
    rt.loop.authorities['capability_verification'] = ['ad']
    await change(rt.loop, entity='capability', target='sound_recorder', field='status', value='unavailable', reporter='ad')
    await reply(rt.loop, must_keep=['Keep audio'])
    rows = [dict(m, constraints_rev=3, capabilities=['lav']) for m in rt.loop.workflow['plans'].values()]
    await reply(rt.loop, candidates=[dict(candidate_id='lav', label='Lav', story_cost='Same schedule', manifests=rows)])
    q = rt.loop.workflow['question']
    assert await rt.loop.handle_outcome(dict(session_id=q['session_id'], request_id=q['request_id'], answered_by='director', candidate_id='lav'))
    await rt.loop.publication_result('r3', 'production', 'sent')
    state = rt.ledger.snapshot_state()
    assert state['releases'][0]['acks']['expected'] == ['maya', 'leela']
    maya = next(p for p in state['crew'] if p['id'] == 'maya')
    dev = next(p for p in state['crew'] if p['id'] == 'dev')
    assert 'Scene 3: Rooftop → Stairwell' in maya['since_confirmed']
    assert dev['since_confirmed'] == []
    await rt.loop.confirm('maya', 'r3')
    assert next(p for p in rt.ledger.snapshot_state()['crew'] if p['id'] == 'maya')['since_confirmed'] == []
    await rt.close()
