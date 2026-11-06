"""Durable native personal cards using Switch's existing question transport.

Prior art: Switch core/switch_core/session_activity/service.py and
bridges/collaboration/session/text.py at 989225d8 (protocol, no code copied).
Switch licence: Apache-2.0 with modified Commons Clause.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from coordinator.switch_models import Question, QuestionOption, QuestionPayload
from coordinator.workflow_models import workflow_transaction


class CardTransitions:
    def _card(self, state: dict[str, Any], spec: dict[str, Any], *,
              expires_at: str | None = None, reissues: int = 0) -> dict[str, Any]:
        request_id = str(uuid4())
        expiry = expires_at or self._stamp(self._now() + timedelta(seconds=self.question_ttl))
        room = spec.get('room_id') or (self.destinations[0] if self.destinations else 'production')
        payload = QuestionPayload(request_id=request_id, turn_id=str(uuid4()), title=spec['title'],
            room_id=room, expires_at=datetime.fromisoformat(expiry),
            questions=[Question(title=spec['title'], prompt=spec['prompt'],
                options=[QuestionOption(**o) for o in spec['options']])]).model_dump(mode='json')
        q = dict(deepcopy(spec), request_id=request_id, session_id=self.session_id,
            script_rev=self.constraints.script_rev, constraints_rev=self.constraints.constraints_rev,
            expires_at=expiry, opened_at=self._stamp(), payload=payload, status='open', reissues=reissues)
        cards = self.workflow.setdefault('cards', {})
        # Closed requests remain in SQLite; bound the hot workflow history.
        if len(cards) >= 400:
            for key in list(cards):
                if len(cards) < 300:
                    break
                if cards[key]['status'] != 'open':
                    del cards[key]
        if len(cards) >= 400:
            raise ValueError('Personal card capacity reached')
        cards[request_id] = q
        self._persist_card(q)
        self._queue('open_question', dict(payload=payload), f'question:{request_id}')
        return q

    def _persist_card(self, q: dict[str, Any]) -> None:
        self.ledger.put('questions', q['request_id'], q, q['status'], q['constraints_rev'])

    def _close_card(self, q: dict[str, Any], status: str) -> None:
        q['status'] = status
        self._persist_card(q)
        self._queue('close_question', dict(request_id=q['request_id'], session_id=q['session_id']), f"close:{q['request_id']}")

    def _close_cards(self, state: dict[str, Any]) -> None:
        for q in self.workflow.get('cards', {}).values():
            if q['status'] == 'open':
                self._close_card(q, 'closed_outdated')
                self._event(state, 'decision', 'Personal card is outdated; no answer applied.', q['request_id'])

    def _duty_cards(self, state: dict[str, Any], release: dict[str, Any]) -> None:
        self._close_cards(state)
        for person in release['acks']['expected']:
            member = next(p for p in state['crew'] if p['id'] == person)
            allowed = [identity for identity, pid in self.crew_ids.items() if pid == person]
            prompt = f"Release {release['number']} · {member['name']}: " + '; '.join(release['duty_changes'][person]) + '.'
            self._card(state, dict(kind='duty', person=person, release_id=release['release_id'],
                authorized_answerers=allowed, title=f"Release {release['number']} · {member['name']}",
                prompt=prompt, options=[dict(id='confirm', label='Confirm'), dict(id='cannot', label="Can't make it")]))

    def _card_current(self, q: dict[str, Any], state: dict[str, Any]) -> bool:
        if not self._bound(q):
            return False
        if q['kind'] != 'duty':
            return True
        r = state['releases'][0] if state['releases'] else None
        return bool(r and r['release_id'] == q['release_id'] and r['status'] == 'published'
            and not self.workflow.get('unresolved'))

    def _card_outcome(self, state: dict[str, Any], q: dict[str, Any], outcome: dict[str, Any]) -> bool:
        if q['status'] not in ('open', 'expired') or q['session_id'] != outcome['session_id'] or not self._card_current(q, state):
            self._event(state, 'stale_reply', 'Ignored an outdated personal card answer.', q['request_id'])
            return False
        timely = False
        try:
            at = datetime.fromisoformat(outcome['answered_at'])
            timely = at.utcoffset() is not None and at <= datetime.fromisoformat(q['expires_at'])
        except (KeyError, ValueError, TypeError):
            pass
        if outcome.get('state') not in (None, 'answered') or (self._now() >= datetime.fromisoformat(q['expires_at']) and not timely):
            self._expire_card(state, q)
            return False
        if outcome.get('answered_by') not in q['authorized_answerers']:
            q['status'] = 'rejected_unauthorized'
            self._persist_card(q)
            retry = q['reissues'] < 1 and self._now() < datetime.fromisoformat(q['expires_at'])
            text = 'Wrong person answered personal card; ' + ('one replacement issued.' if retry else 'replacement limit reached; use the text fallback or contact the AD.')
            self._event(state, 'error', text, q['request_id'])
            self._queue('message', dict(body=text), f"wrong-person:{q['request_id']}")
            if retry:
                spec = {k: q[k] for k in ('kind', 'person', 'release_id', 'authorized_answerers', 'title', 'prompt', 'options', 'report_id', 'command', 'room_id') if k in q}
                self._card(state, spec, expires_at=q['expires_at'], reissues=1)
            return False
        choice = outcome.get('candidate_id')
        q['status'] = 'answered'
        self._persist_card(q)
        if q['kind'] == 'proposal':
            return self._proposal_outcome(state, q, outcome)
        if choice == 'confirm':
            return self._confirm(state, q['person'], q['release_id'], self.destination_platforms.get(q['payload']['room_id']))
        if choice == 'cannot':
            self._pending_duty_report(state, q, outcome)
            return True
        text = 'Personal card answer did not identify an offered choice; no confirmation recorded.'
        self._event(state, 'error', text, q['request_id'])
        self._queue('message', dict(body=text), f"invalid-card:{q['request_id']}")
        return False

    def _pending_duty_report(self, state: dict[str, Any], q: dict[str, Any], outcome: dict[str, Any]) -> None:
        key = 'duty-report:' + q['request_id']
        note = (outcome.get('note') or '').strip()[:512] or "Can't make it"
        state['changes'].insert(0, dict(id=key, at=self._stamp(), reporter=outcome['answered_by'],
            reporter_name=next(p['name'] for p in state['crew'] if p['id'] == q['person']),
            entity='person', target=q['person'], field='report', value=note,
            status='pending_confirmation', source='mattermost' if self.destination_platforms.get(q['payload']['room_id']) == 'mattermost' else 'discord'))
        text = f"{state['changes'][0]['reporter_name']} can't make {q['release_id']}: {note}. Pending AD confirmation."
        self._event(state, 'change', text, key)
        self._queue('message', dict(body=text), key)
        self._start_extraction(state, key, outcome['answered_by'], q['person'], outcome.get('note') or note)

    def _expire_card(self, state: dict[str, Any], q: dict[str, Any]) -> None:
        if q['status'] == 'expired':
            return
        self._close_card(q, 'expired')
        text = 'Personal card expired without confirmation; contact the AD or use confirm rN for the current plan.'
        self._event(state, 'error', text, q['request_id'])
        self._queue('message', dict(body=text), f"card-expired:{q['request_id']}")

    def _tick_cards(self, state: dict[str, Any], now: datetime) -> None:
        for q in self.workflow.get('cards', {}).values():
            if q['status'] == 'open' and now >= datetime.fromisoformat(q['expires_at']):
                self._expire_card(state, q)

    def _confirm(self, state: dict[str, Any], person: str, release_id: str, source: str | None = None) -> bool:
        current = state['releases'][0] if state['releases'] else None
        if not current or self.workflow.get('unresolved') or person not in {c['id'] for c in state['crew']} or current['release_id'] != release_id or current['status'] != 'published':
            self._event(state, 'stale_reply', 'Confirmation does not identify the current published release.', release_id)
            return False
        if person in current['acks']['expected'] and person not in {a['person'] for a in current['acks']['confirmed']}:
            current['acks']['confirmed'].append(dict(person=person, at=self._stamp(), **({'source': source} if source in ('mattermost', 'discord') else {})))
            self.workflow.setdefault('confirmed_releases', {})[person] = release_id
            for member in state['crew']:
                if member['id'] == person:
                    member['acked_release'] = current['number']
                    self._event(state, 'ack', f"{member['name']} confirmed {release_id}.", release_id)
        for q in self.workflow.get('cards', {}).values():
            if q['status'] == 'open' and q.get('person') == person and q.get('release_id') == release_id:
                self._close_card(q, 'answered')
        return True

    async def confirm(self, person: str, release_id: str, source: str | None = None) -> bool:
        async with self.lock:
            state = self._state()
            with workflow_transaction(self):
                result = self._confirm(state, person, release_id, source)
                self._save(state)
                return result
