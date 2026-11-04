"""Protocol punctuation and the deadline that gates recovered decisions."""
import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
import pytest
from websockets.asyncio.server import serve, ServerConnection

from coordinator.switch_client import SwitchClient, SwitchError
from coordinator.tests.test_runtime import runtime_for
from coordinator.tests.test_switch_client import identity_file
from coordinator.tests.test_w4_workflow import runtime, initial, change


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk


async def test_http_multibyte_punctuation_split_across_chunks(tmp_path: Path) -> None:
    text = '📄 updated room document “constraints-r3”.'
    payload = json.dumps({'result': text}, ensure_ascii=False).encode('utf-8')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
            200, stream=Chunks([payload[i:i+1] for i in range(len(payload))])))) as http:
        c = SwitchClient('http://switch.test', identity_file(tmp_path), http_client=http)
        await c.initialize()
        assert await c.operation('read_context') == text


async def test_websocket_multibyte_punctuation_split_across_frames(tmp_path: Path) -> None:
    text = '📄 updated room document “constraints-r3”.'
    payload = json.dumps(dict(event='message', data=dict(body=text)), ensure_ascii=False).encode('utf-8')
    split = payload.index('”'.encode('utf-8')) + 1
    async def handler(socket: ServerConnection) -> None:
        await socket.send([payload[:split], payload[split:split+1], payload[split+1:]], text=True)
        await socket.wait_closed()
    async with serve(handler, '127.0.0.1', 0) as server:
        port = server.sockets[0].getsockname()[1]
        c = SwitchClient(f'http://127.0.0.1:{port}', identity_file(tmp_path))
        try:
            async for frame in c.events():
                assert frame.data['body'] == text
                break
        finally:
            await c.aclose()


async def test_http_escaped_lone_surrogate_is_rejected_at_ingress(tmp_path: Path) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
            200, content=b'{"result":"constraints-r3\\udc9d."}'))) as http:
        c = SwitchClient('http://switch.test', identity_file(tmp_path), http_client=http)
        await c.initialize()
        with pytest.raises(SwitchError, match='invalid JSON'):
            await c.operation('read_context')


async def test_catchup_deadline_blocks_late_fence_and_outcome(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path, switch_production_room_id='production')
    calls: list[str] = []
    async def outcomes() -> list[Any]:
        calls.append('outcomes')
        return []
    rt.client.get_outcomes = outcomes
    rt.catching_up = True
    rt.catchup_through = '2026-11-04T10:00:00+05:30'
    rt.replay_fence = {'s': 0}
    rt.catchup_deadline = asyncio.get_running_loop().time() - 1
    try:
        await rt.finish_catchup()
        await rt.finish_catchup()
        assert not rt.ready
        assert not calls
        errors = [t for t in rt.ledger.snapshot_state()['timeline'] if '45 seconds' in t['text']]
        assert len(errors) == 1
        assert any('45 seconds' in e['payload'].get('body', '') for e in rt.ledger.pending_effects())
    finally:
        await rt.close()


async def test_catchup_outcome_fetch_cannot_overrun_deadline(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path, switch_production_room_id='production')
    cancelled = asyncio.Event()
    async def outcomes() -> list[Any]:
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
        return []
    rt.client.get_outcomes = outcomes
    rt.catching_up = True
    rt.catchup_through = '2026-11-04T10:00:00+05:30'
    rt.replay_fence = {'s': 0}
    rt.catchup_deadline = asyncio.get_running_loop().time() + 0.01
    try:
        await asyncio.wait_for(rt.finish_catchup(), 0.2)
        assert cancelled.is_set()
        assert not rt.ready
        assert any('45 seconds' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
    finally:
        await rt.close()


async def test_catchup_outcome_processing_cannot_overrun_deadline(tmp_path: Path) -> None:
    rt = runtime_for(tmp_path, switch_production_room_id='production')
    async def outcomes() -> list[Any]:
        return [dict(request_id='request')]
    async def handle(outcome: Any) -> bool:
        await asyncio.Event().wait()
        return True
    rt.client.get_outcomes = outcomes
    rt.loop.handle_outcome = handle
    rt.catching_up = True
    rt.catchup_through = '2026-11-04T10:00:00+05:30'
    rt.replay_fence = {'s': 0}
    rt.catchup_deadline = asyncio.get_running_loop().time() + 0.01
    try:
        await asyncio.wait_for(rt.finish_catchup(), 0.2)
        assert not rt.ready
        assert any('45 seconds' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
    finally:
        await rt.close()


async def test_worker_escaped_surrogate_gets_one_retry_then_visible_failure(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    try:
        await initial(rt.loop)
        await change(rt.loop)
        job = rt.loop.workflow['jobs'][-1]
        text = json.dumps(dict(job_id=job['job_id'], script_rev=1, constraints_rev=2,
            must_keep=['bad\udc9d']))
        assert not await rt.loop.handle_worker_reply(text)
        assert job['attempt'] == 1
        assert not await rt.loop.handle_worker_reply(text)
        assert job['status'] == 'failed'
        assert any(t['kind'] == 'error' for t in rt.ledger.snapshot_state()['timeline'])
    finally:
        await rt.close()
