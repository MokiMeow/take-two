"""Bounded durable effects. A remote timeout never implies that a post was absent."""
from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

from coordinator.ledger import Ledger
from coordinator.render_bridge import RenderBridge
from coordinator.switch_client import StaleOperation, SwitchClient, SwitchError
from coordinator.switch_models import QuestionPayload
from coordinator.render_props import preview_props, callsheet_props, release_text


class ObsoleteEffect(Exception):
    """An input revision changed before an external side effect started."""


class PausedDispatch(Exception):
    """The event stream must catch up before any further effects are sent."""


class Dispatcher:
    def __init__(self, ledger: Ledger, loop: Any, client: SwitchClient, *,
                 production_room_id: str, crew_room_ids: list[str], renderer: RenderBridge,
                 retry_delay: float = 0.5, network_timeout: float = 45,
                 enabled: Callable[[], bool] = lambda: True) -> None:
        self.ledger, self.loop, self.client = ledger, loop, client
        self.production_room_id = production_room_id
        self.crew_room_ids = list(dict.fromkeys(crew_room_ids))[:20]
        self.renderer = renderer
        self.retry_delay = min(max(retry_delay, 0), 5)
        self.network_timeout = min(max(network_timeout, 1), 120)
        self.enabled = enabled
        self._lock = asyncio.Lock()
        self._recovered = False

    def _current(self, effect: dict) -> None:
        if not self.enabled():
            raise PausedDispatch()
        if not self.loop.effect_current(effect):
            raise ObsoleteEffect()

    def _notice(self, text: str, ref: str | None = None, *, broadcast: bool = True) -> None:
        with self.ledger.transaction():
            self.ledger.timeline('error', text, ref)
            if broadcast and self.production_room_id:
                digest = hashlib.sha256(text.encode()).hexdigest()[:24]
                self.ledger.enqueue('message', dict(body=text, room_id=self.production_room_id),
                    f'notice:{ref}:{digest}', 0)

    async def _network(self, effect: dict, operation: Callable[[], Awaitable]) -> Any:
        async def invoke() -> Any:
            # The task checks at its own start, immediately before entering the transport.
            self._current(effect)
            return await operation()
        task = asyncio.create_task(invoke())
        try:
            async with asyncio.timeout(self.network_timeout):
                while not task.done():
                    await asyncio.wait({task}, timeout=0.25)
                    if not task.done() and (not self.enabled() or not self.loop.effect_current(effect)):
                        # Cancellation cannot retract a post that reached the remote server.
                        raise TimeoutError('Publication invalidated while delivery was in flight.')
                return task.result()
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    async def _render(self, effect: dict, kind: str, manifest: dict, props: dict) -> Any:
        task = asyncio.create_task(self.renderer.render(kind, manifest, props))
        try:
            async with asyncio.timeout(min(getattr(self.renderer, 'timeout', 120), 300)):
                while not task.done():
                    await asyncio.wait({task}, timeout=0.25)
                    self._current(effect)
                return task.result()
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    def _path(self, value: str | Path, suffix: str) -> Path:
        root = self.renderer.artifacts_dir.resolve()
        path = Path(value).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != suffix:
            raise ValueError('Artifact must be a matching media file inside the artifacts directory.')
        if not 0 < path.stat().st_size <= 32 * 1024 * 1024:
            raise ValueError('Artifact has an invalid size.')
        # Reject disguised placeholders as well as obvious wrong extensions.
        with path.open('rb') as stream:
            header = stream.read(16)
        if suffix == '.png' and not header.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Call sheet is not PNG media.')
        if suffix == '.mp4' and header[4:8] != b'ftyp':
            raise ValueError('Preview is not MP4 media.')
        return path

    def _preview_path(self, url: str) -> Path:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not parsed.path.startswith('/media/'):
            raise ValueError('Preview must identify local rendered media.')
        name = unquote(parsed.path[len('/media/'):])
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Preview media path is invalid.')
        return self._path(self.renderer.artifacts_dir / name, '.mp4')

    def _enqueue(self, kind: str, payload: dict, key: str, effect: dict) -> str:
        return self.ledger.enqueue(kind, payload, key, effect['revision'])

    def _record_artifact(self, effect: dict, path: Path, kind: str) -> None:
        digest = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
        with self.ledger.transaction():
            self.ledger.put('renders', kind + ':' + effect['key'], dict(path=str(path), kind=kind,
                manifest_hash=effect['payload'].get('manifest_hash'), artifact_hash=digest), 'ready', effect['revision'])
            release_id = effect['payload'].get('release_id')
            if kind == 'callsheet' and release_id:
                state = self.ledger.snapshot_state()
                for release in state['releases']:
                    if release['release_id'] == release_id:
                        release['call_sheet_url'] = '/media/' + path.name
                self.ledger.save_state(state)

    async def _release(self, effect: dict) -> None:
        payload = effect['payload']
        release_id = payload['release_id']
        destinations = payload.get('destinations', self.crew_room_ids)
        if not destinations:
            self._notice(f'{release_id}: no crew destinations configured; release remains approved.', release_id)
            raise ValueError('No crew destinations configured.')
        notice = ''
        call_sheet: Path | None = None
        try:
            envelope = payload['envelope']
            result = await self._render(effect, 'callsheet', envelope['manifest'], callsheet_props(envelope))
            self._current(effect)
            if result.placeholder or result.manifest_hash!=payload['manifest_hash']:
                raise ValueError('Call sheet is a placeholder or has the wrong manifest identity.')
            call_sheet = self._path(result.path, '.png')
            self._record_artifact(effect, call_sheet, 'callsheet')
        except ObsoleteEffect:
            raise
        except Exception as error:
            self._current(effect)
            notice = ' Call sheet unavailable; use the complete text plan below.'
            self._notice(f'{release_id}: call sheet unavailable ({str(error)[:512]}); publishing a text plan.', release_id)
        preview: Path | None = None
        if payload.get('preview_url'):
            try:
                preview = self._preview_path(payload['preview_url'])
            except (OSError, ValueError):
                notice += ' Preview unavailable.'
                self._notice(f'{release_id}: approved preview file is unavailable.', release_id)
        body = self._release_text(payload) + notice
        self._current(effect)
        with self.ledger.transaction():
            for room in destinations:
                previous = None
                for label, path in (('callsheet', call_sheet), ('preview', preview)):
                    if path is not None:
                        previous = self._enqueue('publication_media', dict(release_id=release_id,
                            room_id=room, path=str(path), media_kind=label, depends_on=previous),
                            f'{release_id}:{room}:{label}', effect)
                self._enqueue('publication_text', dict(release_id=release_id, room_id=room,
                    body=body, depends_on=previous), f'{release_id}:{room}:text', effect)
            self.ledger.effect_status(effect['id'], 'sent')

    @staticmethod
    def _release_text(payload: dict) -> str:
        return release_text(payload['envelope'])

    async def _preview(self, effect: dict) -> None:
        p = effect['payload']
        url, status = None, 'failed'
        try:
            candidate, metadata = p['candidate'], p['metadata']
            scene = next(s for s in metadata['scenes'] if s['id']==candidate['manifest']['scene_id'])
            props = preview_props(candidate,candidate['letter'],scene,metadata['crew'])
            result = await self._render(effect, 'preview', p['manifest'], props)
            self._current(effect)
            if result.placeholder or result.manifest_hash != p['manifest_hash']:
                raise ValueError('Preview is a placeholder or does not match the candidate.')
            path = self._path(result.path, '.mp4')
            self._record_artifact(effect, path, 'preview')
            url, status = f'/media/{path.name}', 'ready'
        except ObsoleteEffect:
            raise
        except Exception as error:
            self._current(effect)
            self._notice(f"{p['candidate_id']}: preview unavailable ({str(error)[:512]}); option remains text only.", p['candidate_id'])
        await self.loop.preview_result(p['candidate_id'], p['manifest_hash'], url, status)

    async def _document(self, effect: dict) -> None:
        p = effect['payload']
        document_id = self.ledger.get_meta('doc:' + p['name'])
        if document_id is None:
            references = await self._network(effect, self.client.list_references)
            matches = [row for row in references.get('documents', []) if row.get('name') == p['name']]
            if matches:
                if len(matches) != 1 or matches[0].get('created_by_agent_id') != self.client.identity.agent_id:
                    raise ValueError('Canonical document name is owned by another identity.')
                document_id = matches[0]['id']
        if document_id is None:
            result = await self._network(effect, lambda: self.client.create_room_document(p['name'],
                'Take Two canonical production facts', 'Read before answering coordinator jobs.', p['content']))
        else:
            result = await self._network(effect, lambda: self.client.update_room_document(document_id, content=p['content']))
        with self.ledger.transaction():
            self.ledger.set_meta('doc:' + p['name'], result.document_id)

    async def _present_options(self, effect: dict) -> None:
        """Attachments and checked summaries precede the card, with durable receipts.

        An uncertain upload is never retried automatically. It leaves this effect
        uncertain, so a question cannot claim a preview the director has not seen.
        """
        for option in effect['payload'].get('presentations',[]):
            key = f"presentation:{effect['key']}:{option['candidate_id']}"
            if self.ledger.get_meta(key):
                continue
            if option.get('preview_url'):
                try:
                    receipt = await self._network(effect,lambda: self.client.send_media(self.production_room_id,
                        self._preview_path(option['preview_url']),caption=option['summary']))
                except (httpx.TransportError,TimeoutError,ConnectionError):
                    with self.ledger.transaction():
                        self.ledger.set_meta('presentation_uncertain:'+effect['id'],True)
                    raise
            else:
                suffix = ' Preview unavailable; text only.' if option.get('preview_required',True) else ' Initial schedule approval; no creative preview requested.'
                receipt = await self._network(effect,lambda: self.client.send_message(self.production_room_id,
                    option['summary']+suffix))
            with self.ledger.transaction():
                self.ledger.set_meta(key,receipt.model_dump() if hasattr(receipt,'model_dump') else receipt)

    async def _dispatch(self, effect: dict) -> Any:
        kind, p = effect['kind'], effect['payload']
        if kind == 'hold':
            with self.ledger.transaction():
                for room in self.crew_room_ids or [self.production_room_id]:
                    self._enqueue('hold_message', dict(**p, room_id=room), f"{effect['key']}:{room}", effect)
                self.ledger.effect_status(effect['id'], 'sent')
        elif kind in ('hold_message', 'publication_text', 'message'):
            return await self._network(effect, lambda: self.client.send_message(p.get('room_id', self.production_room_id), p['body']))
        elif kind == 'publication_media':
            path = self._path(p['path'], '.png' if p['media_kind'] == 'callsheet' else '.mp4')
            await self._network(effect, lambda: self.client.send_media(p['room_id'], path, caption=f"Release {p['release_id']}"))
        elif kind == 'role_message':
            await self._network(effect, lambda: self.client.send_role_message(p['role'], p['body'],
                expected_holder=p.get('expected_holder'), before_send=lambda: self.enabled() and self.loop.effect_current(effect)))
        elif kind == 'document':
            await self._document(effect)
        elif kind == 'open_question':
            await self._present_options(effect)
            payload = QuestionPayload.model_validate(p['payload'])
            await self._network(effect, lambda: self.client.open_question(payload))
        elif kind in ('close_question', 'mark_delivered'):
            operation = getattr(self.client, kind)
            await self._network(effect, lambda: operation(p['request_id'], session_id=p.get('session_id')))
        elif kind == 'release':
            await self._release(effect)
        elif kind == 'preview':
            await self._preview(effect)
        else:
            raise ValueError('Unsupported outbox effect kind.')

    def _dependency_ready(self, effect: dict) -> bool:
        dependency = effect['payload'].get('depends_on')
        if not dependency:
            return True
        predecessor = self.ledger.effect(dependency)
        return bool(predecessor and predecessor['status'] == 'sent')

    async def _publication(self, effect: dict, status: str) -> None:
        if effect['kind'] not in ('publication_media', 'publication_text'):
            return
        p = effect['payload']
        # Only completion of the final text step marks the room sent.
        if status == 'sent' and effect['kind'] != 'publication_text':
            return
        await self.loop.publication_result(p['release_id'], p['room_id'], status)
        if status == 'sent':
            callbacks = self.ledger.get_meta('publication_callbacks', [])
            if effect['id'] in callbacks:
                with self.ledger.transaction():
                    self.ledger.set_meta('publication_callbacks', [item for item in callbacks if item != effect['id']])

    async def _recover(self) -> None:
        if self._recovered:
            return
        self._recovered = True
        for effect_id in self.ledger.get_meta('publication_callbacks', [])[:1000]:
            effect = self.ledger.effect(effect_id)
            if effect and effect['status'] == 'sent':
                await self._publication(effect, 'sent')
        safe = ('hold', 'release', 'preview', 'document', 'close_question', 'mark_delivered')
        for effect in self.ledger.effects('uncertain'):
            if effect['kind'] in safe and effect['attempts'] < 2:
                self.ledger.effect_status(effect['id'], 'pending')
            else:
                self._notice(f"{effect['kind']} has uncertain delivery after restart; review before retrying.",
                    effect['payload'].get('release_id'), broadcast=effect['kind'] != 'message')
                await self._publication(effect, 'uncertain')

    async def run_once(self, limit: int = 20) -> int:
        """Process at most 100 effects per call, including newly materialized effects."""
        async with self._lock:
            if not self.enabled():
                return 0
            await self._recover()
            completed = 0
            for _ in range(min(max(limit, 0), 100)):
                pending = sorted(self.ledger.pending_effects(),
                    key=lambda item: item['kind'] not in ('hold', 'hold_message'))
                effect = next((item for item in pending
                    if not self.loop.effect_current(item) or self._dependency_ready(item)), None)
                if effect is None:
                    break
                try:
                    self._current(effect)
                except PausedDispatch:
                    return completed
                except ObsoleteEffect:
                    self.ledger.effect_status(effect['id'], 'cancelled')
                    completed += 1
                    continue
                safe = effect['kind'] in ('document', 'open_question', 'close_question', 'mark_delivered')
                for attempt in range(2 if safe else 1):
                    self.ledger.effect_status(effect['id'], 'sending')
                    try:
                        receipt = await self._dispatch(effect)
                    except PausedDispatch:
                        self.ledger.effect_status(effect['id'], 'pending')
                        return completed
                    except (ObsoleteEffect, StaleOperation):
                        if not self.enabled():
                            self.ledger.effect_status(effect['id'], 'pending')
                            return completed
                        self.ledger.effect_status(effect['id'], 'cancelled')
                        break
                    except asyncio.CancelledError:
                        # sending remains durable; restart will classify it as uncertain.
                        raise
                    except Exception as error:
                        transient = isinstance(error, (httpx.TransportError, TimeoutError, ConnectionError))
                        if safe and transient and attempt == 0 and effect['attempts'] < 1 and not self.ledger.get_meta('presentation_uncertain:'+effect['id']) and self.enabled() and self.loop.effect_current(effect):
                            await asyncio.sleep(self.retry_delay)
                            continue
                        status = 'uncertain' if transient else 'failed'
                        code=getattr(error,'http_status',None)
                        diagnostic=type(error).__name__+(f' HTTP {code}' if code else '')
                        if isinstance(error,SwitchError):
                            diagnostic+=': '+str(error)[:160]
                        destination=effect['payload'].get('room_id') or self.production_room_id
                        destination=getattr(self.loop,'room_names',{}).get(destination, 'Crew room')
                        self.ledger.effect_status(effect['id'], status, error=diagnostic)
                        self._notice(f"{effect['kind']} {status} ({diagnostic}, room {destination}); review before retrying.",
                            effect['payload'].get('release_id') or effect['payload'].get('job_id'),
                            broadcast=effect['kind'] != 'message')
                        await self._publication(effect, status)
                        break
                    else:
                        with self.ledger.transaction():
                            self.ledger.effect_status(effect['id'], 'sent')
                            if effect['kind'] == 'publication_text' and receipt is not None:
                                self.ledger.set_meta('publication_message:' + receipt.event_id, effect['payload']['release_id'])
                                callbacks = self.ledger.get_meta('publication_callbacks', [])
                                self.ledger.set_meta('publication_callbacks', [*callbacks, effect['id']])
                        await self._publication(effect, 'sent')
                        break
                completed += 1
            return completed

    async def run(self, stop: asyncio.Event | None = None) -> None:
        stop = stop or asyncio.Event()
        while not stop.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.25)
            except TimeoutError:
                pass
