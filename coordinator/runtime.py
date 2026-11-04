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
from coordinator.recovery import Recovery
from coordinator.rooms import DayRooms
from coordinator.presentation import role_label
from coordinator.render_props import hhmm
from coordinator.switch_text_answer import parse_text_answer

ROOT = Path(__file__).resolve().parent.parent


class ScriptScene(BaseModel):
    id: str = Field(min_length=1,max_length=64)
    number: int = Field(ge=1,le=999)
    title: str = Field(min_length=1,max_length=80)
    hard: list[str] = Field(max_length=40)
    preferences: list[str] = Field(max_length=40)
    people: list[str] = Field(max_length=8)
    required_capabilities: list[str] = Field(max_length=30)


class Script(BaseModel):
    title: str = Field(min_length=1,max_length=80)
    timezone: str
    shoot_day: str
    shoot_day_number: int = Field(ge=1, le=999)
    script_rev: int
    scenes: list[ScriptScene] = Field(max_length=20)


class CrewPerson(BaseModel):
    id: str = Field(min_length=1,max_length=64)
    name: str = Field(min_length=1,max_length=40)
    role: str = Field(min_length=1,max_length=60)
    switch_identity: str = Field(min_length=1,max_length=512)


class Crew(BaseModel):
    production_id: str
    crew: list[CrewPerson] = Field(max_length=30)
    humans: list[CrewPerson] = Field(default_factory=list, max_length=30)


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
                 now=now_iso(), day=f"Day {script.shoot_day_number} - {datetime.fromisoformat(script.shoot_day).day} {datetime.fromisoformat(script.shoot_day):%B}"), revisions=dict(script=script.script_rev, constraints=1),
                 scenes=[dict(**scene.model_dump(exclude={'people','required_capabilities'}), validity='held', hold_reason='Awaiting reviewed initial schedule')
                         for scene in script.scenes], changes=[], jobs=[], decision=None, releases=[],
                 crew=[dict(id=p.id, name=p.name, role=p.role, role_label=role_label(p.role)) for p in crew.crew], timeline=[])
    return State.model_validate(state).model_dump(mode='json')


class Runtime(Recovery, DayRooms):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ledger = Ledger(settings.take_two_db, initial_state=initial_state())
        self.client = SwitchClient(settings.switch_api_url, settings.take_two_identity,
            settings.switch_registration_key.get_secret_value(),
            production_room_id=settings.switch_production_room_id or None)
        self.renderer = RenderBridge(settings.take_two_artifacts, cli=settings.take_two_renderer_cli,
                                     timeout=settings.take_two_render_timeout)
        facts = Constraints.model_validate(read_yaml('constraints-r1.yaml'))
        script = Script.model_validate(read_yaml('script.yaml'))
        crew = Crew.model_validate(read_yaml('crew.yaml'))
        trusted = facts.model_dump(mode='json')
        for scene in trusted['scenes']:
            reviewed = next(s for s in script.scenes if s.id==scene['id'])
            scene.update(required_people=reviewed.people,required_capabilities=reviewed.required_capabilities)
        facts = Constraints.model_validate(trusted)
        metadata = dict(production=dict(title=script.title,day=f'Day {script.shoot_day_number}',
            date=f"{datetime.fromisoformat(script.shoot_day):%A} {datetime.fromisoformat(script.shoot_day).day} {datetime.fromisoformat(script.shoot_day):%B %Y}",
            timezone=script.timezone),scenes=[s.model_dump() for s in script.scenes],
            crew=[p.model_dump(exclude={'switch_identity'}) for p in crew.crew])
        self.loop = Loop(self.ledger, None, facts, renderer=self.renderer,
            authorities={'creative': [settings.take_two_director_id] if settings.take_two_director_id else [],
                         'location_permission': [settings.take_two_producer_id] if settings.take_two_producer_id else [],
                         'safety': [settings.take_two_safety_id] if settings.take_two_safety_id else [],
                         'capability_verification': list(filter(None,[settings.take_two_ad_id, settings.take_two_capability_authority_id])),
                         'overrun_confirmation': list(filter(None,[settings.take_two_ad_id, settings.take_two_script_supervisor_id])),
                         'availability_confirmation': [settings.take_two_ad_id] if settings.take_two_ad_id else []},
            worker_ids={role: value for role, value in (
                ('script-supervisor', settings.take_two_supervisor_sender_id),
                ('first-ad', settings.take_two_ad_sender_id)) if value},
            worker_names={role: value for role,value in (
                ('script-supervisor', settings.take_two_supervisor_agent_name),
                ('first-ad', settings.take_two_ad_agent_name)) if value}, destinations=settings.crew_room_ids,
            metadata=metadata,destination_platforms={settings.switch_production_room_id:'mattermost'})
        crew = Crew.model_validate(read_yaml('crew.yaml'))
        self.crew_ids = {member.switch_identity: member.id for member in crew.crew}
        if not set(settings.take_two_crew_identities.values()) <= {p.id for p in crew.crew}:
            raise ValueError('Configured crew identities must map to reviewed crew IDs')
        self.crew_ids.update(settings.take_two_crew_identities)
        self.loop.crew_ids = self.crew_ids
        self.loop.production_date = script.shoot_day
        people = {p.id: p for p in [*crew.crew, *crew.humans]}
        self.loop.identity_names = {p.switch_identity: p.name for p in people.values()}
        self.loop.identity_roles = {p.switch_identity: p.role for p in people.values()}
        aliases = {**self.crew_ids, **{key: value for key, value in (
            (settings.take_two_director_id, 'arun'), (settings.take_two_producer_id, 'producer'),
            (settings.take_two_ad_id, 'first-ad-human')) if key}}
        for identity, person_id in aliases.items():
            self.loop.identity_names[identity] = people[person_id].name
            self.loop.identity_roles[identity] = people[person_id].role
        self.loop.room_names = {room: '#crew' for room in settings.crew_room_ids}
        self.loop.room_names.update({settings.switch_production_room_id: '#production', **settings.take_two_room_names})
        self.dispatcher: Dispatcher | None = None
        self.stop = asyncio.Event()
        self.tasks: list[asyncio.Task] = []
        self.ready = False
        self.transport_epoch = 0
        self.catching_up = True
        self.client.on_transport_lost = self.transport_lost
        source_script = read_yaml('script.yaml')
        self.source_mismatch = self.ledger.get_meta('source_script', source_script) != source_script
        with self.ledger.transaction():
            if self.ledger.get_meta('source_script') is None:
                self.ledger.set_meta('source_script', source_script)
            if self.ledger.get_meta('history_since') is None:
                self.ledger.set_meta('history_since',now_iso())
        if self.source_mismatch:
            self.notice('Script fixture differs from the persisted script; restart reconciliation is paused.', visible=False)

    def notice(self, text: str, *, visible: bool = True) -> None:
        with self.ledger.transaction():
            self.ledger.timeline('error', text)
            if visible and self.settings.switch_production_room_id:
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
            self.client.resume_from(position or {})
            self.loop.switch = self.client
            self.loop.coordinator_id = self.client.identity.agent_id
        except Exception as error:
            self.notice(f'Switch startup failed ({type(error).__name__}); check server and local credentials.', visible=False)
            return
        self.tasks = [asyncio.create_task(self.consume()), asyncio.create_task(self.service())]

    async def connected(self) -> None:
        self.transport_lost()
        room_id = self.settings.switch_production_room_id
        if not room_id:
            self.notice('Switch connected. Set SWITCH_PRODUCTION_ROOM_ID in .env to enable documents and decisions.', visible=False)
            return
        room = await self.client.connect_to_production(room_id)
        self.dispatcher = Dispatcher(self.ledger, self.loop, self.client,
            production_room_id=room_id, crew_room_ids=self.settings.crew_room_ids, renderer=self.renderer,
            enabled=lambda: self.ready)
        await self.reconcile_documents(room)
        await self.provision_day()
        await self.begin_catchup()
        await self.finish_catchup()

    async def reconcile_documents(self, room: dict) -> None:
        documents = room.get('documents') or []
        for name, content in (
            ('script-r1', json.dumps(self.ledger.get_meta('source_script'), ensure_ascii=False)),
            (f'constraints-r{self.loop.constraints.constraints_rev}', self.loop.constraints.model_dump_json())):
            matches = [doc for doc in documents if doc.get('name') == name]
            known = self.ledger.get_meta('doc:' + name)
            if known or matches:
                document_id = known or matches[0]['id']
                await self.client.update_room_document(document_id, content)
            else:
                document = await self.client.create_room_document(name, 'Take Two canonical input',
                    'Coordinator-owned, revisioned facts. Agents read and propose; humans decide.', content)
                document_id = document.document_id
            with self.ledger.transaction():
                self.ledger.set_meta('doc:' + name, document_id)

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
                await self.finish_catchup()
        except TakenOver:
            self.ready = False
            self.notice('Switch connection taken over. Coordinator stopped; restart only after resolving ownership.', visible=False)
            self.stop.set()
        except Exception as error:
            self.transport_lost()
            self.notice(f'Switch consume failed ({type(error).__name__}); effects paused.',visible=False)

    async def accept_frame(self, frame: SwitchFrame) -> None:
        """Stable dedupe and cursor are committed with the handler's state/effects."""
        serialized = frame.model_dump(mode='json')
        frame_key = hashlib.sha256(json.dumps(serialized, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        message_id = frame.data.get('payload',{}).get('message_id') if frame.event=='message' else None
        key = f"message:{frame.data.get('room_id')}:{message_id}" if message_id else frame_key
        position = dict(frame.data.get('position') or {})
        if not position and frame.id is not None:
            position['s'] = frame.id
        if self.ledger.has_event(key):
            with self.ledger.transaction():
                self.ledger.record_event('cursor:'+frame_key,position,serialized)
            self.client.mark_processed(frame)
            return
        with self.ledger.processing_event(key, position, serialized):
            try:
                await self.process_frame(frame)
            except Exception as error:
                self.transport_lost()
                self.notice(f'Event quarantined ({type(error).__name__}); no unvalidated action was applied.')
            if not self.ledger.has_event(key):
                with self.ledger.transaction():
                    self.ledger.record_event(key, position, serialized)
        self.client.mark_processed(frame)

    async def process_frame(self, frame: SwitchFrame) -> None:
        if frame.event=='room_released':
            self.transport_lost()
            self.catchup_through=None
            self.notice('Switch room ownership was released; effects paused until reconnect.',visible=False)
            return
        if frame.event == 'approval_outcome':
            if self.ready:
                await self.loop.handle_outcome(ApprovalOutcome.model_validate(frame.data))
            return
        if frame.event == 'command':
            command = CommandEvent.model_validate(frame.data)
            event = ChatEvent(room_id=command.room_id, payload=ChatPayload(sender=command.payload.user_id,
                sender_kind='user', body=command.payload.command if command.payload.command.startswith('/') else '/' + command.payload.command,
                message_id='command:' + hashlib.sha256(json.dumps(frame.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()))
            event.payload.body += (' ' + command.payload.args) if command.payload.args else ''
        elif frame.event == 'message':
            raw = frame.data.get('payload',{})
            if raw.get('sender') in self.loop.worker_ids.values() and isinstance(raw.get('body'),str):
                await self.loop.handle_worker_reply(raw['body'],sender_id=raw['sender'])
                return
            event = ChatEvent.model_validate(frame.data)
        else:
            return
        message = event.payload
        if re.search(r"(?i)(failed to relay|couldn.t be relayed|attachment not relayed|incomplete attachment group|bridge delivery failed)",message.body):
            room_name = self.loop.room_names.get(event.room_id, 'Crew room')
            self.notice(f'Switch bridge delivery error observed in {room_name}; external delivery is unverified.')
        if message.sender in (self.client.identity.agent_id, self.loop.coordinator_id,
                              self.settings.take_two_coordinator_sender_id):
            return
        plan = re.fullmatch(r'/plan\s+(day-[1-9][0-9]{0,2})',message.body.strip())
        if plan:
            await self.loop.request_plan(plan[1],message.sender,message.message_id)
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
        if message.body.strip().startswith('/'):
            self.notice('Unrecognized or malformed command; use /change <entity> <target> <field> <value>.')
            return
        await self.pending_report(event, source)

    async def correct_stale_reply(self, event: ChatEvent, referenced: str) -> bool:
        releases = self.ledger.snapshot_state()['releases']
        current = next((release for release in releases if release['status'] == 'published'), None)
        if not current or current['release_id'] == referenced:
            return False
        with self.ledger.transaction():
            person = self.crew_ids.get(event.payload.sender)
            name = next((p['name'] for p in self.ledger.snapshot_state()['crew'] if p['id']==person), 'Crew')
            internal=self.loop.workflow['releases'].get(current['release_id'],{})
            m=internal.get('candidate',{}).get('manifest')
            detail=current['summary']
            if m:
                number=next(s['number'] for s in self.ledger.snapshot_state()['scenes'] if s['id']==m['scene_id'])
                detail=f"Scene {number} → {m['location']}, {hhmm(m['start'])}"
            text = f'@{name} that was release {referenced.removeprefix("r")}. The current plan is release {current["number"]} ({detail}). Please reply "confirm {current["release_id"]}".'
            self.ledger.timeline('stale_reply', text, referenced)
            self.ledger.enqueue('message', dict(room_id=event.room_id, body=text),
                'stale:' + event.payload.message_id, self.loop.constraints.constraints_rev)
        return True

    async def handle_ui_change(self, command: ChangeCommand) -> dict:
        """The browser reports facts; only authenticated Switch identities confirm them."""
        untrusted = command.model_copy(update={'reporter':'control-room-untrusted'})
        response = await self.loop.handle_change(untrusted,source='control_room',authenticated=False)
        return dict(change_id=response.change_id,status='pending_confirmation',reason='Confirm in Switch using an authenticated authority.')

    async def pending_report(self, event: ChatEvent, source: str) -> None:
        message = event.payload
        # Switch relays typed answers alongside their native outcome (no consumed flag).
        # Its bounded parser also recognizes bare decisions consumed in card threads.
        if (message.sender not in self.loop.identity_names or not message.body.strip()
                or message.sender_kind in ('agent', 'platform')
                or parse_text_answer(message.body) is not None
                or re.match(r'^\s*📄\s*(?:created|updated|deleted) room document\b', message.body)):
            return
        await self.loop.record_report(sender=message.sender, person=self.crew_ids.get(message.sender),
            text=message.body, key='pending-report:' + message.message_id, source=source, room_id=event.room_id)

    async def service(self) -> None:
        last_outcomes = asyncio.get_running_loop().time()
        while not self.stop.is_set():
            try:
                if self.ready and self.dispatcher:
                    if asyncio.get_running_loop().time() - last_outcomes >= 15:
                        for outcome in await self.client.get_outcomes():
                            await self.loop.handle_outcome(outcome)
                        last_outcomes = asyncio.get_running_loop().time()
                    await self.loop.tick()
                    await self.dispatcher.run_once()
                elif self.catching_up:
                    self.catchup_valid()
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
