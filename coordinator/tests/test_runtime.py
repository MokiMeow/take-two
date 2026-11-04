from pathlib import Path

import pytest

from coordinator.config import Settings
from coordinator.runtime import Runtime, initial_state
from coordinator.ui_models import State
from coordinator.ui_models import ChangeCommand
from coordinator.switch_models import Identity, SwitchFrame


def test_initial_runtime_does_not_claim_fixture_approvals():
    state = initial_state()
    State.model_validate(state)
    assert state['releases'] == []
    assert all(scene['validity'] == 'held' for scene in state['scenes'])
    assert not any(member.get('acked_release') for member in state['crew'])


@pytest.mark.asyncio
async def test_unconfigured_runtime_exposes_failure_without_fake_switch(tmp_path):
    settings = Settings(_env_file=None, take_two_db=tmp_path/'ledger.sqlite', take_two_identity=tmp_path/'identity.json')
    runtime = Runtime(settings)
    await runtime.start()
    assert any(item['kind'] == 'error' and 'registration key' in item['text'] for item in runtime.ledger.snapshot_state()['timeline'])
    assert not settings.take_two_identity.exists()
    await runtime.close()


def runtime_for(tmp_path, **kwargs):
    runtime = Runtime(Settings(_env_file=None, take_two_db=tmp_path/'ledger.sqlite',
        take_two_identity=tmp_path/'identity.json', **kwargs))
    runtime.client._identity = Identity(agent_id='coordinator', api_key='test-only-secret')
    runtime.loop.coordinator_id = 'coordinator'
    return runtime


@pytest.mark.asyncio
async def test_ui_reporter_cannot_impersonate_permission_authority(tmp_path):
    runtime = runtime_for(tmp_path, take_two_producer_id='producer')
    response = await runtime.handle_ui_change(ChangeCommand(entity='location', target='rooftop',
        field='permission', value='confirmed', reporter='producer'))
    assert response['status'] == 'pending_confirmation'
    assert runtime.loop.constraints.constraints_rev == 1
    assert runtime.ledger.snapshot_state()['changes'][0]['source'] == 'control_room'
    await runtime.close()


@pytest.mark.asyncio
async def test_nullable_kind_worker_routes_once_and_cursor_commits(tmp_path):
    runtime = runtime_for(tmp_path, take_two_supervisor_sender_id='@worker:localhost')
    received = []
    async def receive(body, *, sender_id):
        received.append((body, sender_id))
        with runtime.ledger.transaction():
            runtime.ledger.set_meta('received', True)
    runtime.loop.handle_worker_reply = receive
    frame = SwitchFrame(event='message', id=12, data=dict(room_id='production', payload=dict(
        sender='@worker:localhost', sender_kind=None, sender_name='supervisor', body='bad JSON', message_id='m1')))
    await runtime.accept_frame(frame)
    await runtime.accept_frame(frame)
    assert received == [('bad JSON', '@worker:localhost')]
    assert runtime.ledger.get_meta('event_position') == {'s': 12}
    await runtime.close()


@pytest.mark.asyncio
async def test_long_chat_is_pending_and_oversized_chat_is_quarantined(tmp_path):
    runtime = runtime_for(tmp_path)
    for sequence, body in ((1, 'a'*5000), (2, 'a'*9000)):
        await runtime.accept_frame(SwitchFrame(event='message', id=sequence, data=dict(room_id='crew',
            payload=dict(sender='maya', sender_kind=None, body=body, message_id=f'm{sequence}'))))
    state = runtime.ledger.snapshot_state()
    assert len(state['changes']) == 1
    assert len(state['changes'][0]['value']) == 512
    assert any('quarantined' in item['text'] for item in state['timeline'])
    assert runtime.ledger.get_meta('event_position') == {'s': 2}
    await runtime.close()


@pytest.mark.asyncio
async def test_reconciliation_blocks_dispatch_readiness(tmp_path):
    import asyncio
    runtime = runtime_for(tmp_path, switch_production_room_id='production')
    blocked = asyncio.Event()
    entered = asyncio.Event()
    async def connect(room_id):
        return {'documents': []}
    async def reconcile(room):
        entered.set()
        await blocked.wait()
    async def operation(name, arguments=None):
        assert name=='list_bridges'
        return []
    async def outcomes():
        return []
    runtime.client.connect_to_production = connect
    runtime.client.get_outcomes = outcomes
    runtime.client.operation=operation
    runtime.reconcile_documents = reconcile
    async def head():
        return {'s':0}
    async def rooms():
        return []
    runtime.client.head_position=head
    runtime.client.member_rooms=rooms
    task = asyncio.create_task(runtime.connected())
    await entered.wait()
    assert not runtime.ready
    assert not runtime.dispatcher.enabled()
    blocked.set()
    await task
    assert runtime.ready
    await runtime.close()


@pytest.mark.asyncio
async def test_stale_release_mention_gets_visible_current_release_correction(tmp_path):
    import json
    runtime = runtime_for(tmp_path)
    fixture = Path(__file__).resolve().parents[2]/'fixtures/ui-state/05-released.json'
    with runtime.ledger.transaction():
        runtime.ledger.save_state(json.loads(fixture.read_text()))
    await runtime.accept_frame(SwitchFrame(event='message', id=1, data=dict(room_id='crew',
        payload=dict(sender='maya', sender_kind=None, body='OK see you on r1', message_id='old-plan'))))
    effect = runtime.ledger.pending_effects()[0]
    assert 'r2' in effect['payload']['body']
    assert effect['payload']['room_id'] == 'crew'
    assert runtime.ledger.snapshot_state()['timeline'][0]['kind'] == 'stale_reply'
    await runtime.close()


@pytest.mark.asyncio
async def test_native_structured_command_uses_authenticated_sender(tmp_path):
    runtime = runtime_for(tmp_path, take_two_producer_id='@producer:localhost')
    await runtime.accept_frame(SwitchFrame(event='command', id=2, data=dict(room_id='production',
        payload=dict(command='change', args='location rooftop permission refused',
            user_id='@producer:localhost', user_name='Producer'))))
    assert runtime.loop.constraints.constraints_rev == 2
    assert runtime.ledger.snapshot_state()['changes'][0]['reporter'] == '@producer:localhost'
    await runtime.close()
