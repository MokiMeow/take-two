"""Provision a private production room and run the real five-minute W1 probe.

Run only while the coordinator has no active Switch connection. No application
events are acknowledged: the coordinator must process them on its own restart.
"""
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo

from dotenv import dotenv_values
import yaml

from coordinator.config import Settings
from coordinator.ledger import Ledger, now_iso
from coordinator.runtime import initial_state, read_yaml
from coordinator.switch_client import SwitchClient
from coordinator.switch_models import QuestionOption


async def main() -> None:
    settings = Settings()
    ledger = Ledger(settings.take_two_db, initial_state=initial_state())
    client = SwitchClient(settings.switch_api_url, settings.take_two_identity,
                          settings.switch_registration_key.get_secret_value())
    await client.initialize()
    client.set_session_id(ledger.get_meta('question_session_id', client.identity.session_id))
    connected = asyncio.Event()
    opens = 0
    async def observe() -> None:
        nonlocal opens
        async for frame in client.events():
            if frame.event == 'connection_state':
                opens += 1
                connected.set()
            if frame.event in ('gap', 'evicted', 'refused'):
                raise RuntimeError('Real probe received ' + frame.event)
    observer = asyncio.create_task(observe())
    try:
        await asyncio.wait_for(connected.wait(), 20)
        started_at, start = now_iso(), monotonic()
        room_id = settings.switch_production_room_id or ledger.get_meta('production_room_id')
        if not room_id:
            template = yaml.safe_load(Path('templates/production.yaml').read_text(encoding='utf-8'))
            # The two real Console identities will be attached by the human later.
            for name in ('script_supervisor', 'first_ad'):
                template['params'].pop(name)
            template['room']['agents'] = ['{coordinator}']
            provision = await client.create_room_from_yaml(yaml.safe_dump(template), {'bridge': 'Mattermost'})
            if provision.failed_attachments:
                raise RuntimeError('Production room has failed attachments; inspect the ledger.')
            room_id = provision.room_id
            with ledger.transaction():
                ledger.set_meta('production_room_id', room_id)
            path = Path('.env')
            lines = path.read_text(encoding='utf-8').splitlines()
            lines = [('SWITCH_PRODUCTION_ROOM_ID=' + room_id) if line.startswith('SWITCH_PRODUCTION_ROOM_ID=') else line for line in lines]
            path.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
            print('private_production_room_created', flush=True)
        room = await client.connect_to_production(room_id)
        documents = room.get('documents') or []
        for name, content in (
            ('script-r1', json.dumps(read_yaml('script.yaml'), ensure_ascii=False)),
            ('constraints-r1', json.dumps(read_yaml('constraints-r1.yaml'), ensure_ascii=False))):
            existing = next((doc for doc in documents if doc.get('name') == name), None)
            result = await client.update_room_document(existing['id'], content=content) if existing else await client.create_room_document(
                name, 'Take Two canonical input', 'Agents propose; the coordinator checks; humans decide.', content)
            with ledger.transaction():
                ledger.set_meta('document:' + name, result.document_id)
                ledger.set_meta('doc:' + name, result.document_id)
        payload = client.question_payload('Take Two W1 live connection check',
            'Can you see this native question? This transport check approves no shoot plan.',
            [QuestionOption(id='visible', label='I can see the card')],
            datetime.now(ZoneInfo('Asia/Kolkata')) + timedelta(hours=2))
        with ledger.transaction():
            ledger.put('questions', payload.request_id, payload.model_dump(mode='json'), 'open', 1)
        response = await client.open_question(payload)
        print('real_documents_and_question_created', flush=True)
        evidence = dict(started_at=started_at, room_id=room_id, request_id=payload.request_id,
            request=payload.model_dump(mode='json'), response=response.model_dump(mode='json'))
        Path('data/live-w1-proof.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8', newline='\n')
        for _ in range(301):
            if observer.done():
                await observer
                raise RuntimeError('Live stream ended early.')
            if monotonic()-start >= 300:
                break
            await asyncio.sleep(1)
        if opens != 1:
            raise RuntimeError('Probe reconnected; five-minute uninterrupted condition failed.')
        evidence.update(connected_seconds=round(monotonic()-start, 2), connection_opens=opens, finished_at=now_iso())
        Path('data/live-w1-proof.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8', newline='\n')
        print(json.dumps({key: evidence[key] for key in ('connected_seconds','connection_opens','finished_at')}), flush=True)
    finally:
        observer.cancel()
        await asyncio.gather(observer, return_exceptions=True)
        await client.aclose()
        ledger.close()


if __name__ == '__main__':
    asyncio.run(main())
