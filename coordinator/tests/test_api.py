import asyncio
import copy
import json
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient

from coordinator.api import MAX_BODY_BYTES, MAX_QUEUED_STATES, MAX_SUBSCRIBERS, StateEvents, _contained, create_app

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "ui-state" / "01-normal.json"


def snapshot() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class Ledger:
    def __init__(self) -> None:
        self.state = snapshot()
        self.callbacks = []

    def snapshot_state(self) -> dict:
        return copy.deepcopy(self.state)

    def subscribe(self, callback):
        self.callbacks.append(callback)
        return lambda: self.callbacks.remove(callback)

    def commit(self, revision: int) -> None:
        self.state["revisions"]["constraints"] = revision
        for callback in self.callbacks:
            callback()


def test_state_and_structured_change_use_injected_pipeline() -> None:
    ledger = Ledger()
    received = []

    async def report(command):
        received.append(command)
        ledger.commit(2)
        return {"change_id": "change-1", "status": "recorded"}

    app = create_app(ledger, report)
    with TestClient(app) as client:
        assert len(ledger.callbacks) == 1
        assert client.get("/api/state").json() == snapshot()
        payload = dict(entity="location", target="rooftop", field="permission", value="refused", reporter="producer")
        response = client.post("/api/changes", json=payload)
        assert response.status_code == 200
        assert response.json() == {"change_id": "change-1", "status": "recorded"}
        assert received[0].model_dump() == payload
        assert client.get("/api/state").json()["revisions"]["constraints"] == 2
        assert client.post("/api/changes", json={**payload, "release": True}).status_code == 422
        assert len(received) == 1
    assert not ledger.callbacks


def test_unconfigured_reporter_is_visible_and_callback_provider_works() -> None:
    with TestClient(create_app(state_provider=snapshot)) as client:
        assert client.get("/api/state").status_code == 200
        result = client.post("/api/changes", json=dict(entity="scene", target="s3", field="safety", value="hold", reporter="maya"))
        assert result.status_code == 503


def test_no_implicit_demo_state() -> None:
    with pytest.raises(ValueError, match="ledger or state_provider"):
        create_app()


@pytest.mark.parametrize("dev,allowed", [(False, False), (True, True)])
def test_cors_is_dev_only_and_scoped_to_vite(dev: bool, allowed: bool) -> None:
    with TestClient(create_app(state_provider=snapshot, dev=dev)) as client:
        response = client.get("/api/state", headers={"Origin": "http://localhost:5173"})
        assert (response.headers.get("access-control-allow-origin") == "http://localhost:5173") is allowed
        hostile = client.get("/api/state", headers={"Origin": "https://other.example"})
        assert "access-control-allow-origin" not in hostile.headers


def test_static_media_only_serves_allowed_files_under_roots(tmp_path: Path) -> None:
    artifacts, ui = tmp_path / "out", tmp_path / "dist"
    artifacts.mkdir()
    (ui / "assets").mkdir(parents=True)
    (artifacts / "preview.mp4").write_bytes(b"demo-mp4")
    (artifacts / "sheet.png").write_bytes(b"demo-png")
    (artifacts / "secret.txt").write_text("never serve me")
    (tmp_path / "outside.png").write_bytes(b"outside")
    (ui / "index.html").write_text("<main>Control Room</main>")
    (ui / "assets" / "app.js").write_text("console.log('ready')")
    app = create_app(state_provider=snapshot, artifacts_dir=artifacts, ui_dist=ui)
    with TestClient(app) as client:
        assert client.get("/media/preview.mp4").headers["content-type"] == "video/mp4"
        assert client.get("/media/sheet.png").content == b"demo-png"
        assert client.get("/").text == "<main>Control Room</main>"
        assert client.get("/assets/app.js").status_code == 200
        for path in ("/media/secret.txt", "/media/%2e%2e/outside.png", "/media/..%5coutside.png", "/assets/%2e%2e/index.html"):
            assert client.get(path).status_code == 404


def test_media_resolves_symlinks_before_containment_check(tmp_path: Path) -> None:
    root = tmp_path / "media"
    root.mkdir()
    secret = tmp_path / "outside.png"
    secret.write_bytes(b"outside")
    try:
        (root / "link.png").symlink_to(secret)
    except OSError:
        pytest.skip("Symlink creation requires Windows developer mode or privilege")
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        _contained(root, "link.png")
    assert error.value.status_code == 404


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_sse_tracks_commits_in_order_and_heartbeats_then_unsubscribes() -> None:
    ledger = Ledger()
    app = create_app(ledger)
    async with app.router.lifespan_context(app):
        events = app.state.state_events
        assert events.heartbeat_seconds == 15
        events.heartbeat_seconds = 0.01
        stream = events.stream(ConnectedRequest())
        initial = await anext(stream)
        assert initial.startswith("event: state\ndata: ")
        assert json.loads(initial.split("data: ")[1])["revisions"]["constraints"] == 1
        # A commit from a worker thread must capture that revision, not a later one.
        await asyncio.to_thread(ledger.commit, 2)
        await asyncio.to_thread(ledger.commit, 3)
        for revision in (2, 3):
            item = await asyncio.wait_for(anext(stream), 1)
            assert json.loads(item.split("data: ")[1])["revisions"]["constraints"] == revision
        assert await anext(stream) == ": heartbeat\n\n"
        await stream.aclose()
        assert not events.listeners
    assert not ledger.callbacks


@pytest.mark.asyncio
async def test_callback_integration_requires_explicit_commit_publish() -> None:
    current = snapshot()
    events = StateEvents(lambda: current)
    events.heartbeat_seconds = 0.001
    stream = events.stream(ConnectedRequest())
    await anext(stream)
    current["revisions"]["constraints"] = 2
    assert await anext(stream) == ": heartbeat\n\n"
    await events.publish()
    assert json.loads((await anext(stream)).split("data: ")[1])["revisions"]["constraints"] == 2
    await stream.aclose()


def test_sse_subscriber_capacity_returns_429_before_streaming_headers() -> None:
    app = create_app(state_provider=snapshot)
    events = app.state.state_events
    for _ in range(MAX_SUBSCRIBERS):
        events.subscribe()
    with TestClient(app) as client:
        response = client.get("/api/events")
        assert response.status_code == 429
        assert response.headers["content-type"] == "application/json"
    assert len(events.listeners) == MAX_SUBSCRIBERS


@pytest.mark.asyncio
async def test_slow_sse_consumer_has_bounded_queue_and_receives_latest_snapshot() -> None:
    current = snapshot()
    events = StateEvents(lambda: current)
    stream = events.stream(ConnectedRequest())
    await anext(stream)
    queue = next(iter(events.listeners))
    for revision in range(2, 102):
        current["revisions"]["constraints"] = revision
        await events.publish()
        assert queue.qsize() <= MAX_QUEUED_STATES
    revisions = []
    while not queue.empty():
        revisions.append(json.loads((await anext(stream)).split("data: ")[1])["revisions"]["constraints"])
    assert revisions[-1] == 101
    assert len(revisions) <= MAX_QUEUED_STATES
    await stream.aclose()
    assert not events.listeners


def test_stalled_event_loop_schedules_only_one_bounded_commit_drain() -> None:
    scheduled = []

    class StalledLoop:
        def call_soon_threadsafe(self, callback):
            scheduled.append(callback)

    current = snapshot()
    events = StateEvents(lambda: current)
    events.loop = StalledLoop()
    queue = events.subscribe()
    for revision in range(2, 102):
        current["revisions"]["constraints"] = revision
        events.committed()
    assert len(scheduled) == 1
    assert len(events._pending) <= MAX_QUEUED_STATES
    scheduled[0]()
    assert queue.qsize() <= MAX_QUEUED_STATES
    payloads = [json.loads(queue.get_nowait()) for _ in range(queue.qsize())]
    assert payloads[-1]["revisions"]["constraints"] == 101


def test_oversized_content_length_is_rejected_before_parsing_or_handler() -> None:
    called = []
    app = create_app(state_provider=snapshot, change_handler=lambda value: called.append(value))
    with TestClient(app) as client:
        response = client.post("/api/changes", content=b"x" * (MAX_BODY_BYTES + 1))
        assert response.status_code == 413
    assert not called


@pytest.mark.asyncio
@pytest.mark.parametrize("declared_length", [None, "2"])
async def test_chunked_or_misdeclared_body_is_counted_before_json_parse(declared_length: str | None) -> None:
    called = []
    app = create_app(state_provider=snapshot, change_handler=lambda value: called.append(value))

    async def chunks():
        yield b"x" * (MAX_BODY_BYTES // 2)
        yield b"y" * MAX_BODY_BYTES
        raise AssertionError("Oversized request must stop consuming the upload")

    headers = {"Content-Type": "application/json"}
    if declared_length is not None:
        headers["Content-Length"] = declared_length
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/changes", content=chunks(), headers=headers)
    assert response.status_code == 413
    assert not called


def test_sqlite_save_with_exclude_none_preserves_required_decision_key(tmp_path: Path) -> None:
    from coordinator.ledger import Ledger as SQLiteLedger
    ledger = SQLiteLedger(tmp_path / "ledger.sqlite", initial_state=snapshot())
    try:
        stored = ledger.get_meta("state")
        assert "decision" in stored and stored["decision"] is None
        with TestClient(create_app(ledger)) as client:
            state = client.get("/api/state").json()
            assert "decision" in state and state["decision"] is None
    finally:
        ledger.connection.close()
