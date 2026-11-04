"""W4 chatter replay and real human report boundaries."""
from pathlib import Path
from typing import Any
import json

import pytest

from coordinator.switch_models import SwitchFrame
from coordinator.tests.test_runtime import runtime_for


def chat(sender: str, body: str, number: int, **fields: Any) -> SwitchFrame:
    return SwitchFrame(event='message', id=number, data=dict(room_id='production',
        payload=dict(sender=sender, body=body, message_id=f'm{number}', **fields)))


async def test_w4_chatter_never_becomes_report_but_maya_does_once(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path, take_two_director_id='director',
        take_two_supervisor_sender_id='supervisor', take_two_ad_sender_id='ad-worker')
    messages = [
        ('coordinator', 'Scene 3 is ON HOLD. Update coming.'),
        ('@switch-agent-self:localhost', 'Release r2'),
        ('@switch-agent-self:localhost', 'Release 2 approved; publication pending.'),
        ('@switch-agent-self:localhost', 'That was release 1. Please confirm r2.'),
        ('@switch-agent-self:localhost', 'A · Stairwell · checked pass'),
        ('@switch-agent-self:localhost', 'Report recorded as pending. An authorized person must confirm it with /change.'),
        ('@switch-agent-self:localhost', 'No Discord bridge yet; shoot-day publication is unavailable.'),
        ('@switch-agent-self:localhost', '@first-ad {"job_id":"123"}'),
        ('@switch-agent-self:localhost', '@script-supervisor {"job_id":"124"}'),
        ('@switch-agent-self:localhost', '📄 updated room document “constraints-r3”.'),
        ('supervisor', 'Malformed reply'),
        ('ad-worker', '{"job_id":"old"}'),
        ('director', 'A20 q1=2, "keep the confession private"'),
        ('director', '`A20: q1=2`'),
        ('maya', '/unknown command'),
        ('stranger', 'Sorry, I have to leave at 6.'),
        ('maya', '📄 updated room document “constraints-r3”.'),
    ]
    try:
        for number, (sender, body) in enumerate(messages, 1):
            await rt.accept_frame(chat(sender, body, number))
        assert not rt.ledger.snapshot_state()['changes']
        assert not any('reported a change' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
        maya = chat('maya', 'Sorry, I have to leave at 6.', 100, sender_name='Not a trusted name')
        await rt.accept_frame(maya)
        await rt.accept_frame(maya)
        state = rt.ledger.snapshot_state()
        assert len(state['changes']) == 1
        assert state['changes'][0]['reporter_name'] == 'Maya'
        assert state['changes'][0]['status'] == 'pending_confirmation'
        assert [t['text'] for t in state['timeline'] if 'reported a change' in t['text']] == [
            'Maya (Actor) reported a change; structured confirmation is required.']
    finally:
        await rt.close()


@pytest.mark.parametrize('kind', ['platform', 'agent'])
async def test_system_kind_cannot_become_human_report(tmp_path: Path, kind: str) -> None:
    rt = runtime_for(tmp_path)
    try:
        await rt.accept_frame(chat('maya', 'A system notice', 1, sender_kind=kind))
        assert not rt.ledger.snapshot_state()['changes']
    finally:
        await rt.close()


async def test_known_authority_report_uses_configured_name_not_message_name(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path, take_two_producer_id='@nila:localhost')
    try:
        await rt.accept_frame(chat('@nila:localhost', 'The location contact has changed.', 1, sender_name='Evil name'))
        state = rt.ledger.snapshot_state()
        assert state['changes'][0]['reporter_name'] == 'Nila'
        assert state['timeline'][0]['text'].startswith('Nila (Producer) reported')
    finally:
        await rt.close()


async def test_consumed_question_message_never_becomes_report(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path, take_two_director_id='director')
    try:
        await rt.accept_frame(chat('director', 'yes', 1, thread_id='native-card-root'))
        assert not rt.ledger.snapshot_state()['changes']
    finally:
        await rt.close()


async def test_pending_report_is_deduped_across_restart_and_history(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path)
    frame = chat('maya', 'Sorry, I have to leave at 6.', 1)
    await rt.accept_frame(frame)
    await rt.close()
    rt = runtime_for(tmp_path)
    try:
        await rt.accept_frame(frame.model_copy(update={'id': 2}))
        assert len(rt.ledger.snapshot_state()['changes']) == 1
        assert len([e for e in rt.ledger.pending_effects() if e['key'].startswith('pending-report:')]) == 1
    finally:
        await rt.close()


async def test_exact_w4_ledger_reports_replay_without_coordinator_noise(tmp_path: Path) -> None:
    fixture = json.loads((Path(__file__).resolve().parents[2] / 'fixtures/w5-room-chatter.json').read_text(encoding='utf-8'))
    rt = runtime_for(tmp_path, take_two_director_id='director',
        take_two_coordinator_sender_id='@switch-agent-self:localhost')
    try:
        for sequence, message in enumerate(fixture['messages'], 1):
            await rt.accept_frame(chat(message['sender'], message['body'], sequence))
        state = rt.ledger.snapshot_state()
        assert len(state['changes']) == 1
        assert state['changes'][0]['reporter_name'] == 'Maya'
        assert len([t for t in state['timeline'] if 'reported a change' in t['text']]) == 1
    finally:
        await rt.close()


async def test_coordinator_sender_is_excluded_even_if_misconfigured_as_crew(tmp_path: Path) -> None:
    sender = '@switch-agent-self:localhost'
    rt = runtime_for(tmp_path, take_two_coordinator_sender_id=sender,
        take_two_crew_identities={sender: 'maya'})
    try:
        await rt.accept_frame(chat(sender, 'Release r2', 1))
        assert not rt.ledger.snapshot_state()['changes']
    finally:
        await rt.close()
