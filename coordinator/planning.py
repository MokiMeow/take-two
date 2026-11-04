"""Authenticated initial planning and conservative, durable scene scope."""
from copy import deepcopy
from typing import Any

from coordinator.constraints import Manifest
from coordinator.checker import check_manifest
from coordinator.workflow_models import workflow_transaction
from coordinator.ripple import ripple_holds


class PlanningTransitions:
    async def request_plan(self, day: str, sender: str, message_id: str) -> bool:
        async with self.lock:
            state = self._state()
            if self.ledger.get_meta('plan_source:'+message_id):
                return False
            with workflow_transaction(self):
                planning_started = any(j['context'].get('task') != 'extract_change' for j in self.workflow['jobs'])
                if day!='day-1' or sender not in self.authorities.get('creative',[]) or state['releases'] or planning_started:
                    self._event(state,'error','Initial /plan requires the authenticated director, day-1 and an unplanned production.',message_id)
                    self._queue('message',dict(body='Initial plan was not started. Use /plan day-1 as the named director before any release.'),'plan-rejected:'+message_id)
                    self._save(state)
                    return False
                self.ledger.set_meta('plan_source:'+message_id,True)
                self.workflow['unresolved']=[s['id'] for s in state['scenes']]
                self._job(state,'script-supervisor',dict(scene_ids=list(self.workflow['unresolved']),initial_plan=True,
                    schedule_contract='Initial AD candidate uses manifests: a complete array of every scene, approved once.'))
                self._save(state)
                return True

    def _affected(self, command: Any, state: dict[str, Any]) -> list[str]:
        unresolved = set(self.workflow.get('unresolved',[]))
        unresolved.update(ripple_holds(self.workflow.get('plans',{}),self.constraints))
        for scene in state['scenes']:
            sid = scene['id']
            if command.entity=='scene' and command.target==sid:
                unresolved.add(sid)
                continue
            m = self.workflow.get('plans',{}).get(sid)
            if not m:
                continue
            current = dict(m,script_rev=self.constraints.script_rev,constraints_rev=self.constraints.constraints_rev)
            if check_manifest(Manifest.model_validate(current),self.constraints).result!='pass':
                unresolved.add(sid)
        self.workflow['unresolved']=sorted(unresolved)
        return sorted(unresolved)

    def _hold(self, state: dict[str, Any], scene_ids: list[str], reason: str, ref: str) -> None:
        for scene in state['scenes']:
            if scene['id'] in scene_ids:
                scene.update(validity='held',hold_reason=reason)
        self.workflow['unresolved']=sorted(set(self.workflow.get('unresolved',[]))|set(scene_ids))
        if not scene_ids:
            return
        affected = [s for s in state['scenes'] if s['id'] in scene_ids]
        labels = ', '.join(f"Scene {s['number']} ({s['title']})" for s in affected)
        reason_text = reason[0].upper()+reason[1:]
        body = f'HOLD · {labels}. {reason_text}.'
        if 'rooftop' in reason.lower() and ('refused' in reason.lower() or 'confirmation' in reason.lower()):
            body += ' Do not go to the rooftop.'
        unchanged = [str(s['number']) for s in state['scenes'] if s['id'] not in scene_ids and s['validity']=='valid']
        if unchanged:
            body += '\nScenes '+' and '.join(unchanged)+' are unchanged.'
        body += ' An update is coming.'
        self._event(state,'hold',body,ref)
        self._queue('hold',dict(scene_ids=scene_ids,body=body),f'hold:{ref}')
