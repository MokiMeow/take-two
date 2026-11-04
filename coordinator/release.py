"""Release transitions share Loop's serialized SQLite transaction."""
from copy import deepcopy
from datetime import datetime
import json
from typing import Any

from coordinator.constraints import Manifest
from coordinator.render_props import callsheet_props, call_times, operational, hhmm, preview_props
from coordinator.schedules import check_schedule, digest, plans, retained_plans, snapshot
from coordinator.workflow_models import workflow_transaction


class ReleaseTransitions:
    def _prepare_candidates(self, proposals: Any, state: dict[str, Any]) -> list[dict[str, Any]]:
        from coordinator.ui_models import Candidate
        from coordinator.workflow_models import visible_candidate
        result = []
        for proposal in proposals:
            rows = [m.model_dump(mode='json',exclude={'manifest_hash'}) for m in proposal.plans()]
            item = dict(candidate_id=proposal.candidate_id,label=proposal.label,story_cost=proposal.story_cost,
                manifest=rows[-1],preview_status='none',preview_url=None)
            if len(rows)>1:
                item['manifests']=rows
            item.update(manifest_hash=self._candidate_digest(item),check=self._candidate_check(item,state).model_dump())
            Candidate.model_validate(visible_candidate(item))
            scene = next(s for s in self.metadata['scenes'] if s['id']==item['manifest']['scene_id'])
            preview_props(item,'A',scene,self.metadata['crew'])
            result.append(item)
        return result

    def _candidate_check(self, candidate: dict[str, Any], state: dict[str, Any]) -> Any:
        return check_schedule([Manifest.model_validate(m) for m in plans(candidate)],self.constraints,
            retained_plans(self.workflow,state))

    def _candidate_digest(self, candidate: dict[str, Any]) -> str:
        return digest(dict(scenes=candidate['manifests'])) if candidate.get('manifests') else digest(candidate['manifest'])

    def _release(self, state: dict[str, Any], candidate: dict[str, Any], question: dict[str, Any]) -> None:
        number = max((r['number'] for r in state['releases']),default=0)+1
        if number>999:
            raise ValueError('Release limit reached; create a new production.')
        release_id = f'r{number}'
        manifest = snapshot(self.workflow,state,plans(candidate),self.constraints)
        previous = next((v['envelope']['manifest'] for r in state['releases'] if r['status']=='published'
            and (v:=self.workflow['releases'].get(r['release_id'])) and 'envelope' in v),None)
        metadata = deepcopy(self.metadata)
        if len(plans(candidate))==1:
            m = candidate['manifest']
            scene = next(s for s in metadata['scenes'] if s['id']==m['scene_id'])
            coverage = ', reduced coverage' if 'reduced' in candidate['label'].lower() else ''
            summary = f"Scene {scene['number']} moves to the {m['location']}, {hhmm(m['start'])}–{hhmm(m['end'])}{coverage}."
        elif number == 1:
            summary = 'Initial complete three-scene schedule approved.'
        else:
            summary = candidate['label']+'.'
        stamp = self._stamp()
        identity = dict(number=number,release_id=release_id,manifest_hash=digest(manifest),summary=summary,
            changes=[f"Director chose: {candidate['label']}"],created_at=stamp)
        envelope = dict(manifest=manifest,previous_manifest=previous,metadata=metadata,release=identity,
            approved_candidate_hash=candidate['manifest_hash'],request_id=question['request_id'])
        callsheet_props(envelope)  # Validate the complete immutable artifact input before commit.
        times, old_times = call_times(manifest), call_times(previous or dict(scenes=[]))
        expected = [p['id'] for p in metadata['crew'] if times.get(p['id']) != old_times.get(p['id'])]
        for member in state['crew']:
            member.update(affected=member['id'] in expected,call_time=times.get(member['id']))
            if member['affected']:
                member['acked_release']=None
        release = dict(release_id=release_id,number=number,status='approved',created_at=stamp,
            manifest_hash=identity['manifest_hash'],summary=summary,preview_url=candidate.get('preview_url'),
            publications=[dict(room=r,room_name=self.room_names.get(r,r if r.startswith('#') else 'Crew room'),
                platform=self.destination_platforms.get(r,'discord'),status='pending') for r in self.destinations],
            acks=dict(expected=expected,confirmed=[],policy='affected_only'))
        state['releases'].insert(0,release)
        self.workflow['releases'][release_id] = dict(script_rev=self.constraints.script_rev,
            constraints_rev=self.constraints.constraints_rev,candidate=deepcopy(candidate),
            request_id=question['request_id'],envelope=deepcopy(envelope))
        self._queue('release',dict(release_id=release_id,manifest=manifest,manifest_hash=identity['manifest_hash'],
            envelope=envelope,summary=summary,preview_url=candidate.get('preview_url'),destinations=list(self.destinations)),f'release:{release_id}')
        self._event(state,'release',f'Release {number} approved; publication pending.',release_id)

    def effect_current(self, effect: dict[str, Any]) -> bool:
        kind = effect.get('kind')
        if kind in ('hold','hold_message','close_question','mark_delivered','message'):
            return True
        if effect.get('revision') != self.constraints.constraints_rev:
            return False
        p = effect.get('payload',{})
        if isinstance(p,str):
            p = json.loads(p)
        if kind=='document':
            return True
        if kind=='role_message':
            return any(j['job_id']==p.get('job_id') and self._bound(j) and j['status'] in ('queued','running') for j in self.workflow['jobs'])
        if kind=='open_question':
            q = self.workflow['question']
            return bool(q and q['status']=='open' and q['request_id']==p['payload']['request_id'] and self._now()<datetime.fromisoformat(q['expires_at']))
        if kind=='preview':
            return any(c['candidate_id']==p.get('candidate_id') and c['manifest_hash']==p.get('manifest_hash') and c['preview_status']=='rendering' for c in self.workflow['candidates'])
        if kind in ('release','publication_media','publication_text'):
            r = self.workflow['releases'].get(p.get('release_id'))
            return bool(r and self._bound(r) and not (set(self.workflow['holds']) & {m['scene_id'] for m in plans(r['candidate'])})
                and self._candidate_check(r['candidate'],self._state()).result=='pass')
        return False

    async def publication_result(self, release_id: str, room: str, status: str) -> None:
        async with self.lock:
            state = self._state()
            with workflow_transaction(self):
                r = next((r for r in state['releases'] if r['release_id']==release_id),None)
                if not r or r['status']=='superseded':
                    return
                for destination in r['publications']:
                    if destination['room']==room:
                        destination['status']=status
                if r['publications'] and all(p['status']=='sent' for p in r['publications']) and r['status']!='published':
                    r['status']='published'
                    for other in state['releases']:
                        if other is not r and other['status']=='published':
                            other['status']='superseded'
                    internal = self.workflow['releases'].get(release_id)
                    if internal and self._bound(internal):
                        for m in plans(internal['candidate']):
                            self.workflow.setdefault('plans',{})[m['scene_id']]=deepcopy(m)
                            self.workflow['unresolved']=[s for s in self.workflow.get('unresolved',[]) if s!=m['scene_id']]
                            for s in state['scenes']:
                                if s['id']==m['scene_id']:
                                    s.update(validity='valid',hold_reason=None,plan={k:m[k] for k in ('location','start','end','setup_min','wrap_min','people')})
                    else:
                        self._hold(state,[s['id'] for s in state['scenes'] if s['validity']!='valid'],'A newer change arrived during publication',release_id)
                    self._event(state,'release',f'{release_id} published: accepted by Switch for relay; external delivery is unverified.',release_id)
                self._save(state)
