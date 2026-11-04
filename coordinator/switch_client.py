"""Original async Switch client; wire contract checked at commit 989225d8.

References: sandbox-quantum/switch core/switch_core/bridges/agent/api/{handlers,
activity_routes,operations}.py; protocol/{stream,positions}.py; and Console's
switch-agent-runtime/src/event-stream.ts. Switch copyright SandboxAQ; its
license is Apache-2.0 with modified Commons Clause. No implementation copied.
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
from coordinator.unicode_text import require_unicode

from coordinator.switch_models import (
    ApprovalOutcome, DocumentResult, Identity, InternalDocument, MessageReceipt,
    OperationEnvelope, Question, QuestionOption, QuestionPayload, Registration,
    RegistrationResponse, RoomProvision, RoomRole, SwitchFrame, TargetedMessage,
)


class SwitchError(RuntimeError):
    """A server refusal or invalid protocol response; credentials are omitted."""

    def __init__(self, message: str, *, http_status: int | None=None) -> None:
        super().__init__(message)
        self.http_status=http_status


class TakenOver(SwitchError):
    """Terminal: another process owns this connection. Do not reconnect."""


class RoleUnavailable(SwitchError):
    """Delegation has no live, permitted holder in the production room."""


class StaleOperation(SwitchError):
    """The application invalidated work while a presence check was in flight."""


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class SwitchClient:
    def __init__(
        self, base_url: str, identity_path: str | Path = "data/identity.json",
        registration_key: str | None = None, *, production_room_id: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        websocket_connect: Callable[..., Any] | None = None,
        max_reconnects: int = 5, reconnect_delay: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.identity_path = Path(identity_path)
        self.question_path = self.identity_path.with_name("questions.json")
        self.registration_key = registration_key
        self.production_room_id = production_room_id
        self.http = http_client or httpx.AsyncClient(timeout=30)
        self._owns_http = http_client is None
        self._connect = websocket_connect or connect
        self._identity: Identity | None = None
        self.max_reconnects = max_reconnects
        self.reconnect_delay = reconnect_delay
        self._reader: asyncio.Task[None] | None = None
        self._taken_over = False
        self.on_transport_lost: Callable[[],None] = lambda: None

    async def head_position(self) -> dict[str,int]:
        """Read the authoritative own-event head without claiming any room.

        Source: Switch protocol/stream.py connection_state and Console's
        event-stream.ts positions; this short probe has its own connection UUID.
        """
        parts = urlsplit(self.base_url)
        params = dict(connection_id=str(uuid4()),scope='all',filter='addressed',start_at='head',protocol='9',protocol_accepts='9')
        url = urlunsplit(('wss' if parts.scheme=='https' else 'ws',parts.netloc,
            parts.path+self._agent_path+'/connection/ws',urlencode(params),''))
        async with self._connect(url,additional_headers=self._headers,open_timeout=15,max_size=2**20) as socket:
            frame = SwitchFrame.model_validate_json(await asyncio.wait_for(socket.recv(),15))
            if frame.event!='connection_state':
                raise SwitchError('Catch-up head probe was refused')
            return Identity.model_validate(dict(agent_id='probe',api_key='unused',position=frame.data['position'])).position

    async def member_rooms(self) -> list[dict[str,Any]]:
        return await self.operation('list_rooms')

    async def read_context(self, room_id: str, since: str) -> dict[str,Any]:
        return await self.operation('read_context',dict(room_id=room_id,since=since,limit=1000))

    @property
    def identity(self) -> Identity:
        if self._identity is None:
            raise SwitchError("initialize the Switch identity first")
        return self._identity

    async def initialize(self) -> Identity:
        if self._identity is not None:
            return self._identity
        if self.identity_path.exists():
            self._identity = Identity.model_validate_json(self.identity_path.read_text(encoding="utf-8"))
        else:
            if not self.registration_key:
                raise SwitchError("a personal Switch registration key is required for first registration")
            body = RegistrationResponse.model_validate(await self._exchange("POST", "/agents",
                headers={"Authorization": f"Bearer {self.registration_key}"},
                json=Registration().model_dump(mode="json")))
            self._identity = Identity(agent_id=body.id, api_key=body.api_key)
            self._save_identity()
        self.registration_key = None
        return self.identity

    def _save_identity(self) -> None:
        value = self.identity.model_dump(mode="json")
        value["api_key"] = self.identity.api_key.get_secret_value()
        _write_json(self.identity_path, value)

    def set_session_id(self, session_id: str) -> None:
        """Restore the ledger's logical question session before opening requests."""
        self._identity = Identity.model_validate({**self.identity.model_dump(), "session_id": session_id})
        self._save_identity()

    def resume_from(self, position: dict[str, int]) -> None:
        """Restore exactly the ledger's committed position before opening a socket."""
        self._identity = Identity.model_validate({**self.identity.model_dump(), "position": position,
            "cursor": position.get("s", 0)})
        self._save_identity()

    @property
    def _agent_path(self) -> str:
        return "/agents/" + quote(self.identity.agent_id, safe="")

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.identity.api_key.get_secret_value()}",
            "X-Switch-Connection-Id": self.identity.connection_id}

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.is_error:
            raise SwitchError(f"Switch request refused (HTTP {response.status_code})",http_status=response.status_code)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._taken_over:
            raise TakenOver("Switch connection was taken over; coordinator stopped")
        return await self._exchange(method, path, headers=self._headers, **kwargs)

    async def _exchange(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self.http.stream(method, self.base_url + path, **kwargs) as response:
            self._check(response)
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 4 * 1024 * 1024:
                    raise SwitchError("Switch response exceeds the 4 MiB limit")
            try:
                # Decode once after collecting chunks; never decode partial UTF-8.
                return require_unicode(json.loads(body.decode('utf-8', errors='strict')))
            except (ValueError, UnicodeDecodeError) as exc:
                raise SwitchError("Switch returned invalid JSON") from exc

    async def aclose(self) -> None:
        if self._reader is not None:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)
        if self._owns_http:
            await self.http.aclose()

    async def operation(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        envelope = await self._request("POST", self._agent_path + "/ops/" + quote(name, safe=""),
            json=arguments or {})
        return OperationEnvelope.model_validate(envelope).result

    async def list_operations(self) -> Any:
        return await self._request("GET", self._agent_path + "/ops")

    async def list_references(self) -> dict[str, Any]:
        self._require_production()
        return await self.operation("list_references")

    async def load_internal_documents(self, ids: list[str]) -> list[InternalDocument]:
        self._require_production()
        return [InternalDocument.model_validate(row) for row in
                await self.operation("load_internal_documents", {"ids": ids})]

    async def connect_to_production(self, room_id: str) -> dict[str, Any]:
        result = await self.operation("connect_to_room", {"room_id": room_id})
        self.production_room_id = room_id
        return result

    def _require_production(self) -> str:
        if not self.production_room_id:
            raise SwitchError("production room context is required")
        return self.production_room_id

    async def create_room_document(self, name: str, description: str, instructions: str,
                                   content: str) -> DocumentResult:
        self._require_production()
        result = await self.operation("create_room_document", {
            "name": name, "description": description, "instructions": instructions, "content": content})
        return DocumentResult.model_validate(result)

    async def update_room_document(self, document_id: str, content: str | None = None,
                                   **fields: str) -> DocumentResult:
        self._require_production()
        arguments = {"document_id": document_id, **fields}
        if content is not None:
            arguments["content"] = content
        return DocumentResult.model_validate(await self.operation("update_room_document", arguments))

    async def list_roles(self) -> list[RoomRole]:
        self._require_production()
        return [RoomRole.model_validate(row) for row in await self.operation("list_roles")]

    async def send_role_message(self, role: str, body: str,
                                expected_holder: str | None = None,
                                before_send: Callable[[], bool] | None = None) -> TargetedMessage:
        roles = await self.list_roles()
        selected = next((row for row in roles if row.name == role), None)
        holders = selected.held_by if selected else []
        if not holders or any(not holder.present_here for holder in holders):
            raise RoleUnavailable(f"role {role} has no available production-room holder")
        names = {holder.name for holder in holders}
        if expected_holder and names != {expected_holder}:
            raise RoleUnavailable(f"role {role} is not held by the expected worker")
        if before_send is not None and not before_send():
            raise StaleOperation("delegation was superseded during its presence check")
        result = TargetedMessage.model_validate(await self.operation("send_targeted_message",
            {"body": body, "target_roles": [role]}))
        if not names.issubset(result.target_statuses) or any(
            result.target_statuses[name] != "live" for name in names):
            raise RoleUnavailable(f"role {role} delivery has no confirmed live permitted target")
        return result

    async def send_message(self, room_id: str, body: str) -> MessageReceipt:
        return MessageReceipt.model_validate(await self._request("POST", self._agent_path + "/message",
            json={"room_id": room_id, "content": body}))

    async def send_media(self, room_id: str, path: str | Path, caption: str | None = None,
                         thread_id: str | None = None) -> dict[str, Any]:
        source = Path(path)
        data = {key: value for key, value in {"caption": caption, "thread_id": thread_id}.items()
                if value is not None}
        with source.open("rb") as stream:
            return await self._request("POST", self._agent_path + "/rooms/" + quote(room_id, safe="") + "/media",
                data=data, files={"file": (source.name, stream,
                    mimetypes.guess_type(source.name)[0] or "application/octet-stream")})

    async def upload_media(self, room_id: str, path: str | Path, caption: str | None = None,
                           thread_id: str | None = None) -> dict[str, Any]:
        return await self.send_media(room_id, path, caption, thread_id)

    async def create_room_from_yaml(self, yaml: str, inputs: dict[str, Any] | None = None) -> RoomProvision:
        return RoomProvision.model_validate(await self.operation("create_room_from_yaml",
            {"yaml": yaml, "inputs": inputs or {}}))

    def question_payload(self, title: str, prompt: str, options: list[QuestionOption],
                         expires_at: datetime, request_id: str | None = None,
                         turn_id: str | None = None) -> QuestionPayload:
        return QuestionPayload(request_id=request_id or str(uuid4()), turn_id=turn_id or str(uuid4()),
            title=title, room_id=self._require_production(), expires_at=expires_at,
            questions=[Question(title=title, prompt=prompt, options=options)])

    def _questions(self) -> dict[str, Any]:
        if not self.question_path.exists():
            return {}
        return json.loads(self.question_path.read_text(encoding="utf-8"))

    def _approval_path(self, request_id: str | None = None, session_id: str | None = None) -> str:
        path = "/agent-sessions/" + quote(session_id or self.identity.session_id, safe="") + "/approvals"
        return path if request_id is None else path + "/" + quote(request_id, safe="")

    async def open_question(self, payload: QuestionPayload) -> ApprovalOutcome:
        questions = self._questions()
        exact = payload.model_dump(mode="json")
        key = self.identity.session_id + ":" + payload.request_id
        if key in questions and questions[key] != exact:
            raise ValueError("question payload is immutable for a request identity")
        questions[key] = exact
        _write_json(self.question_path, questions)
        return ApprovalOutcome.model_validate(await self._request("POST", self._approval_path(), json=exact))

    async def retry_question(self, request_id: str) -> ApprovalOutcome:
        key = self.identity.session_id + ":" + request_id
        exact = self._questions()[key]
        return ApprovalOutcome.model_validate(await self._request("POST", self._approval_path(), json=exact))

    async def get_outcomes(self) -> list[ApprovalOutcome]:
        return [ApprovalOutcome.model_validate(row) for row in
            await self._request("GET", "/agent-sessions/approvals/outcomes")]

    async def mark_delivered(self, request_id: str, session_id: str | None = None) -> ApprovalOutcome:
        """Call only after the ledger commits processing, including rejected answers."""
        return ApprovalOutcome.model_validate(await self._request("POST",
            self._approval_path(request_id, session_id) + "/delivered"))

    async def close_question(self, request_id: str, session_id: str | None = None) -> ApprovalOutcome:
        return ApprovalOutcome.model_validate(await self._request("POST",
            self._approval_path(request_id, session_id) + "/close"))

    def mark_processed(self, frame: SwitchFrame) -> None:
        """Persist progress after the caller's inbox/state transaction commits."""
        position = frame.data.get("position")
        if frame.event == "gap" and "resumed_position" in frame.data:
            self.identity.position = dict(frame.data["resumed_position"])
        elif isinstance(position, dict):
            for source, seq in position.items():
                self.identity.position[source] = max(self.identity.position.get(source, 0), seq)
        elif frame.id is not None:
            self.identity.position["s"] = max(self.identity.position.get("s", 0), frame.id)
        if frame.id is not None:
            self.identity.cursor = frame.id
        if frame.event == "connection_state" and isinstance(frame.data.get("generation"), int):
            self.identity.generation = frame.data["generation"]
        self._save_identity()

    def _socket_url(self) -> str:
        parts = urlsplit(self.base_url)
        params = {"connection_id": self.identity.connection_id, "scope": "all", "filter": "all",
            "protocol": "9", "protocol_accepts": "9", "client": "take-two-coordinator",
            "start_at": json.dumps(self.identity.position, separators=(",", ":"))
                if self.identity.position else "head"}
        if self.production_room_id:
            params["rooms"] = self.production_room_id
        if self.identity.generation is not None:
            params["expected_generation"] = str(self.identity.generation)
        return urlunsplit(("wss" if parts.scheme == "https" else "ws", parts.netloc,
            parts.path + self._agent_path + "/connection/ws", urlencode(params), ""))

    async def _read_socket(self, queue: asyncio.Queue[SwitchFrame | BaseException]) -> None:
        attempts = 0
        try:
            while True:
                try:
                    async with self._connect(self._socket_url(), additional_headers=self._headers,
                            open_timeout=15, max_size=2**20) as socket:
                        async for raw in socket:
                            frame = SwitchFrame.model_validate_json(raw)
                            if frame.event == "ping":
                                await socket.send(json.dumps({"type": "pong",
                                    "cursor": self.identity.cursor or 0, "position": self.identity.position}))
                                continue
                            code = frame.data.get("code")
                            detail = frame.data.get("detail")
                            if isinstance(detail, dict):
                                code = detail.get("code", code)
                            if code == "taken_over":
                                self._taken_over = True
                                raise TakenOver("Switch connection was taken over; coordinator stopped")
                            if frame.event=='evicted' and code=='heartbeat_lapsed':
                                self.on_transport_lost()
                                raise OSError('Switch heartbeat lapsed; bounded reconnect required')
                            if frame.event == "refused":
                                status = frame.data.get("status")
                                if isinstance(status, int) and (status == 429 or status >= 500):
                                    raise OSError("Switch is temporarily unavailable")
                                raise SwitchError(f"Switch socket refused (status {status})")
                            # The opening baseline precedes catch-up, so storing it cannot skip an event.
                            if frame.event == "connection_state":
                                self.mark_processed(frame)
                            queue.put_nowait(frame)
                    raise OSError("Switch stream closed")
                except (OSError, ConnectionClosed) as exc:
                    self.on_transport_lost()
                    if attempts >= self.max_reconnects:
                        raise ConnectionError("Switch reconnect limit reached") from exc
                    await asyncio.sleep(min(self.reconnect_delay * 2**attempts, 15))
                    attempts += 1
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            self.on_transport_lost()
            await queue.put(exc)

    async def events(self) -> AsyncIterator[SwitchFrame]:
        """Stream frames with pings handled independently from application work.

        Gap, evicted, subscription_changed and unknown frames remain visible to
        the caller. A gap requires history reconciliation before acting again.
        Every frame must be marked processed only after durable application work.
        """
        await self.initialize()
        if self._taken_over:
            raise TakenOver("Switch connection was taken over; coordinator stopped")
        if self._reader is not None and not self._reader.done():
            raise SwitchError("only one event consumer is allowed per client")
        queue: asyncio.Queue[SwitchFrame | BaseException] = asyncio.Queue(maxsize=256)
        self._reader = asyncio.create_task(self._read_socket(queue))
        try:
            while True:
                item = await queue.get()
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)
