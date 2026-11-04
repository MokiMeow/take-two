from pathlib import Path
from typing import Any
import json
from datetime import datetime

import pytest

from coordinator.switch_models import SwitchFrame, Identity
from coordinator.tests.test_w4_workflow import runtime, initial, change, options


async def test_offline_refusal_precedes_owed_answer_and_dispatch(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    q = await options(rt.loop)
    rt.client._identity = Identity(agent_id='coordinator',api_key='test-secret')
    rt.loop.coordinator_id='coordinator'
    async def connect(room: Any) -> Any:
        return {'documents':[]}
    async def reconcile(room: Any) -> Any:
        pass
    async def head() -> Any:
        return {'s':42}
    async def rooms() -> Any:
        return [{'id':'production'}]
    async def context(room_id: Any, since: Any) -> Any:
        return dict(truncated=False,threads=[dict(root=dict(id='offline-refusal',kind='message',sender='producer',
            sender_name='Producer',body='/change location stairwell permission refused',timestamp=1793950000000),replies=[])])
    async def operation(name: Any, arguments: Any=None) -> Any:
        assert name=='list_bridges'
        return []
    async def outcomes() -> Any:
        return [dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='stairs')]
    rt.client.connect_to_production=connect
    rt.reconcile_documents=reconcile
    rt.client.head_position=head
    rt.client.member_rooms=rooms
    rt.client.read_context=context
    rt.client.get_outcomes=outcomes
    rt.client.operation=operation
    await rt.connected()
    assert not rt.ready
    assert rt.loop.constraints.locations[2].permission=='refused'
    assert len(rt.ledger.snapshot_state()['releases'])==1
    await rt.accept_frame(SwitchFrame(event='message',data=dict(position={'s':42},room_id='production',payload=dict(
        sender='producer',body='/change location stairwell permission refused',message_id='offline-refusal'))))
    await rt.finish_catchup()
    assert rt.ready
    assert len(rt.ledger.snapshot_state()['releases'])==1
    assert not any(rt.loop.effect_current(e) for e in rt.ledger.pending_effects() if e['kind']=='release')
    rt.transport_lost()
    assert not rt.ready and not rt.dispatcher.enabled()
    await rt.close()


async def test_room_release_pauses_and_bridge_failure_is_visible(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    rt.client._identity=Identity(agent_id='coordinator',api_key='test-secret')
    rt.ready=True
    await rt.accept_frame(SwitchFrame(event='room_released',data=dict(room_id='production')))
    assert not rt.ready
    await rt.accept_frame(SwitchFrame(event='message',data=dict(room_id='production',payload=dict(sender='platform',
        sender_kind='platform',message_id='bridge-failure',body='Failed to relay message to Discord: channel unavailable'))))
    assert any('bridge delivery error' in t['text'].lower() for t in rt.ledger.snapshot_state()['timeline'])
    await rt.close()


async def test_transport_loss_during_outcome_fetch_cannot_reenable_old_barrier(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    q=await options(rt.loop)
    rt.catching_up=True
    rt.replay_fence={'s':0}
    rt.catchup_through='2026-11-04T10:00:00+05:30'
    async def outcomes() -> Any:
        rt.transport_lost()
        return [dict(session_id=q['session_id'],request_id=q['request_id'],answered_by='director',candidate_id='stairs')]
    rt.client.get_outcomes=outcomes
    await rt.finish_catchup()
    assert not rt.ready
    assert len(rt.ledger.snapshot_state()['releases'])==1
    await rt.close()
