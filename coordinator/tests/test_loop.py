"""Adversarial state-machine tests use SQLite and external effects stay queued."""
import json
from pathlib import Path
from datetime import datetime, timedelta

import pytest
import yaml

from coordinator.constraints import Constraints
from coordinator.loop import Loop
from coordinator.ui_models import ChangeCommand, State
from coordinator.ledger import Ledger

ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture
def loop(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.sqlite3')
    state = json.loads((ROOT / 'fixtures/ui-state/01-normal.json').read_text())
    with ledger.transaction():
        ledger.save_state(state)
    facts = Constraints.model_validate(yaml.safe_load((ROOT / 'fixtures/film/constraints-r1.yaml').read_text()))
    from coordinator.tests.w4_support import metadata as trusted_metadata
    metadata=trusted_metadata()
    result = Loop(ledger, None, facts, metadata=metadata, authorities={'creative': ['arun'], 'location_permission': ['producer'], 'availability_confirmation': ['first-ad-human']}, clock=lambda: datetime.fromisoformat('2026-11-06T14:00:00+05:30'))
    result.workflow['plans']={scene['id']:dict(scene_id=scene['id'],**scene['plan'],shots=['wide'],capabilities=['sound_recorder'],script_rev=1,constraints_rev=1,requires_light=False) for scene in state['scenes']}
    return result

async def change(loop, **kwargs):
    data = dict(entity='location', target='rooftop', field='permission', value='refused', reporter='producer')
    data.update(kwargs)
    return await loop.handle_change(ChangeCommand(**data), source_message_id=kwargs.get('source_message_id'))

async def propose(loop):
    await change(loop)
    job = loop.workflow['jobs'][-1]
    await loop.handle_worker_reply(dict(job_id=job['job_id'], script_rev=1, constraints_rev=2, must_keep=['confession is intelligible and confidential in the story'], preferences=['sunset']), sender_id=None)
    job = loop.workflow['jobs'][-1]
    manifest = dict(scene_id='s3',location='stairwell', start='2026-11-06T16:00:00+05:30', end='2026-11-06T17:15:00+05:30',setup_min=0,wrap_min=0,people=['maya','dev','leela'],shots=['wide'],capabilities=['sound_recorder'],script_rev=1,constraints_rev=2)
    await loop.handle_worker_reply(dict(job_id=job['job_id'],script_rev=1,constraints_rev=2,candidates=[dict(candidate_id='stairs',label='Stairwell',story_cost='Loses sunset',manifest=manifest)]),sender_id=None)
    return loop.workflow['question']

@pytest.mark.asyncio
async def test_new_change_holds_and_invalidates_pending_work(loop):
    question = await propose(loop)
    old_id = question['request_id']
    await change(loop, entity='person',target='maya',field='hard_stop',value='18:00',reporter='first-ad-human')
    state = loop.ledger.snapshot_state()
    assert state['revisions']['constraints'] == 3
    assert next(s for s in state['scenes'] if s['id']=='s3')['validity'] == 'held'
    assert loop.workflow['question'] is None
    assert old_id in loop.workflow['closed_questions']
    State.model_validate(state)

@pytest.mark.asyncio
async def test_unauthorized_answer_is_durable_and_replaced_without_release(loop):
    question = await propose(loop)
    outcome = dict(session_id=question['session_id'], request_id=question['request_id'], answered_by='intruder', candidate_id='stairs')
    await loop.handle_outcome(outcome)
    assert len(loop.ledger.snapshot_state()['releases']) == 1
    assert loop.workflow['question']['request_id'] != question['request_id']
    assert len(loop.workflow['outcomes']) == 1
    await loop.handle_outcome(outcome)
    assert len(loop.workflow['outcomes']) == 1

@pytest.mark.asyncio
async def test_authorized_answer_commits_exact_release_once(loop):
    question = await propose(loop)
    original = json.loads(json.dumps(question['payload']))
    outcome = dict(session_id=question['session_id'],request_id=question['request_id'],answered_by='arun',candidate_id='stairs',note='keep the confession private')
    await loop.handle_outcome(outcome)
    await loop.handle_outcome(outcome)
    state = loop.ledger.snapshot_state()
    assert len(state['releases']) == 2
    assert state['releases'][0]['status'] == 'approved'
    assert question['payload'] == original
    assert loop.workflow['releases']['r2']['envelope']['approved_candidate_hash'] == question['candidates'][0]['manifest_hash']
    assert state['releases'][0]['manifest_hash'] != question['candidates'][0]['manifest_hash']
    State.model_validate(state)

@pytest.mark.asyncio
async def test_expiry_never_approves_and_stale_answers_do_nothing(loop):
    question = await propose(loop)
    await loop.tick(datetime.fromisoformat(question['expires_at']) + timedelta(seconds=1))
    await loop.handle_outcome(dict(session_id=question['session_id'],request_id=question['request_id'],answered_by='arun',candidate_id='stairs'))
    assert len(loop.ledger.snapshot_state()['releases']) == 1
    assert loop.ledger.snapshot_state()['decision']['status'] == 'expired'

@pytest.mark.asyncio
async def test_untrusted_permission_report_does_not_mutate_fact(loop):
    result = await change(loop, value='confirmed',reporter='intruder')
    assert result.status == 'pending_confirmation'
    assert loop.constraints.constraints_rev == 1

@pytest.mark.asyncio
async def test_malformed_worker_reply_retries_once_then_visible_failure(loop):
    await change(loop)
    job = loop.workflow['jobs'][-1]
    await loop.handle_worker_reply({'job_id':job['job_id'],'script_rev':1,'constraints_rev':2},sender_id=None)
    assert job['attempt'] == 1
    await loop.tick(datetime.fromisoformat(job['retry_at']) + timedelta(seconds=1))
    await loop.handle_worker_reply({'job_id':job['job_id'],'script_rev':1,'constraints_rev':2},sender_id=None)
    assert job['status'] == 'failed'
    assert any(t['kind']=='error' for t in loop.ledger.snapshot_state()['timeline'])

@pytest.mark.asyncio
async def test_unknown_candidate_is_never_released(loop):
    question = await propose(loop)
    await loop.handle_outcome(dict(session_id=question['session_id'],request_id=question['request_id'],answered_by='arun',candidate_id='invented'))
    assert len(loop.ledger.snapshot_state()['releases']) == 1

@pytest.mark.asyncio
async def test_confirmation_requires_known_crew_and_current_published_release(loop):
    assert not await loop.confirm('stranger','r1')
    assert not await loop.confirm('maya','yes')
    assert await loop.confirm('maya','r1')
    question = await propose(loop)
    await loop.handle_outcome(dict(session_id=question['session_id'],request_id=question['request_id'],answered_by='arun',candidate_id='stairs'))
    assert not await loop.confirm('maya','r1')
    assert not await loop.confirm('maya','r2')

@pytest.mark.asyncio
async def test_unconfirmed_refusal_invalidates_pending_approval(loop):
    q = await propose(loop)
    await change(loop,target='stairwell',value='refused',reporter='stranger')
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='stairs'))
    assert len(loop.ledger.snapshot_state()['releases']) == 1

@pytest.mark.asyncio
async def test_native_outcome_uses_choice_identity_and_persists_real_question_payload(loop):
    q = await propose(loop)
    assert q['payload']['kind'] == 'questions'
    assert q['payload']['options'] == []
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],state='answered',kind='questions',answered_by='arun',answers=[{'questionId':'choice','selectedOptionIds':['stairs'],'customAnswer':None}]))
    assert len(loop.ledger.snapshot_state()['releases']) == 2

@pytest.mark.asyncio
async def test_safety_hold_requires_named_clearance_even_after_creative_approval(loop):
    q = await propose(loop)
    result = await change(loop,entity='scene',target='s3',field='safety',value='hold',reporter='anyone')
    assert result.status == 'recorded'
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='stairs'))
    assert len(loop.ledger.snapshot_state()['releases']) == 1

@pytest.mark.asyncio
async def test_restart_rejects_old_outcome_and_preserves_exact_question(loop):
    q = await propose(loop)
    restored = Loop(loop.ledger,None,loop.constraints,authorities=loop.authorities,clock=loop.clock,metadata=loop.metadata)
    assert restored.workflow['question']['payload'] == q['payload']
    await restored.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='stairs'))
    assert len(restored.ledger.snapshot_state()['releases']) == 2

@pytest.mark.asyncio
async def test_short_time_uses_existing_shoot_day_not_runtime_day(loop):
    loop.clock = lambda: datetime.fromisoformat('2026-11-04T14:00:00+05:30')
    await change(loop,entity='person',target='maya',field='hard_stop',value='18:00',reporter='first-ad-human')
    assert loop.constraints.people[0].hard_stop.isoformat() == '2026-11-06T18:00:00+05:30'

@pytest.mark.asyncio
async def test_invalid_json_retries_active_worker_instead_of_becoming_stale(loop):
    await change(loop)
    job = loop.workflow['jobs'][-1]
    await loop.handle_worker_reply('not json')
    assert job['attempt'] == 1
    await loop.handle_worker_reply('{}')
    assert job['status'] == 'failed'

@pytest.mark.asyncio
async def test_preview_completion_cannot_resurrect_old_candidate(loop):
    loop.renderer = object()
    await propose(loop)
    assert loop.workflow['question'] is None
    candidate = loop.workflow['candidates'][0]
    await change(loop,entity='person',target='maya',field='hard_stop',value='18:00',reporter='first-ad-human')
    assert not await loop.preview_result(candidate['candidate_id'],candidate['manifest_hash'],'/media/old.mp4','ready')
    assert loop.workflow['question'] is None

@pytest.mark.asyncio
async def test_rendered_question_waits_for_bound_previews_and_release_contains_all_scenes(loop):
    loop.renderer = object()
    await propose(loop)
    candidate = loop.workflow['candidates'][0]
    assert await loop.preview_result('stairs',candidate['manifest_hash'],'/media/stairs.mp4','ready')
    q = loop.workflow['question']
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='stairs'))
    effect = next(e for e in loop.ledger.pending_effects() if e['kind']=='release')
    assert [s['scene_id'] for s in effect['payload']['envelope']['manifest']['scenes']] == ['s1','s2','s3']
    assert effect['payload']['preview_url'] == '/media/stairs.mp4'

@pytest.mark.asyncio
async def test_duplicate_source_command_does_not_advance_revision(loop):
    command = ChangeCommand(entity='location',target='rooftop',field='permission',value='refused',reporter='producer')
    first = await loop.handle_change(command,source_message_id='m1')
    second = await loop.handle_change(command,source_message_id='m1')
    assert first.change_id == second.change_id
    assert loop.constraints.constraints_rev == 2

@pytest.mark.asyncio
async def test_candidate_overlapping_unchanged_scene_cannot_be_approved(loop):
    await change(loop)
    job = loop.workflow['jobs'][-1]
    await loop.handle_worker_reply(dict(job_id=job['job_id'],script_rev=1,constraints_rev=2,must_keep=['confession is intelligible and confidential in the story']))
    job = loop.workflow['jobs'][-1]
    manifest = dict(scene_id='s3',location='stairwell',start='2026-11-06T15:00:00+05:30',end='2026-11-06T15:20:00+05:30',setup_min=0,wrap_min=0,people=['dev'],shots=['wide'],capabilities=[],script_rev=1,constraints_rev=2)
    await loop.handle_worker_reply(dict(job_id=job['job_id'],script_rev=1,constraints_rev=2,candidates=[dict(candidate_id='overlap',label='Overlap',story_cost='',manifest=manifest)]))
    assert loop.workflow['candidates'][0]['check']['result'] == 'fail'
    assert loop.workflow['question'] is None

@pytest.mark.asyncio
async def test_wrong_scene_candidate_cannot_replace_a_held_scene(loop):
    await change(loop)
    job = loop.workflow['jobs'][-1]
    await loop.handle_worker_reply(dict(job_id=job['job_id'],script_rev=1,constraints_rev=2,must_keep=['confession is intelligible and confidential in the story']))
    job = loop.workflow['jobs'][-1]
    manifest = dict(scene_id='s1',location='stairwell',start='2026-11-06T16:00:00+05:30',end='2026-11-06T16:20:00+05:30',setup_min=0,wrap_min=0,people=['dev'],shots=['wide'],capabilities=[],script_rev=1,constraints_rev=2)
    await loop.handle_worker_reply(dict(job_id=job['job_id'],script_rev=1,constraints_rev=2,candidates=[dict(candidate_id='wrong',label='Wrong scene',story_cost='',manifest=manifest)]))
    assert loop.workflow['question'] is None
    assert job['attempt'] == 1

@pytest.mark.asyncio
async def test_native_custom_text_note_is_recorded(loop):
    q = await propose(loop)
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],state='answered',kind='questions',answered_by='arun',answers=[{'question_id':'choice','selected_option_ids':['stairs'],'custom_text':'Keep it private'}]))
    assert loop.ledger.snapshot_state()['decision']['answer']['note'] == 'Keep it private'

@pytest.mark.asyncio
async def test_failed_transaction_restores_live_revision(loop):
    original = loop.ledger.save_state
    def reject(state):
        raise RuntimeError('Controlled failed commit')
    loop.ledger.save_state = reject
    with pytest.raises(RuntimeError):
        await change(loop)
    loop.ledger.save_state = original
    assert loop.constraints.constraints_rev == 1
    assert loop.workflow['jobs'] == []
    assert loop.ledger.snapshot_state()['revisions']['constraints'] == 1

@pytest.mark.asyncio
async def test_general_producer_cannot_override_a_different_named_location_authority(loop):
    facts = loop.constraints.model_dump(mode='json')
    facts['locations'][0]['permission_authority']='location-contact'
    facts['locations'][0]['permission_confirmed_by']='location-contact'
    loop.constraints = Constraints.model_validate(facts)
    result = await change(loop,reporter='producer')
    assert result.status == 'pending_confirmation'

@pytest.mark.asyncio
async def test_neither_note_becomes_unverified_hard_rule_for_one_more_round(loop):
    q = await propose(loop)
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='neither',note='The door must remain visible'))
    assert loop.constraints.constraints_rev == 3
    assert 'The door must remain visible' in next(s for s in loop.constraints.scenes if s.id=='s3').hard
    assert loop.workflow['jobs'][-1]['role'] == 'script-supervisor'
    assert loop.workflow['decision_round'] == 2
    assert len(loop.ledger.snapshot_state()['releases']) == 1
    row=loop.ledger.connection.execute('SELECT status FROM questions WHERE id=?',(q['request_id'],)).fetchone()
    assert row['status']=='answered'

@pytest.mark.asyncio
async def test_second_neither_hands_off_without_another_agent_round(loop):
    q = await propose(loop)
    loop.workflow['decision_round']=2
    count = len(loop.workflow['jobs'])
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='neither',note='Different again'))
    assert len(loop.workflow['jobs']) == count
    assert any('by hand' in t['text'] for t in loop.ledger.snapshot_state()['timeline'])

@pytest.mark.asyncio
async def test_deadline_retry_waits_for_backoff_and_stops_after_one_retry(loop):
    await change(loop)
    job = loop.workflow['jobs'][-1]
    deadline = datetime.fromisoformat(job['deadline'])
    await loop.tick(deadline + timedelta(seconds=1))
    assert datetime.fromisoformat(job['retry_at']) > deadline
    await loop.tick(datetime.fromisoformat(job['retry_at']) + timedelta(seconds=1))
    await loop.tick(datetime.fromisoformat(job['deadline']) + timedelta(seconds=1))
    assert job['status'] == 'failed'
    assert len([e for e in loop.ledger.pending_effects() if e['kind']=='role_message']) == 2

@pytest.mark.asyncio
@pytest.mark.parametrize('settled_status', ['published', 'superseded'])
async def test_publication_callback_replay_preserves_progress_and_adds_no_hold(loop, settled_status):
    q = await propose(loop)
    await loop.handle_outcome(dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='arun',candidate_id='stairs'))
    await loop.publication_result('r2','#crew','sent')
    await loop.publication_result('r2','#day-1','sent')
    await change(loop,entity='person',target='maya',field='hard_stop',value='18:00',reporter='first-ad-human')
    state = loop.ledger.snapshot_state()
    state['releases'][0]['status']=settled_status
    with loop.ledger.transaction():
        loop.ledger.save_state(state)
    timeline = loop.ledger.snapshot_state()['timeline']
    effects = len(loop.ledger.pending_effects())
    await loop.publication_result('r2','#crew','sent')
    state = loop.ledger.snapshot_state()
    assert state['releases'][0]['status'] == settled_status
    assert state['timeline'] == timeline
    assert len(loop.ledger.pending_effects()) == effects
