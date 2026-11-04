"""Read-mostly Control Room API backed by committed ledger snapshots."""

import asyncio
import inspect
import threading
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .ui_models import ChangeCommand, ChangeResponse, State

ROOT = Path(__file__).resolve().parent.parent
MAX_BODY_BYTES = 16 * 1024
MAX_SUBSCRIBERS = 64
MAX_QUEUED_STATES = 8
Snapshot = State | dict[str, Any]
StateProvider = Callable[[], Snapshot | Awaitable[Snapshot]]
ChangeHandler = Callable[[ChangeCommand], ChangeResponse | dict[str, Any] | Awaitable[Any]]


class LedgerSource(Protocol):
    def snapshot_state(self) -> Snapshot: ...

    def subscribe(self, callback: Callable[..., None]) -> Callable[[], None]: ...


async def _resolve(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _json(snapshot: Snapshot) -> str:
    return State.model_validate(snapshot).model_dump_json(exclude_none=True)


class StateEvents:
    """Process-local fanout; durable state always comes from the ledger."""

    def __init__(self, provider: StateProvider) -> None:
        self.provider = provider
        self.listeners: set[asyncio.Queue[str]] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.heartbeat_seconds = 15.0
        self._pending: deque[str] = deque(maxlen=MAX_QUEUED_STATES)
        self._pending_lock = threading.Lock()
        self._drain_scheduled = False

    def subscribe(self) -> asyncio.Queue[str]:
        if len(self.listeners) >= MAX_SUBSCRIBERS:
            raise HTTPException(429, "Too many live state subscribers")
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=MAX_QUEUED_STATES)
        self.listeners.add(queue)
        return queue

    async def publish(self, snapshot: Snapshot | None = None) -> None:
        payload = _json(snapshot if snapshot is not None else await _resolve(self.provider()))
        self._broadcast(payload)

    def _broadcast(self, payload: str) -> None:
        for queue in tuple(self.listeners):
            if queue.full():
                # Every event is a complete snapshot; retain the newest state.
                while not queue.empty():
                    queue.get_nowait()
            queue.put_nowait(payload)

    def _drain(self) -> None:
        with self._pending_lock:
            payloads = tuple(self._pending)
            self._pending.clear()
            self._drain_scheduled = False
        for payload in payloads:
            self._broadcast(payload)

    def committed(self, snapshot: Snapshot | None = None, *_: Any) -> None:
        """Ledger callbacks run only after COMMIT, possibly from another thread."""
        value = snapshot if isinstance(snapshot, (dict, State)) else self.provider()
        if inspect.isawaitable(value):
            if inspect.iscoroutine(value):
                value.close()
            raise TypeError("Ledger commit snapshots must be synchronous; use publish for async providers")
        payload = _json(value)
        if self.loop is not None:
            # One scheduled callback and at most eight snapshots even if the
            # event loop is stalled while another thread commits repeatedly.
            with self._pending_lock:
                self._pending.append(payload)
                if not self._drain_scheduled:
                    self._drain_scheduled = True
                    self.loop.call_soon_threadsafe(self._drain)

    async def stream(self, request: Request, queue: asyncio.Queue[str] | None = None) -> AsyncIterator[str]:
        queue = queue if queue is not None else self.subscribe()
        try:
            # Subscribe before reading, so a concurrent commit cannot be missed.
            yield f"event: state\ndata: {_json(await _resolve(self.provider()))}\n\n"
            while not await request.is_disconnected():
                try:
                    payload = await asyncio.wait_for(queue.get(), self.heartbeat_seconds)
                    yield f"event: state\ndata: {payload}\n\n"
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            self.listeners.discard(queue)


class BoundedChangeBody:
    """Reject oversized bodies before FastAPI buffers or parses their JSON."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != "/api/changes":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            await JSONResponse({"detail": "Invalid Content-Length"}, 400)(scope, receive, send)
            return
        if declared < 0 or declared > MAX_BODY_BYTES:
            await JSONResponse({"detail": "Change body exceeds 16 KiB"}, 413)(scope, receive, send)
            return
        body: bytearray | None = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                await JSONResponse({"detail": "Change body exceeds 16 KiB"}, 413)(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            nonlocal body
            if body is not None:
                content, body = bytes(body), None
                return {"type": "http.request", "body": content, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def _contained(root: Path, filename: str) -> Path:
    """Resolve symlinks and Windows separators before permitting a file read."""
    if not filename or "\\" in filename or ":" in filename:
        raise HTTPException(404, "File not found")
    resolved_root = root.resolve()
    candidate = (resolved_root / filename).resolve()
    if not candidate.is_relative_to(resolved_root) or not candidate.is_file():
        raise HTTPException(404, "File not found")
    return candidate


def create_app(
    ledger: LedgerSource | None = None,
    change_handler: ChangeHandler | None = None,
    *,
    state_provider: StateProvider | None = None,
    artifacts_dir: str | Path = ROOT / "out",
    ui_dist: str | Path = ROOT / "ui" / "dist",
    dev: bool = False,
) -> FastAPI:
    """Use a ledger, or inject callbacks and publish after your transaction commits.

    Callback integrations call ``await app.state.state_events.publish()`` after
    COMMIT. Ledger integrations subscribe automatically during app lifespan.
    """
    if state_provider is None:
        if ledger is None:
            raise ValueError("create_app requires a ledger or state_provider")
        state_provider = ledger.snapshot_state
    events = StateEvents(state_provider)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        events.loop = asyncio.get_running_loop()
        unsubscribe = ledger.subscribe(events.committed) if ledger is not None else None
        try:
            yield
        finally:
            if unsubscribe is not None:
                unsubscribe()
            events.loop = None

    app = FastAPI(title="Take Two Control Room", lifespan=lifespan)
    app.add_middleware(BoundedChangeBody)
    app.state.state_events = events
    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @app.get("/api/state", response_model=State, response_model_exclude_none=True)
    async def get_state() -> State:
        return State.model_validate(await _resolve(state_provider()))

    @app.get("/api/events")
    async def get_events(request: Request) -> StreamingResponse:
        queue = events.subscribe()  # Reserve before StreamingResponse sends 200.
        return StreamingResponse(
            events.stream(request, queue),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/changes", response_model=ChangeResponse, response_model_exclude_none=True)
    async def post_change(command: ChangeCommand) -> ChangeResponse:
        if change_handler is None:
            raise HTTPException(503, "Change reporting is unavailable")
        return ChangeResponse.model_validate(await _resolve(change_handler(command)))

    artifact_root, ui_root = Path(artifacts_dir), Path(ui_dist)

    @app.get("/media/{filename:path}")
    async def media(filename: str) -> FileResponse:
        path = _contained(artifact_root, filename)
        if path.suffix.lower() not in {".png", ".mp4"}:
            raise HTTPException(404, "File not found")
        return FileResponse(path, media_type="image/png" if path.suffix.lower() == ".png" else "video/mp4")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(_contained(ui_root, "index.html"), media_type="text/html")

    @app.get("/assets/{filename:path}")
    async def assets(filename: str) -> FileResponse:
        return FileResponse(_contained(ui_root / "assets", filename))

    return app
