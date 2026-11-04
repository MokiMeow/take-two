"""Protocol tests use in-memory transports; runtime code always calls Switch."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from coordinator.switch_client import RoleUnavailable, StaleOperation, SwitchClient, SwitchError, TakenOver
from coordinator.switch_models import QuestionOption, SwitchFrame


def identity_file(tmp_path):
    path = tmp_path / "identity.json"
    path.write_text(json.dumps({"agent_id": "coordinator", "api_key": "agent-secret",
        "connection_id": "connection-1", "session_id": "session-1",
        "position": {"s": 4}, "cursor": 4}), encoding="utf-8")
    return path


def client(tmp_path, handler, **kwargs):
    return SwitchClient("http://switch.test", identity_file(tmp_path),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **kwargs)


def test_registration_once_and_secret_redaction(tmp_path):
    async def scenario():
        calls = []
        def handler(req):
            calls.append(req)
            body = json.loads(req.content)
            assert req.url.path == "/agents"
            assert req.headers["authorization"] == "Bearer registration-secret"
            assert body["connector_type"] == "take-two-coordinator"
            assert body["integration_profile"]["connection_model"] == "always_on"
            assert body["overwrite"] is False
            return httpx.Response(200, json={"id": "agent-1", "api_key": "agent-secret"})
        path = tmp_path / "identity.json"
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            first = SwitchClient("http://switch.test", path, "registration-secret", http_client=http)
            identity = await first.initialize()
            assert "agent-secret" not in repr(identity)
            second = SwitchClient("http://switch.test", path, http_client=http)
            restored = await second.initialize()
            assert restored.agent_id == "agent-1"
            assert restored.connection_id == identity.connection_id
            assert restored.session_id == identity.session_id
            assert len(calls) == 1
    asyncio.run(scenario())


def test_operations_documents_and_explicit_room_routes(tmp_path):
    async def scenario():
        requests = []
        def handler(req):
            requests.append(req)
            assert req.headers["authorization"] == "Bearer agent-secret"
            assert req.headers["x-switch-connection-id"] == "connection-1"
            if "/media" in req.url.path:
                assert b"video/mp4" in req.content and b"movie-bytes" in req.content
                return httpx.Response(200, json={"ok": True})
            if req.url.path.endswith("/message"):
                assert json.loads(req.content) == {"room_id": "crew", "content": "hold"}
                return httpx.Response(200, json={"event_id": "m1", "ok": True})
            op = req.url.path.rsplit("/", 1)[-1]
            data = {"room_id": "production"} if op == "connect_to_room" else {"document_id": "doc1"}
            return httpx.Response(200, json={"result": data})
        c = client(tmp_path, handler)
        await c.initialize()
        await c.connect_to_production("production")
        assert (await c.create_room_document("script", "script", "read", "hello")).document_id == "doc1"
        await c.update_room_document("doc1", content="revision2")
        await c.send_message("crew", "hold")
        movie = tmp_path / "preview.mp4"
        movie.write_bytes(b"movie-bytes")
        await c.send_media("crew", movie, caption="r2")
        assert requests[-1].url.path == "/agents/coordinator/rooms/crew/media"
        await c.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("holders,statuses", [([], {}),
    ([{"name": "ad", "present_here": False}], {}),
    ([{"name": "ad", "present_here": True}], {}),
    ([{"name": "ad", "present_here": True}], {"ad": "not_permitted"})])
def test_empty_absent_or_denied_role_is_visible_failure(tmp_path, holders, statuses):
    async def scenario():
        def handler(req):
            if req.url.path.endswith("list_roles"):
                result = [{"name": "first-ad", "exclusive": True, "held_by": holders}]
            else:
                result = {"event_id": "m", "target_statuses": statuses}
            return httpx.Response(200, json={"result": result})
        c = client(tmp_path, handler, production_room_id="production")
        await c.initialize()
        with pytest.raises(RoleUnavailable):
            await c.send_role_message("first-ad", "job")
        await c.aclose()
    asyncio.run(scenario())


def test_question_exact_payload_survives_restart_and_outcomes_are_not_auto_delivered(tmp_path):
    async def scenario():
        calls = []
        outcome = {"sessionId": "session-1", "requestId": "request-1", "kind": "questions",
            "state": "answered", "answer": None, "answers": [{"question_id": "choice", "selected_option_ids": ["A"]}],
            "answeredBy": "director", "answeredAt": "2026-11-04T10:00:00+05:30",
            "expiresAt": None, "deliveredAt": None}
        def handler(req):
            calls.append(req)
            if req.url.path.endswith("outcomes"):
                return httpx.Response(200, json=[outcome])
            if req.url.path.endswith("approvals"):
                stored = tmp_path / "questions.json"
                assert stored.exists()  # exact payload durable before network side effect
            return httpx.Response(200, json=outcome)
        c = client(tmp_path, handler, production_room_id="production")
        await c.initialize()
        payload = c.question_payload("Pick a plan", "Which?", [QuestionOption(id="A", label="Stairwell")],
            datetime.now(timezone.utc) + timedelta(hours=2), request_id="request-1")
        await c.open_question(payload)
        first = calls[-1].content
        opened = json.loads(first)
        assert opened["kind"] == "questions" and opened["options"] == []
        assert opened["thread_id"] is None and opened["room_id"] == "production"
        assert opened["questions"][0]["allow_custom_answer"] is True
        restored = SwitchClient("http://switch.test", c.identity_path, http_client=c.http)
        await restored.initialize()
        await restored.retry_question("request-1")
        assert calls[-1].content == first
        assert (await restored.get_outcomes())[0].answered_by == "director"
        assert not any(r.url.path.endswith("/delivered") for r in calls)
        await restored.mark_delivered("request-1")
        assert calls[-1].url.path.endswith("/session-1/approvals/request-1/delivered")
        await restored.close_question("request-1")
        assert calls[-1].url.path.endswith("/close")
        with pytest.raises(ValueError, match="immutable"):
            await c.open_question(payload.model_copy(update={"title": "changed"}))
        await c.aclose()
    asyncio.run(scenario())


class FakeSocket:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent = []
    async def __aenter__(self):
        return self
    async def __aexit__(self, *_):
        pass
    def __aiter__(self):
        return self
    async def __anext__(self):
        await asyncio.sleep(0)
        if not self.frames:
            raise StopAsyncIteration
        return json.dumps(self.frames.pop(0))
    async def send(self, payload):
        self.sent.append(json.loads(payload))


def test_socket_ping_scope_resume_and_terminal_takeover(tmp_path):
    async def scenario():
        socket = FakeSocket([
            {"event": "connection_state", "data": {"position": {"s": 4, "r:crew": 2}}},
            {"event": "message", "id": 5, "data": {"position": {"r:crew": 3}, "payload": {"body": "report"}}},
            {"event": "ping", "data": {}},
            {"event": "evicted", "data": {"code": "taken_over"}}])
        opens = []
        def connect(url, **kwargs):
            opens.append((url, kwargs))
            return socket
        c = client(tmp_path, lambda _: httpx.Response(200), websocket_connect=connect,
            production_room_id="production")
        await c.initialize()
        with pytest.raises(TakenOver):
            async for frame in c.events():
                c.mark_processed(frame)
                await asyncio.sleep(0.01)  # ping must work while consumer is busy
        assert len(opens) == 1
        query = parse_qs(urlparse(opens[0][0]).query)
        assert query["scope"] == ["all"] and query["filter"] == ["all"]
        assert query["rooms"] == ["production"] and query["protocol"] == ["9"]
        assert json.loads(query["start_at"][0]) == {"s": 4}
        assert socket.sent[0]["type"] == "pong"
        restored = SwitchClient("http://switch.test", c.identity_path)
        assert (await restored.initialize()).position["r:crew"] == 3
        await c.aclose()
        await restored.aclose()
    asyncio.run(scenario())


def test_cursor_only_advances_after_commit_and_gap_can_reset_position(tmp_path):
    async def scenario():
        c = client(tmp_path, lambda _: httpx.Response(200))
        identity = await c.initialize()
        frame = SwitchFrame(event="message", id=7, data={"position": {"s": 7}})
        assert identity.position == {"s": 4}
        c.mark_processed(frame)
        assert c.identity.position == {"s": 7}
        c.mark_processed(SwitchFrame(event="gap", data={"resumed_position": {"s": 1}}))
        assert c.identity.position == {"s": 1}
        await c.aclose()
    asyncio.run(scenario())


def test_transient_reconnect_is_bounded(tmp_path):
    async def scenario():
        calls = []
        def connect(*args, **kwargs):
            calls.append(args)
            raise OSError("offline")
        c = client(tmp_path, lambda _: httpx.Response(200), websocket_connect=connect,
            max_reconnects=2, reconnect_delay=0)
        await c.initialize()
        with pytest.raises(ConnectionError, match="reconnect"):
            async for _ in c.events():
                pass
        assert len(calls) == 3
        await c.aclose()
    asyncio.run(scenario())


def test_role_revision_guard_runs_after_async_presence_check(tmp_path):
    async def scenario():
        paths = []
        def handler(req):
            paths.append(req.url.path)
            return httpx.Response(200, json={"result": [{"name": "first-ad", "held_by": [
                {"name": "ad", "present_here": True}]}]})
        c = client(tmp_path, handler, production_room_id="production")
        await c.initialize()
        with pytest.raises(StaleOperation):
            await c.send_role_message("first-ad", "job", before_send=lambda: False)
        assert len(paths) == 1 and paths[0].endswith("list_roles")
        await c.aclose()
    asyncio.run(scenario())


def test_room_provision_retains_failed_attachments(tmp_path):
    async def scenario():
        def handler(req):
            assert json.loads(req.content)["inputs"] == {"bridge": "Discord"}
            return httpx.Response(200, json={"result": {"room_id": "crew", "room_name": "crew",
                "failed_attachments": [{"name": "reference", "reason": "not found"}]}})
        c = client(tmp_path, handler)
        await c.initialize()
        result = await c.create_room_from_yaml("room: {}", {"bridge": "Discord"})
        assert result.room_id == "crew" and result.failed_attachments
        await c.aclose()
    asyncio.run(scenario())


def test_question_rejects_naive_expiry(tmp_path):
    async def scenario():
        c = client(tmp_path, lambda _: httpx.Response(200), production_room_id="production")
        await c.initialize()
        with pytest.raises(ValueError, match="timezone"):
            c.question_payload("Plan", "Which?", [QuestionOption(id="A", label="A")], datetime(2026, 11, 4))
        await c.aclose()
    asyncio.run(scenario())


def test_resume_uses_authoritative_ledger_position_and_session(tmp_path):
    async def scenario():
        c = client(tmp_path, lambda _: httpx.Response(200))
        await c.initialize()
        c.set_session_id("persisted-logical-session")
        c.resume_from({"s": 2, "r:crew": 6})
        restored = SwitchClient("http://switch.test", c.identity_path)
        identity = await restored.initialize()
        assert identity.session_id == "persisted-logical-session"
        assert identity.position == {"s": 2, "r:crew": 6}
        assert identity.cursor == 2
        await c.aclose()
        await restored.aclose()
    asyncio.run(scenario())


def test_http_response_is_bounded(tmp_path):
    async def scenario():
        c = client(tmp_path, lambda _: httpx.Response(200, content=b"x" * (4 * 1024 * 1024 + 1)))
        await c.initialize()
        with pytest.raises(SwitchError, match="limit"):
            await c.get_outcomes()
        await c.aclose()
    asyncio.run(scenario())


def test_taken_over_refusal_remains_terminal_for_same_client(tmp_path):
    async def scenario():
        calls = []
        def connect(*args, **kwargs):
            calls.append(args)
            return FakeSocket([{"event": "refused", "data": {"status": 409,
                "detail": {"code": "taken_over", "message": "newer incarnation"}}}])
        c = client(tmp_path, lambda _: httpx.Response(200), websocket_connect=connect)
        await c.initialize()
        with pytest.raises(TakenOver):
            async for _ in c.events():
                pass
        with pytest.raises(TakenOver):
            await c.send_message("crew", "must not send")
        with pytest.raises(TakenOver):
            async for _ in c.events():
                pass
        assert len(calls) == 1
        await c.aclose()
    asyncio.run(scenario())


def test_transient_open_refusals_reconnect_with_a_bound(tmp_path):
    async def scenario():
        calls = []
        def connect(*args, **kwargs):
            calls.append(args)
            return FakeSocket([{"event": "refused", "data": {"status": 503, "detail": "starting"}}])
        c = client(tmp_path, lambda _: httpx.Response(200), websocket_connect=connect,
            max_reconnects=1, reconnect_delay=0)
        await c.initialize()
        with pytest.raises(ConnectionError):
            async for _ in c.events():
                pass
        assert len(calls) == 2
        await c.aclose()
    asyncio.run(scenario())


async def test_heartbeat_lapse_pauses_before_reconnect_without_terminal_frame(tmp_path) -> None:
    sockets=[FakeSocket([dict(event='connection_state',data=dict(position={'s':4})),
        dict(event='evicted',data=dict(code='heartbeat_lapsed'))]),
        FakeSocket([dict(event='connection_state',data=dict(position={'s':4})),
            dict(event='message',data=dict(position={'s':5},payload=dict(body='caught up')))])]
    opened=[]
    def connect(*args,**kwargs):
        opened.append(True)
        return sockets.pop(0)
    c=client(tmp_path,lambda _:httpx.Response(200),websocket_connect=connect,max_reconnects=1,reconnect_delay=0)
    paused=[]
    c.on_transport_lost=lambda:paused.append(True)
    seen=[]
    try:
        async for frame in c.events():
            seen.append(frame.event)
            assert frame.event!='evicted'
            if frame.event=='message':
                break
        assert len(opened)==2 and paused
    finally:
        await c.aclose()
