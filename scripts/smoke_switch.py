"""Real-server acceptance probe. Run with the coordinator stopped; no fake path."""
import asyncio
from datetime import datetime, timedelta
import json
from time import monotonic
from zoneinfo import ZoneInfo

from coordinator.config import Settings
from coordinator.ledger import Ledger
from coordinator.runtime import initial_state
from coordinator.switch_client import SwitchClient
from coordinator.switch_models import QuestionOption


async def main() -> None:
    settings = Settings()
    if not settings.switch_production_room_id:
        raise RuntimeError('Set SWITCH_PRODUCTION_ROOM_ID before the real probe.')
    client = SwitchClient(settings.switch_api_url, settings.take_two_identity,
        settings.switch_registration_key.get_secret_value(), production_room_id=settings.switch_production_room_id)
    ledger = Ledger(settings.take_two_db, initial_state=initial_state())
    connected = asyncio.Event()
    opens = 0
    async def observe() -> None:
        nonlocal opens
        async for frame in client.events():
            if frame.event == 'connection_state':
                opens += 1
                connected.set()
            elif frame.event in ('gap', 'evicted', 'refused'):
                raise RuntimeError('Connection requires reconciliation; real probe failed.')
            # This transport probe does not execute the coordinator's business handlers.
            # Never advance their inbox/cursor or acknowledge their outcomes here.
    await client.initialize()
    observer = asyncio.create_task(observe())
    try:
        await asyncio.wait_for(connected.wait(), 20)
        start = monotonic()
        await client.connect_to_production(settings.switch_production_room_id)
        document = await client.create_room_document('w1-probe-' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'Real day-one transport probe', 'Test input only; does not approve any plan.',
            'Take Two registered and connected to the real Switch server.')
        payload = client.question_payload('Take Two connection check', 'Can you see this question card?',
            [QuestionOption(id='visible', label='I can see this card')],
            datetime.now(ZoneInfo('Asia/Kolkata')) + timedelta(hours=2))
        with ledger.transaction():
            ledger.put('questions', payload.request_id, payload.model_dump(mode='json'), 'open', 1)
        opened = await client.open_question(payload)
        for _ in range(301):
            if observer.done():
                await observer
                raise RuntimeError('Live stream ended before five minutes.')
            if monotonic() - start >= 300:
                break
            await asyncio.sleep(1)
        if opens != 1:
            raise RuntimeError('Stream reconnected during the five-minute probe.')
        print(json.dumps(dict(connected_seconds=round(monotonic()-start, 1), connection_opens=opens,
            document_response=document.model_dump(), question_state=opened.state,
            question_request_shape=payload.model_dump(mode='json')), ensure_ascii=False))
    finally:
        observer.cancel()
        await asyncio.gather(observer, return_exceptions=True)
        await client.aclose()
        ledger.close()


if __name__ == '__main__':
    asyncio.run(main())
