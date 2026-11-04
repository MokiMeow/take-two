"""Bounded first-ad extraction and human confirmation of crew reports."""
from datetime import datetime, time
import json
import re
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import Field

from coordinator.presentation import person_label
from coordinator.ui_models import ChangeCommand, Entity, NonEmpty
from coordinator.workflow_models import Reply, apply_change, workflow_transaction

FIELDS = {'person': ('hard_stop', 'available', 'late_by'),
    'location': ('permission', 'window', 'windows', 'light_until'),
    'scene': ('status', 'overrun'), 'capability': ('status',)}


class Extraction(Reply):
    entity: Entity
    target: NonEmpty
    field: NonEmpty
    value: NonEmpty
    confidence: float = Field(strict=True, ge=0, le=1, allow_inf_nan=False)


def authority_ids(command: ChangeCommand, constraints: Any, authorities: dict[str, list[str]]) -> list[str]:
    role = {'person': 'availability_confirmation', 'scene': 'overrun_confirmation',
        'capability': 'capability_verification', 'location': 'location_permission'}[command.entity]
    allowed = authorities.get(role, [])
    if command.entity == 'location':
        location = next((x for x in constraints.locations if x.id == command.target), None)
        named = location.permission_authority if location else None
        allowed = authorities.get(f'location_permission:{command.target}', allowed if named == 'producer'
            else authorities.get(named or '', [named] if named else []))
    return list(allowed)


def grounded_time(command: ChangeCommand, text: str, constraints: Any, date: str) -> None:
    """A model cannot resolve an ungrounded clock time by claiming confidence."""
    if command.field not in ('hard_stop', 'light_until', 'available', 'window', 'windows'):
        return
    if re.search(r'\b(maybe|might|sometime|around|or|tomorrow|yesterday|today|next)\b', text, re.I):
        raise ValueError('Ambiguous time')
    # The bounded extractor handles the supplied production day/local clock.
    # Other calendar/zone syntax needs clarification rather than partial parsing.
    calendar = r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|\d{4}[-/]\d{1,2}|\d{1,2}/\d{1,2}'
    zone = r'\b(?:UTC|GMT|PST|PDT|EST|EDT|CST|CDT|MST|MDT|BST|CET|CEST|JST|AEST)\b|[+-]\d{2}:?\d{2}|(?:America|Europe|Asia|Africa|Australia)/'
    if re.search(calendar, text, re.I) or re.search(zone, text, re.I) or re.search(r'\d{1,2}:\d{2}:', text):
        raise ValueError('Unsupported source date, zone or seconds')
    if command.field in ('window', 'windows'):
        intervals = re.findall(r'\b(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})\b', text)
        if len(intervals) != 1:
            raise ValueError('One explicit 24-hour interval required')
        start, end = intervals[0]
        if command.field == 'window':
            if command.value != f'{start}-{end}':
                raise ValueError('Window disagrees with source')
        else:
            rows = json.loads(command.value)
            expected = [dict(start=f'{date}T{start}:00+05:30', end=f'{date}T{end}:00+05:30')]
            if rows != expected:
                raise ValueError('Window date/endpoints disagree with source')
        return
    clocks = list(re.finditer(r'\b(?:at|by|until|from)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', text, re.I))
    if len(clocks) != 1:
        raise ValueError('One explicit time required')
    match = clocks[0]
    if re.search(r'\d', text[:match.start()] + text[match.end():]):
        raise ValueError('Other numeric source terms need clarification')
    hour, minute, meridiem = match.groups(default='')
    h, m = int(hour), int(minute or '0')
    if h > 23 or m > 59 or (meridiem and not 1 <= h <= 12):
        raise ValueError('Invalid source time')
    hours = [h % 12 + (12 if meridiem.lower() == 'pm' else 0)] if meridiem else ([h, h + 12] if h < 12 else [h])
    target = next((x for x in (constraints.people if command.entity == 'person' else constraints.locations) if x.id == command.target), None)
    windows = getattr(target, 'available' if command.entity == 'person' else 'windows', None)
    zone = ZoneInfo(constraints.timezone)
    possible = [datetime.combine(datetime.fromisoformat(date).date(), time(hh, m), zone) for hh in hours]
    if not meridiem and h < 12:
        possible = [v for v in possible if isinstance(windows, list) and any(w.start <= v <= w.end for w in windows)]
    if len(possible) != 1:
        raise ValueError('Ambiguous AM/PM')
    expected = possible[0]
    if re.fullmatch(r'\d{2}:\d{2}', command.value):
        if command.value != expected.strftime('%H:%M'):
            raise ValueError('Proposed time disagrees with source')
    else:
        actual = datetime.fromisoformat(command.value)
        if actual.utcoffset() is None or actual != expected:
            raise ValueError('Proposed date/time disagrees with source')


class ReportTransitions:
    async def record_report(self, *, sender: str, person: str | None, text: str,
                            key: str, source: str, room_id: str) -> None:
        async with self.lock:
            if self.ledger.get_meta(key):
                return
            state = self._state()
            with workflow_transaction(self):
                self._add_report(state, sender=sender, person=person, text=text, key=key, source=source, room_id=room_id)
                self.ledger.set_meta(key, True)
                self._save(state)

    def _add_report(self, state: dict[str, Any], *, sender: str, person: str | None,
                    text: str, key: str, source: str, room_id: str) -> None:
        original = text
        text = text.strip()[:512]
        state['changes'].insert(0, dict(id=key, at=self._stamp(), reporter=sender,
            reporter_name=self.identity_names.get(sender, 'Crew member'), entity='scene', target='unconfirmed',
            field='report', value=text, status='pending_confirmation', source=source))
        label = person_label(sender, self.identity_names, self.identity_roles)
        self._event(state, 'change', f'{label} reported a change; structured confirmation is required.', key)
        self._queue('message', dict(body='Report recorded as pending. An authorized person must confirm the proposed change or use /change <entity> <target> <field> <value>.'), key)
        self._start_extraction(state, key, sender, person, original)

    def _start_extraction(self, state: dict[str, Any], key: str, sender: str, person: str | None, text: str) -> None:
        if len(text) > 512:
            self._event(state, 'error', 'Long report remains pending; clarify it without truncation before extraction.', key)
            self._queue('message', dict(body='Long report remains pending. The AD must clarify the full source before recording a change.'), 'long-report:' + key)
            return
        if not person or not re.search(r'\b(leave|late|dead|broken|unavailable|can.t make|lost|overrun|permission|running)\b', text, re.I):
            return
        if len(self.workflow['jobs']) >= 18 or sum(j['status'] in ('queued', 'running') for j in self.workflow['jobs']) >= 6:
            self._event(state, 'error', 'Extraction capacity reached; report remains pending.', key)
            self._queue('message', dict(body='Extraction capacity reached; the AD must normalize the pending report.'), 'capacity:' + key)
            return
        self._job(state, 'first-ad', dict(task='extract_change', report_id=key, message=text,
            sender_id=sender, person_id=person, production_date=self.production_date, timezone=self.constraints.timezone,
            allowed_fields=FIELDS, instruction='Return job identity/revisions/addressed_to plus entity,target,field,value,confidence only. Use reviewed IDs. Report uncertainty with confidence below 0.9. Never decide authority. Clock times must match the production date and known availability.'))

    def _extraction_reply(self, state: dict[str, Any], job: dict[str, Any], data: dict[str, Any]) -> bool:
        reply = Extraction.model_validate(data)  # malformed JSON/schema uses the common one-retry path
        job['status'] = 'done'
        self._sync_jobs(state)
        try:
            command = ChangeCommand(**reply.model_dump(include={'entity', 'target', 'field', 'value'}), reporter=job['context']['sender_id'])
            if reply.confidence < 0.9 or command.field not in FIELDS[command.entity]:
                raise ValueError('Uncertain or unsupported extraction')
            if command.entity == 'person' and command.target != job['context']['person_id']:
                if not re.search(r'\b' + re.escape(command.target) + r'\b', job['context']['message'], re.I):
                    raise ValueError('Ungrounded person')
            grounded_time(command, job['context']['message'], self.constraints, self.production_date)
            allowed = authority_ids(command, self.constraints, self.authorities)
            probe = command.model_copy(update={'reporter': allowed[0] if allowed else ''})
            status, _, _ = apply_change(probe, self.constraints, self.authorities, self._now(), self.workflow.get('plans', {}))
            if not allowed or status != 'recorded':
                raise ValueError('Proposal does not identify a valid known change')
        except (ValueError, TypeError, StopIteration, OverflowError):
            text = 'Report remains pending: extraction is uncertain or invalid; the AD must clarify it.'
            self._event(state, 'error', text, job['context']['report_id'])
            self._queue('message', dict(body=text), 'extraction-pending:' + job['job_id'])
            self._save(state)
            return False
        name = self.identity_names.get(command.reporter, 'Crew member')
        prompt = f"{name} says: '{job['context']['message']}'. Record `{command.entity} {command.target} {command.field} {command.value}`?"
        room = getattr(self.switch, 'production_room_id', None) or 'production'
        self._card(state, dict(kind='proposal', title=f'{name} · proposed change', prompt=prompt,
            options=[dict(id='record', label='Record'), dict(id='ignore', label='Ignore')],
            authorized_answerers=allowed, report_id=job['context']['report_id'], command=command.model_dump(), room_id=room))
        self._event(state, 'decision', 'A proposed change awaits the responsible authority.', job['context']['report_id'])
        self._save(state)
        return True

    def _proposal_outcome(self, state: dict[str, Any], q: dict[str, Any], outcome: dict[str, Any]) -> bool:
        report = next((c for c in state['changes'] if c['id'] == q['report_id']), None)
        if report is None or report.get('resolution'):
            self._event(state, 'stale_reply', 'Proposal report is no longer pending.', q['request_id'])
            return False
        if outcome.get('candidate_id') == 'ignore':
            report['resolution'] = 'dismissed'
            self._event(state, 'decision', 'Authority dismissed the proposed change; facts unchanged.', q['report_id'])
            return True
        if outcome.get('candidate_id') != 'record':
            self._event(state, 'error', 'Invalid proposed change answer; report remains pending.', q['request_id'])
            self._queue('message', dict(body='Invalid proposed change answer; no facts recorded.'), 'invalid-proposal:' + q['request_id'])
            return False
        command = ChangeCommand.model_validate(dict(q['command'], reporter=outcome['answered_by']))
        result = self._record_change(command, source=report['source'], source_message_id='proposal:' + q['report_id'], state=state)
        if result.status == 'recorded':
            report['resolution'] = 'recorded'
            return True
        return False
