"""Live wiring. Missing server/credentials stays visible without simulated workers."""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import hashlib
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field
import yaml

from coordinator.commands import parse_command
from coordinator.config import Settings
from coordinator.constraints import Constraints
from coordinator.dispatcher import Dispatcher
from coordinator.ledger import Ledger, now_iso
from coordinator.loop import Loop
from coordinator.render_bridge import RenderBridge
from coordinator.switch_client import SwitchClient, TakenOver
from coordinator.switch_models import ApprovalOutcome, SwitchFrame
from coordinator.ui_models import ChangeCommand, State

ROOT = Path(__file__).resolve().parent.parent


class ScriptScene(BaseModel):
    id: str
    number: int
    title: str
    hard: list[str]
    preferences: list[str]


class Script(BaseModel):
    title: str
    timezone: str
    shoot_day: str
    script_rev: int
    scenes: list[ScriptScene] = Field(max_length=200)


class CrewPerson(BaseModel):
    id: str
    name: str
    role: str
    switch_identity: str


class Crew(BaseModel):
    production_id: str
    crew: list[CrewPerson] = Field(max_length=500)


class ChatPayload(BaseModel):
    sender: str = Field(max_length=512)
    sender_kind: str | None = None
    sender_name: str = Field(default='', max_length=512)
    body: str = Field(max_length=8192)
    message_id: str = Field(max_length=512)
    thread_id: str | None = Field(default=None, max_length=512)


class ChatEvent(BaseModel):
    room_id: str = Field(max_length=512)
    payload: ChatPayload


class CommandPayload(BaseModel):
    command: str = Field(max_length=512)
    args: str = Field(default='', max_length=8192)
    user_id: str = Field(max_length=512)
    user_name: str = Field(default='', max_length=512)


class CommandEvent(BaseModel):
    room_id: str = Field(max_length=512)
    payload: CommandPayload


def read_yaml(name: str) -> Any:
    path = ROOT / 'fixtures/film' / name
    if path.stat().st_size > 262144:
        raise ValueError('Film configuration exceeds 256 KiB.')
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def initial_state() -> dict:
    script = Script.model_validate(read_yaml('script.yaml'))
    crew = Crew.model_validate(read_yaml('crew.yaml'))
    # Fixture approvals are illustrative. A live database begins with no claimed human decision.
    state = dict(production=dict(id=crew.production_id, title=script.title, timezone=script.timezone,
                 now=now_iso(), day=script.shoot_day), revisions=dict(script=script.script_rev, constraints=1),
                 scenes=[dict(**scene.model_dump(), validity='held', hold_reason='Awaiting reviewed initial schedule')
                         for scene in script.scenes], changes=[], jobs=[], decision=None, releases=[],
                 crew=[dict(id=p.id, name=p.name, role=p.role) for p in crew.crew], timeline=[])
    return State.model_validate(state).model_dump(mode='json')


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ledger = Ledger(settings.take_two_db, initial_state=initial_state())
        self.client = SwitchClient(settings.switch_api_url, settings.take_two_identity,
            settings.switch_registration_key.get_secret_value(),
            production_room_id=settings.switch_production_room_id or None)
        self.renderer = RenderBridge(settings.take_two_artifacts, cli=ROOT/'render/cli.mjs',
                                     timeout=settings.take_two_render_timeout)
        facts = Constraints.model_validate(read_yaml('constraints-r1.yaml'))
        self.loop = Loop(self.ledger, None, facts, renderer=self.renderer,
            authorities={'creative': [settings.take_two_director_id] if settings.take_two_director_id else [],
                         'location_permission': [settings.take_two_producer_id] if settings.take_two_producer_id else [],
                         'safety': [settings.take_two_safety_id] if settings.take_two_safety_id else [],
                         'capability_verification': [settings.take_two_capability_authority_id] if settings.take_two_capability_authority_id else [],
                         'availability_confirmation': [settings.take_two_ad_id] if settings.take_two_ad_id else []},
            worker_ids={role: value for role, value in (
                ('script-supervisor', settings.take_two_supervisor_sender_id),
                ('first-ad', settings.take_two_ad_sender_id)) if value},
            worker_names={role: value for role,value in (
                ('script-supervisor', settings.take_two_supervisor_agent_name),
                ('first-ad', settings.take_two_ad_agent_name)) if value}, destinations=settings.crew_room_ids)
        crew = Crew.model_validate(read_yaml('crew.yaml'))
        self.crew_ids = {member.switch_identity: member.id for member in crew.crew}
        self.dispatcher: Dispatcher | None = None
        self.stop = asyncio.Event()
        self.tasks: list[asyncio.Task] = []
        self.ready = False
        source_script = read_yaml('script.yaml')
        self.source_mismatch = self.ledger.get_meta('source_script', source_script) != source_script
        with self.ledger.transaction():
            if self.ledger.get_meta('source_script') is None:
                self.ledger.set_meta('source_script', source_script)
        if self.source_mismatch:
            self.notice('Script fixture differs from the persisted script; restart reconciliation is paused.', visible=False)

    def notice(self, text: str, *, visible: bool = True) -> None:
        with self.ledger.transaction():
            self.ledger.timeline('error', text)
            if visible and self.ready and self.settings.switch_production_room_id:
                self.ledger.enqueue('message', dict(room_id=self.settings.switch_production_room_id, body=text),
                    f'notice:{datetime.now().timestamp()}', self.loop.constraints.constraints_rev)

    async def start(self) -> None:
        if self.source_mismatch:
            return
        if not self.settings.take_two_identity.exists() and not self.settings.switch_registration_key.get_secret_value():
            self.notice('Switch is disconnected: set a personal registration key in .env and restart.', visible=False)
            return
        try:
            await self.client.initialize()
            self.client.set_session_id(self.loop.session_id)
            position = self.ledger.get_meta('event_position')
            if position is not None:
                self.client.resume_from(position)
            self.loop.switch = self.client
            self.loop.coordinator_id = self.client.identity.agent_id
        except Exception as error:
            self.notice(f'Switch startup failed ({type(error).__name__}); check server and local credentials.', visible=False)
            return
        self.tasks = [asyncio.create_task(self.consume()), asyncio.create_task(self.service())]

    async def connected(self) -> None:
        self.ready = False
        room_id = self.settings.switch_production_room_id
        if not room_id:
            self.notice('Switch connected. Set SWITCH_PRODUCTION_ROOM_ID in .env to enable documents and decisions.', visible=False)
            return
        room = await self.client.connect_to_production(room_id)
        self.dispatcher = Dispatcher(self.ledger, self.loop, self.client,
            production_room_id=room_id, crew_room_ids=self.settings.crew_room_ids, renderer=self.renderer,
            enabled=lambda: self.ready)
        await self.reconcile_documents(room)
        for outcome in await self.client.get_outcomes():
            await self.loop.handle_outcome(outcome)
        self.ready = True

    async def reconcile_documents(self, room: dict) -> None:
        documents = room.get('documents') or []
        for name, content in (
            ('script-r1', json.dumps(self.ledger.get_meta('source_script'), ensure_ascii=False)),
            (f'constraints-r{self.loop.constraints.constraints_rev}', self.loop.constraints.model_dump_json())):
            matches = [doc for doc in documents if doc.get('name') == name]
            known = self.ledger.get_meta('document:' + name)
            if known or matches:
                document_id = known or matches[0]['id']
                await self.client.update_room_document(document_id, content)
            else:
                document = await self.client.create_room_document(name, 'Take Two canonical input',
                    'Coordinator-owned, revisioned facts. Agents read and propose; humans decide.', content)
                document_id = document.document_id
            with self.ledger.transaction():
                self.ledger.set_meta('document:' + name, document_id)

    async def consume(self) -> None:
        try:
            async for frame in self.client.events():
                if self.stop.is_set():
                    break
                if frame.event == 'connection_state':
                    await self.connected()
                elif frame.event in ('gap', 'evicted', 'subscription_changed'):
                    self.ready = False
                    self.notice('Switch history needs reconciliation; releases paused. Review history before restarting.', visible=False)
                    break
                await self.accept_frame(frame)
        except TakenOver:
            self.ready = False
            self.notice('Switch connection taken over. Coordinator stopped; restart only after resolving ownership.', visible=False)
            self.stop.set()
        except Exception as error:
            self.ready = False
            self.notice(f'Switch stream failed ({type(error).__name__}); releases paused.', visible=False)

    async def accept_frame(self, frame: SwitchFrame) -> None:
        """Stable dedupe and cursor are committed with the handler's state/effects."""
        serialized = frame.model_dump(mode='json')
        key = hashlib.sha256(json.dumps(serialized, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if self.ledger.has_event(key):
            return
        position = dict(frame.data.get('position') or {})
        if not position and frame.id is not None:
            position['s'] = frame.id
        with self.ledger.processing_event(key, position, serialized):
            try:
                await self.process_frame(frame)
            except Exception as error:
                self.notice(f'Event quarantined ({type(error).__name__}); no unvalidated action was applied.')
            if not self.ledger.has_event(key):
                with self.ledger.transaction():
                    self.ledger.record_event(key, position, serialized)
        self.client.mark_processed(frame)

    async def process_frame(self, frame: SwitchFrame) -> None:
        if frame.event == 'approval_outcome':
            await self.loop.handle_outcome(ApprovalOutcome.model_validate(frame.data))
            return
        if frame.event == 'command':
            command = CommandEvent.model_validate(frame.data)
            event = ChatEvent(room_id=command.room_id, payload=ChatPayload(sender=command.payload.user_id,
                sender_kind='user', body=command.payload.command if command.payload.command.startswith('/') else '/' + command.payload.command,
                message_id='command:' + hashlib.sha256(json.dumps(frame.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()))
            event.payload.body += (' ' + command.payload.args) if command.payload.args else ''
        elif frame.event == 'message':
            event = ChatEvent.model_validate(frame.data)
        else:
            return
        message = event.payload
        if message.sender == self.client.identity.agent_id:
            return
        if message.sender in self.loop.worker_ids.values():
            await self.loop.handle_worker_reply(message.body, sender_id=message.sender)
            return
        if message.sender_kind in ('agent', 'platform'):
            return
        crew_person = self.crew_ids.get(message.sender)
        confirmation = re.fullmatch(r'confirm\s+(r[1-9][0-9]{0,5})', message.body.strip(), re.IGNORECASE)
        if crew_person and confirmation:
            if not await self.loop.confirm(crew_person, confirmation[1].lower()):
                await self.correct_stale_reply(event, confirmation[1].lower())
            return
        if crew_person:
            mentions = re.findall(r'\b(?:release\s*|r)([1-9][0-9]{0,5})\b', message.body, re.IGNORECASE)
            previous = self.ledger.get_meta('publication_message:' + message.thread_id) if message.thread_id else None
            referenced = previous or ('r' + mentions[0] if mentions else None)
            if referenced and await self.correct_stale_reply(event, referenced):
                return
        source = 'mattermost' if event.room_id == self.settings.switch_production_room_id else 'discord'
        parsed = parse_command(message.body, message.sender, message.message_id)
        if parsed.command:
            await self.loop.handle_change(ChangeCommand.model_validate(parsed.command.model_dump()),
                                          source=source, source_message_id=message.message_id)
            return
        await self.pending_report(event, source)

    async def correct_stale_reply(self, event: ChatEvent, referenced: str) -> bool:
        releases = self.ledger.snapshot_state()['releases']
        current = next((release for release in releases if release['status'] == 'published'), None)
        if not current or current['release_id'] == referenced:
            return False
        with self.ledger.transaction():
            text = f"That's release {referenced}. Current plan is release {current['release_id']}. {current['summary']} Please confirm {current['release_id']}."
            self.ledger.timeline('stale_reply', text, referenced)
            self.ledger.enqueue('message', dict(room_id=event.room_id, body=text),
                'stale:' + event.payload.message_id, self.loop.constraints.constraints_rev)
        return True

    async def handle_ui_change(self, command: ChangeCommand) -> dict:
        """The browser reports facts; only authenticated Switch identities confirm them."""
        from uuid import uuid4
        key = str(uuid4())
        state = self.ledger.snapshot_state()
        with self.ledger.transaction():
            state['changes'].insert(0, dict(**command.model_dump(), id=key, at=now_iso(),
                status='pending_confirmation', source='control_room'))
            state['changes'] = state['changes'][:200]
            self.ledger.save_state(state)
            self.ledger.timeline('change', 'Control Room report awaits confirmation by an authenticated Switch authority.', key)
            self.ledger.enqueue('message', dict(room_id=self.settings.switch_production_room_id,
                body=f'Report pending: {command.target} {command.field}. Confirm in Switch with the structured /change command.'),
                'ui-report:' + key, self.loop.constraints.constraints_rev)
        return dict(change_id=key, status='pending_confirmation', reason='Confirm this report in Switch using your authorized identity.')

    async def pending_report(self, event: ChatEvent, source: str) -> None:
        message = event.payload
        key = 'pending-report:' + message.message_id
        if self.ledger.get_meta(key):
            return
        state = self.ledger.snapshot_state()
        with self.ledger.transaction():
            state['changes'].insert(0, dict(id=key, at=now_iso(), reporter=message.sender, entity='scene',
                target='unconfirmed', field='report', value=message.body[:512], status='pending_confirmation', source=source))
            state['changes'] = state['changes'][:200]
            self.ledger.save_state(state)
            self.ledger.timeline('change', f'{message.sender} reported a change; structured confirmation is required.', key)
            self.ledger.set_meta(key, True)
            self.ledger.enqueue('message', dict(room_id=self.settings.switch_production_room_id or event.room_id,
                body='Report recorded as pending. An authorized person must confirm it with /change <entity> <target> <field> <value>.'),
                key, self.loop.constraints.constraints_rev)

    async def service(self) -> None:
        last_outcomes = asyncio.get_running_loop().time()
        while not self.stop.is_set():
            try:
                await self.loop.tick()
                if self.ready and self.dispatcher:
                    await self.dispatcher.run_once()
                    if asyncio.get_running_loop().time() - last_outcomes >= 15:
                        for outcome in await self.client.get_outcomes():
                            await self.loop.handle_outcome(outcome)
                        last_outcomes = asyncio.get_running_loop().time()
            except Exception as error:
                self.ready = False
                self.notice(f'Coordinator service failed ({type(error).__name__}); effects paused.', visible=False)
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=1)
            except TimeoutError:
                pass

    async def close(self) -> None:
        self.stop.set()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.client.aclose()
        self.ledger.close()
