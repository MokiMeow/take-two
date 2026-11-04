"""The shared authority-checked structured change transaction body."""
from typing import Any
from uuid import uuid4
from coordinator.ui_models import ChangeCommand, ChangeResponse
from coordinator.workflow_models import apply_change
from coordinator.presentation import person_name, person_label, resolved_change_at


class ChangeTransitions:
    def _record_change(self, command: ChangeCommand, *, source: str = 'control_room',
                       source_message_id: str | None = None, authenticated: bool = True,
                       state: dict[str, Any] | None = None) -> ChangeResponse:
        key = f'{source}:{source_message_id}' if source_message_id else None
        prior = self.ledger.get_meta(f'change_source:{key}') if key else None
        if prior:
            return ChangeResponse.model_validate(prior)
        state = self._state() if state is None else state
        status,reason,facts = apply_change(command,self.constraints,self.authorities if authenticated else {},self._now(),
            plans=self.workflow.get('plans',{}))
        change_id = str(uuid4())
        response = ChangeResponse(change_id=change_id,status=status,reason=reason)
        if facts is not None:
            self.constraints = facts
            if command.field != 'verified_facts':
                self.workflow['decision_round']=1
            self._invalidate(state)
            state['revisions'] = dict(script=facts.script_rev,constraints=facts.constraints_rev)
        if command.entity == 'scene' and command.field == 'safety' and status == 'recorded':
            if command.value == 'hold':
                self.workflow['holds'][command.target] = dict(reporter=command.reporter, at=self._stamp())
            else:
                self.workflow['holds'].pop(command.target, None)
        stamp = self._stamp()
        at = resolved_change_at(command, facts, stamp) if facts is not None else stamp
        state['changes'].insert(0,dict(**command.model_dump(),id=change_id,at=at,recorded_at=stamp,
            reporter_name=person_name(command.reporter,self.identity_names),status=status,source=source,
            constraints_rev=self.constraints.constraints_rev if status=='recorded' else None))
        label = person_label(command.reporter,self.identity_names,self.identity_roles)
        self._event(state,'change',f'{label}: {command.target} {command.field} {command.value} ({status}).',change_id)
        affected = self._affected(command,state) if facts is not None or status=='recorded' else list(self.workflow.get('unresolved',[]))
        if status == 'recorded':
            self._hold(state,affected,f'{command.target} {command.field} {command.value}',change_id)
            state['jobs'] = []
            if affected:
                eligible = [sid for sid in affected if sid not in self.workflow['holds'] and
                    next(s for s in self.constraints.scenes if s.id==sid).status != 'held']
                if eligible:
                    self._job(state,'script-supervisor',dict(change=command.model_dump(),scene_ids=eligible,
                        current_schedule=list(self.workflow.get('plans',{}).values())))
                else:
                    self._queue('message',dict(body='Safety hold recorded. Named clearance is required before planning a replacement.'),f'safety-wait:{change_id}')
        elif status == 'pending_confirmation' and command.value in ('refused','unknown'):
            self._hold(state,affected,'Report requires confirmation',change_id)
        if status != 'recorded':
            self._queue('message',dict(body=f'Change {status}: {reason or "authority confirmation required"}.'),f'change-result:{change_id}')
        if key:
            self.ledger.set_meta(f'change_source:{key}',response.model_dump())
        self._save(state)
        return response

