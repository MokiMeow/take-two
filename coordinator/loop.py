"""Serialized production decisions; all external effects use the durable outbox.

The asyncio lock covers local transitions only. No network/render work is awaited
inside it, so a change can invalidate an effect while an external send runs.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
import json
from uuid import uuid4
from typing import Any, Callable
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from coordinator.checker import manifest_hash
from coordinator.constraints import Constraints, Manifest
from coordinator.ui_models import ChangeCommand, ChangeResponse, State
from coordinator.workflow_models import ADReply, SupervisorReply, visible_candidate, release_snapshot, apply_change, check_candidate, normalize_outcome, note_constraints, workflow_transaction
from coordinator.switch_models import Question, QuestionOption, QuestionPayload

IST = ZoneInfo('Asia/Kolkata')

class Loop:
    def __init__(self, ledger: Any, switch: Any, constraints: Constraints, renderer: Any = None, *,
                 authorities: dict[str, list[str]] | None = None, worker_ids: dict[str, str] | None = None,
                 worker_names: dict[str,str] | None = None,
                 coordinator_id: str | None = None, clock: Callable[[], datetime] | None = None,
                 destinations: list[str] | None = None, job_timeout: int = 120, retry_backoff: int = 5,
                 question_ttl: int = 7200) -> None:
        self.ledger, self.switch, self.renderer = ledger, switch, renderer
        self.authorities = authorities or {}
        self.worker_ids = worker_ids or {}
        self.worker_names = worker_names or {}
        self.coordinator_id = coordinator_id
        self.clock = clock or (lambda: datetime.now(IST))
        self.destinations = ['#crew', '#day-1'] if destinations is None else destinations
        self.job_timeout, self.retry_backoff, self.question_ttl = job_timeout, retry_backoff, question_ttl
        self.lock = asyncio.Lock()
        saved = ledger.get_meta('workflow')
        self.workflow = saved or dict(constraints=constraints.model_dump(mode='json'), jobs=[], question=None,
            closed_questions=[], outcomes=[], candidates=[], holds={}, source_responses={}, releases={})
        self.constraints = Constraints.model_validate(self.workflow['constraints'])
        identity = getattr(switch, 'identity', None)
        self.session_id = ledger.get_meta('question_session_id') or (identity.session_id if identity else str(uuid4()))
        with ledger.transaction():
            ledger.set_meta('question_session_id', self.session_id)
            self._save()

    def _now(self) -> datetime:
        return self.clock().astimezone(IST)

    def _stamp(self, value: datetime | None = None) -> str:
        return (value or self._now()).astimezone(IST).isoformat()

    def _state(self) -> dict[str, Any]:
        return deepcopy(self.ledger.snapshot_state())

    def _save(self, state: dict[str, Any] | None = None) -> None:
        self.workflow['constraints'] = self.constraints.model_dump(mode='json')
        self.ledger.set_meta('workflow', self.workflow)
        if state is not None:
            state['production']['now'] = self._stamp()
            state['timeline'] = state['timeline'][:200]
            state['changes'], state['releases'] = state['changes'][:200], state['releases'][:200]
            self.ledger.save_state(State.model_validate(state).model_dump(mode='json', exclude_none=True))
        for job in self.workflow['jobs']:
            self.ledger.put('jobs',job['job_id'],job,job['status'],job['constraints_rev'])
        question = self.workflow['question']
        if question:
            self.ledger.put('questions',question['request_id'],question,question['status'],question['constraints_rev'])

    def _event(self, state: dict[str, Any], kind: str, text: str, ref: str | None = None) -> None:
        text = text[:512]
        state['timeline'].insert(0, dict(at=self._stamp(),kind=kind,text=text,ref=ref))
        self.ledger.timeline(kind, text, ref)

    def _queue(self, kind: str, payload: dict[str, Any], key: str) -> str:
        return self.ledger.enqueue(kind,payload,key,self.constraints.constraints_rev)

    def _bound(self, value: dict[str, Any]) -> bool:
        return value.get('script_rev') == self.constraints.script_rev and value.get('constraints_rev') == self.constraints.constraints_rev

    def _invalidate(self, state: dict[str, Any]) -> None:
        for job in self.workflow['jobs']:
            if job['status'] in ('queued','running'):
                job['status'] = 'cancelled'
                self.ledger.put('jobs',job['job_id'],job,'cancelled',job['constraints_rev'])
        self.workflow['jobs'] = []
        for job in state['jobs']:
            if job['status'] in ('queued','running'):
                job['status'] = 'cancelled'
        question = self.workflow['question']
        if question:
            question['status']='closed_outdated'
            self.ledger.put('questions',question['request_id'],question,'closed_outdated',question['constraints_rev'])
            self.workflow['closed_questions'] = [*self.workflow['closed_questions'],question['request_id']][-200:]
            self._queue('close_question',dict(request_id=question['request_id']),f"close:{question['request_id']}")
            if state.get('decision'):
                state['decision']['status'] = 'closed_outdated'
            self.workflow['question'] = None
        self.workflow['candidates'] = []

    def _affected(self, command: ChangeCommand, state: dict[str, Any]) -> list[str]:
        result = []
        for scene in state['scenes']:
            plan = scene.get('plan') or {}
            if (command.entity == 'scene' and scene['id'] == command.target
                or command.entity == 'location' and plan.get('location') == command.target
                or command.entity == 'person' and command.target in plan.get('people', [])
                or command.entity == 'capability'):
                result.append(scene['id'])
        return result

    def _hold(self, state: dict[str, Any], scene_ids: list[str], reason: str, ref: str) -> None:
        for scene in state['scenes']:
            if scene['id'] in scene_ids:
                scene.update(validity='held',hold_reason=reason)
        if scene_ids:
            self._event(state,'hold',f"{', '.join(scene_ids)} on hold: {reason}",ref)
            self._queue('hold',dict(scene_ids=scene_ids,body=f"{', '.join(scene_ids)} ON HOLD. {reason}. Update coming."),f'hold:{ref}')

    async def handle_change(self, command: ChangeCommand, *, source: str = 'control_room', source_message_id: str | None = None) -> ChangeResponse:
        command = ChangeCommand.model_validate(command)
        async with self.lock:
            key = f'{source}:{source_message_id}' if source_message_id else None
            prior = self.ledger.get_meta(f'change_source:{key}') if key else None
            if prior:
                return ChangeResponse.model_validate(prior)
            state = self._state()
            status,reason,facts = apply_change(command,self.constraints,self.authorities,self._now())
            change_id = str(uuid4())
            response = ChangeResponse(change_id=change_id,status=status,reason=reason)
            with workflow_transaction(self):
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
                state['changes'].insert(0,dict(**command.model_dump(),id=change_id,at=self._stamp(),status=status,source=source,
                    constraints_rev=self.constraints.constraints_rev if status=='recorded' else None))
                self._event(state,'change',f'{command.reporter}: {command.target} {command.field} {command.value} ({status}).',change_id)
                affected = self._affected(command,state)
                if status == 'recorded':
                    self._hold(state,affected,f'{command.target} {command.field} changed',change_id)
                    state['jobs'] = []
                    self._job(state,'script-supervisor',dict(change=command.model_dump(),scene_ids=affected))
                elif status == 'pending_confirmation' and command.value in ('refused','unknown'):
                    self._hold(state,affected,'Report requires confirmation',change_id)
                if key:
                    self.ledger.set_meta(f'change_source:{key}',response.model_dump())
                self._save(state)
            return response

    def _job(self, state: dict[str, Any], role: str, context: dict[str, Any]) -> None:
        job_id = str(uuid4())
        job = dict(job_id=job_id,role=role,status='queued',attempt=0,script_rev=self.constraints.script_rev,
                   constraints_rev=self.constraints.constraints_rev,started_at=self._stamp(),
                   deadline=self._stamp(self._now()+timedelta(seconds=self.job_timeout)),context=context)
        self.workflow['jobs'].append(job)
        state['jobs'].append({key:job[key] for key in ('job_id','role','status','started_at','deadline')})
        self._queue_job(job)
        self._event(state,'job',f'Requested {role}.',job_id)

    def _queue_job(self, job: dict[str, Any]) -> None:
        document = self._queue('document',dict(name=f'constraints-r{job["constraints_rev"]}',
            content=json.dumps(self.constraints.model_dump(mode='json'),ensure_ascii=False,sort_keys=True)),f'constraints-document:{job["constraints_rev"]}')
        body = json.dumps(dict(job_id=job['job_id'],script_rev=job['script_rev'],constraints_rev=job['constraints_rev'],
            addressed_to=self.coordinator_id, constraints=self.constraints.model_dump(mode='json'),**job['context']),sort_keys=True)
        self._queue('role_message',dict(role=job['role'],body=body,expected_holder=self.worker_names.get(job['role']),job_id=job['job_id'],depends_on=document),
                    f"job:{job['job_id']}:{job['attempt']}")

    def _retry(self, state: dict[str, Any], job: dict[str, Any], reason: str, now: datetime | None = None) -> None:
        if job['attempt'] >= 1:
            job['status'] = 'failed'
            self._event(state,'error',f"{job['role']} failed after one retry: {reason}",job['job_id'])
            self._queue('message',dict(body=f"{job['role']} failed after one retry. Plan remains on hold."),f"job-failed:{job['job_id']}")
        else:
            job['attempt'] += 1
            job['status'] = 'queued'
            job['retry_at'] = self._stamp((now or self._now())+timedelta(seconds=self.retry_backoff))
            self._event(state,'job',f"{job['role']} reply rejected; one retry scheduled: {reason}",job['job_id'])
        self._sync_jobs(state)

    def _sync_jobs(self,state: dict[str, Any]) -> None:
        for visible in state['jobs']:
            job = next(j for j in self.workflow['jobs'] if j['job_id']==visible['job_id'])
            for key in ('status','deadline'):
                visible[key] = job[key]

    async def handle_worker_reply(self, payload: dict[str, Any] | str, *, sender_id: str | None = None) -> bool:
        async with self.lock:
            state = self._state()
            try:
                if isinstance(payload,str) and len(payload)>65536:
                    raise ValueError('Worker reply too large')
                data = json.loads(payload) if isinstance(payload,str) else payload
                job = next((j for j in self.workflow['jobs'] if j['job_id']==data.get('job_id')),None)
            except (ValueError,TypeError,AttributeError,RecursionError):
                data, job = {}, next((j for j in reversed(self.workflow['jobs']) if j['status'] in ('queued','running')),None)
            if not job and isinstance(data,dict) and not data.get('job_id'):
                job = next((j for j in reversed(self.workflow['jobs']) if j['status'] in ('queued','running')),None)
            with workflow_transaction(self):
                if not job or not self._bound(job) or job['status'] not in ('queued','running'):
                    self._event(state,'stale_reply','Discarded an obsolete worker reply.',data.get('job_id'))
                    self._save(state)
                    return False
                expected = self.worker_ids.get(job['role'])
                if (expected and sender_id != expected) or (self.coordinator_id and not expected):
                    self._event(state,'error','Discarded reply from an unexpected worker identity.',job['job_id'])
                    self._save(state)
                    return False
                if ('script_rev' in data and 'constraints_rev' in data) and not self._bound(data):
                    self._event(state,'stale_reply','Discarded worker reply with old revisions.',job['job_id'])
                    self._save(state)
                    return False
                try:
                    if self.coordinator_id and data.get('addressed_to') != self.coordinator_id:
                        raise ValueError('Reply must address coordinator')
                    reply = (SupervisorReply if job['role']=='script-supervisor' else ADReply).model_validate(data)
                    if isinstance(reply,ADReply) and len({c.candidate_id for c in reply.candidates}) != len(reply.candidates):
                        raise ValueError('Duplicate candidate ids')
                    if isinstance(reply,ADReply) and any(c.manifest.scene_id not in job['context'].get('scene_ids',[]) for c in reply.candidates):
                        raise ValueError('Candidate must resolve an affected scene')
                except (ValidationError,ValueError) as exc:
                    self._retry(state,job,'Invalid structured reply' if isinstance(exc,ValidationError) else str(exc)[:200])
                    self._save(state)
                    return False
                job['status'] = 'done'
                self._sync_jobs(state)
                if isinstance(reply,SupervisorReply):
                    self.workflow['supervisor'] = reply.model_dump()
                    self._job(state,'first-ad',dict(supervisor=reply.model_dump(),change=job['context'].get('change'),scene_ids=job['context'].get('scene_ids',[])))
                else:
                    candidates = []
                    for candidate in reply.candidates:
                        manifest = candidate.manifest
                        result = check_candidate(manifest,self.constraints,state)
                        item = dict(candidate_id=candidate.candidate_id,label=candidate.label,story_cost=candidate.story_cost,
                            manifest=manifest.model_dump(mode='json',exclude={'manifest_hash'}),manifest_hash=manifest_hash(manifest),check=result.model_dump(),
                            preview_status='none',preview_url=None)
                        candidates.append(item)
                        self._event(state,'check',f'{candidate.label}: {result.result}.',candidate.candidate_id)
                    self.workflow['candidates'] = candidates
                    if any(c['check']['result']=='pass' for c in candidates):
                        if self.renderer:
                            for c in candidates:
                                if c['check']['result']=='pass':
                                    c['preview_status']='rendering'
                                    self._queue('preview', {k:c[k] for k in ('candidate_id','manifest','manifest_hash')},f"preview:{self.constraints.constraints_rev}:{c['manifest_hash']}")
                        else:
                            self._question(state,candidates)
                    else:
                        self._event(state,'error','No feasible option. Resolve failed or unknown facts before release.')
                self._save(state)
                return True

    def _question(self, state: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
        request_id, turn_id = str(uuid4()),str(uuid4())
        expiry = self._stamp(self._now()+timedelta(seconds=self.question_ttl))
        allowed = list(self.authorities.get('creative',[]))
        options = [dict(id=c['candidate_id'],label=c['label'],description=c['story_cost']) for c in candidates if c['check']['result']=='pass']
        options.append(dict(id='neither',label='Neither',description='Add a note; no release.'))
        title, prompt = 'Choose the current shoot plan', 'Choose a checked option or Neither with your note.'
        if self.switch is not None:
            payload = self.switch.question_payload(title, prompt, [QuestionOption(**o) for o in options],
                datetime.fromisoformat(expiry), request_id=request_id, turn_id=turn_id).model_dump(mode='json')
        else:
            payload = QuestionPayload(request_id=request_id,turn_id=turn_id,title=title,room_id='production',
                expires_at=datetime.fromisoformat(expiry),questions=[Question(title=title,prompt=prompt,
                options=[QuestionOption(**o) for o in options])]).model_dump(mode='json')
        question = dict(request_id=request_id,turn_id=turn_id,session_id=self.session_id,script_rev=self.constraints.script_rev,
            constraints_rev=self.constraints.constraints_rev,authorized_answerers=allowed,candidates=deepcopy(candidates),
            expires_at=expiry,payload=payload,status='open')
        self.workflow['question'] = question
        state['decision'] = dict(request_id=request_id,status='open',question=prompt,authority=', '.join(allowed) or 'Unconfigured authority',
            bound=dict(script=self.constraints.script_rev,constraints=self.constraints.constraints_rev),opened_at=self._stamp(),
            expires_at=expiry,candidates=[visible_candidate(c) for c in candidates])
        self._queue('open_question',dict(payload=payload),f'question:{request_id}')
        self._event(state,'decision','A checked plan is ready for the named authority.',request_id)

    async def handle_outcome(self, outcome: Any) -> bool:
        outcome = normalize_outcome(outcome)
        if not outcome.get('request_id') or not outcome.get('session_id'):
            return False
        async with self.lock:
            state = self._state()
            request_id = outcome.get('request_id')
            session_id = outcome.get('session_id')
            key = f'{session_id}:{request_id}'
            with workflow_transaction(self):
                if not self.ledger.record_outcome(session_id,request_id,outcome):
                    return False
                self.workflow['outcomes'] = [*self.workflow['outcomes'],key][-200:]
                self._queue('mark_delivered',dict(request_id=request_id,session_id=session_id),f'delivered:{key}')
                q = self.workflow['question']
                if not q or q['request_id']!=request_id or q['session_id']!=session_id or not self._bound(q) or q['status']!='open':
                    self._event(state,'stale_reply','Ignored an outcome for an obsolete decision.',request_id)
                    self._save(state)
                    return False
                if self._now() >= datetime.fromisoformat(q['expires_at']):
                    q['status'] = 'expired'
                    state['decision']['status'] = 'expired'
                    self._save(state)
                    return False
                if outcome.get('answered_by') not in q['authorized_answerers']:
                    q['status']='rejected_unauthorized'
                    self.ledger.put('questions',q['request_id'],q,q['status'],q['constraints_rev'])
                    state['decision']['status'] = 'rejected_unauthorized'
                    self._event(state,'decision','Unauthorized answer recorded; replacement question issued.',request_id)
                    self.workflow['closed_questions'] = [*self.workflow['closed_questions'],request_id][-200:]
                    self._question(state,q['candidates'])
                    self._save(state)
                    return False
                candidate_id = outcome.get('candidate_id')
                if outcome.get('state') not in (None, 'answered'):
                    q['status'] = 'expired'
                    state['decision']['status'] = 'expired'
                    self._save(state)
                    return False
                candidate = next((c for c in q['candidates'] if c['candidate_id']==candidate_id),None)
                q['status'] = 'answered'
                state['decision']['status'] = 'answered'
                if candidate_id == 'neither':
                    self._neither(state,q,outcome)
                    self._save(state)
                    return False
                if not candidate:
                    self._event(state,'error','Answer did not identify a checked candidate.',request_id)
                    self._save(state)
                    return False
                manifest = Manifest.model_validate(candidate['manifest'])
                if self.workflow['holds'] or candidate['check']['result']!='pass' or manifest_hash(manifest)!=candidate['manifest_hash'] or check_candidate(manifest,self.constraints,state).result!='pass':
                    self._event(state,'error','Approval failed the final feasibility and content check.',request_id)
                    self._save(state)
                    return False
                state['decision']['answer'] = dict(candidate_id=candidate_id,note=outcome.get('note'),answered_by=outcome['answered_by'],at=self._stamp())
                self._release(state,candidate,q)
                self._save(state)
                return True

    def _neither(self, state: dict[str, Any], question: dict[str, Any], outcome: dict[str, Any]) -> None:
        note = (outcome.get('note') or '').strip()
        state['decision']['answer']=dict(candidate_id='neither',note=note,answered_by=outcome['answered_by'],at=self._stamp())
        if self.workflow.get('decision_round',1)>=2 or not note or len(note)>200:
            self._event(state,'decision','Neither selected; director must decide by hand after at most two rounds.',question['request_id'])
            self._queue('message',dict(body='Plan remains held. Director: decide by hand; automated rounds have stopped.'),f"manual:{question['request_id']}")
            return
        scene_ids = {c['manifest']['scene_id'] for c in question['candidates']}
        self.constraints = note_constraints(self.constraints,scene_ids,note)
        self._invalidate(state)
        self.workflow['decision_round']=2
        state['revisions']['constraints']=self.constraints.constraints_rev
        for scene in state['scenes']:
            if scene['id'] in scene_ids and note not in scene['hard']:
                scene['hard'].append(note)
        self._event(state,'decision','Director note is an unverified hard rule; one further round requested.',question['request_id'])
        state['jobs']=[]
        self._job(state,'script-supervisor',dict(scene_ids=sorted(scene_ids),change=dict(director_note=note)))

    def _release(self,state: dict[str, Any],candidate: dict[str, Any],question: dict[str, Any]) -> None:
        number = max((r['number'] for r in state['releases']),default=0)+1
        release_id = f'r{number}'
        m = candidate['manifest']
        summary = f"{m['scene_id']} moves to {m['location']}, {m['start']} to {m['end']}."
        expected = [p['id'] for p in state['crew'] if p['id'] in m['people']]
        for person in state['crew']:
            person['affected']=person['id'] in expected
            if person['affected']:
                person['acked_release']=None
        release = dict(release_id=release_id,number=number,status='approved',created_at=self._stamp(),
            manifest_hash=candidate['manifest_hash'],summary=summary,preview_url=candidate.get('preview_url'),
            publications=[dict(room=r,platform='discord',status='pending') for r in self.destinations],
            acks=dict(expected=expected,confirmed=[],policy='affected_only'))
        state['releases'].insert(0,release)
        self.workflow['releases'][release_id] = dict(script_rev=self.constraints.script_rev,constraints_rev=self.constraints.constraints_rev,
            candidate=deepcopy(candidate),request_id=question['request_id'])
        self._queue('release',dict(release_id=release_id,manifest=m,candidate_id=candidate['candidate_id'],manifest_hash=candidate['manifest_hash'],
            summary=summary,preview_url=candidate.get('preview_url'),destinations=self.destinations,
            snapshot=release_snapshot(state,m)),f'release:{release_id}')
        self._event(state,'release',f'Release {number} approved; publication pending.',release_id)

    def effect_current(self, effect: dict[str, Any]) -> bool:
        kind = effect.get('kind')
        if kind in ('hold','hold_message','close_question','mark_delivered','message'):
            return True
        revision = effect.get('revision')
        if revision != self.constraints.constraints_rev:
            return False
        if kind == 'document':
            return True
        payload = effect.get('payload',{})
        if isinstance(payload,str):
            payload = json.loads(payload)
        if kind == 'role_message':
            job = next((j for j in self.workflow['jobs'] if j['job_id']==payload.get('job_id')),None)
            return bool(job and self._bound(job) and job['status'] in ('queued','running'))
        if kind == 'open_question':
            q = self.workflow['question']
            return bool(q and q['status']=='open' and q['request_id']==payload['payload']['request_id'] and self._now()<datetime.fromisoformat(q['expires_at']))
        if kind == 'preview':
            return any(c['candidate_id']==payload.get('candidate_id') and c['manifest_hash']==payload.get('manifest_hash') and c['preview_status']=='rendering' for c in self.workflow['candidates'])
        if kind in ('release', 'publication_media', 'publication_text'):
            release = self.workflow['releases'].get(payload.get('release_id'))
            return bool(release and not self.workflow['holds'] and self._bound(release) and check_candidate(Manifest.model_validate(release['candidate']['manifest']),self.constraints,self._state()).result=='pass')
        return False

    async def publication_result(self,release_id: str,room: str,status: str) -> None:
        async with self.lock:
            state = self._state()
            with workflow_transaction(self):
                release = next((r for r in state['releases'] if r['release_id']==release_id),None)
                if not release or (release['status'] in ('published','superseded') and
                        any(p['room']==room and p['status']=='sent' for p in release['publications'])):
                    return
                for destination in release['publications']:
                    if destination['room']==room:
                        destination['status']=status
                if all(p['status']=='sent' for p in release['publications']):
                    release['status']='published'
                    for other in state['releases']:
                        if other is not release and other['status']=='published':
                            other['status']='superseded'
                    internal = self.workflow['releases'].get(release_id)
                    if internal and self._bound(internal):
                        candidate = internal['candidate']
                        for scene in state['scenes']:
                            if scene['id']==candidate['manifest']['scene_id']:
                                scene.update(validity='valid',hold_reason=None,plan={k:v for k,v in visible_candidate(candidate)['manifest'].items() if k in ('location','start','end','setup_min','wrap_min','people')})
                    else:
                        self._hold(state,[s['id'] for s in state['scenes'] if s['validity']!='valid'],'A newer change arrived during publication',release_id)
                    self._event(state,'release',f'{release_id} published.',release_id)
                self._save(state)

    async def confirm(self,person: str,release_id: str) -> bool:
        async with self.lock:
            state = self._state()
            current = state['releases'][0] if state['releases'] else None
            if not current or person not in {c['id'] for c in state['crew']} or current['release_id']!=release_id or current['status']!='published':
                with workflow_transaction(self):
                    self._event(state,'stale_reply',f'{person}: confirmation does not identify the current published release.',release_id)
                    self._save(state)
                return False
            with workflow_transaction(self):
                if person in current['acks']['expected'] and person not in {a['person'] for a in current['acks']['confirmed']}:
                    current['acks']['confirmed'].append(dict(person=person,at=self._stamp()))
                    for crew in state['crew']:
                        if crew['id']==person:
                            crew['acked_release']=current['number']
                    self._event(state,'ack',f'{person} confirmed {release_id}.',release_id)
                self._save(state)
            return True

    async def tick(self,now: datetime | None = None) -> None:
        async with self.lock:
            now = now or self._now()
            state = self._state()
            with workflow_transaction(self):
                for job in self.workflow['jobs']:
                    if job['status'] not in ('queued','running') or not self._bound(job):
                        continue
                    if job.get('retry_at'):
                        if now >= datetime.fromisoformat(job['retry_at']):
                            job.pop('retry_at')
                            job['deadline']=self._stamp(now+timedelta(seconds=self.job_timeout))
                            self._queue_job(job)
                    elif now >= datetime.fromisoformat(job['deadline']):
                        self._retry(state,job,'deadline elapsed',now)
                q = self.workflow['question']
                if q and q['status']=='open' and now>=datetime.fromisoformat(q['expires_at']):
                    q['status']='expired'
                    state['decision']['status']='expired'
                    self._queue('close_question',dict(request_id=q['request_id']),f"close:{q['request_id']}")
                    self._event(state,'decision','Question expired without approval.',q['request_id'])
                    self._queue('message',dict(body='Decision expired without approval. The hold remains; please request a new decision.'),f"expiry:{q['request_id']}")
                self._sync_jobs(state)
                self._save(state)

    async def preview_result(self, candidate_id: str, digest: str, url: str | None, status: str) -> bool:
        async with self.lock:
            candidate = next((c for c in self.workflow['candidates'] if c['candidate_id']==candidate_id and c['manifest_hash']==digest),None)
            if not candidate or candidate['preview_status']!='rendering':
                return False
            state = self._state()
            with workflow_transaction(self):
                candidate.update(preview_status='ready' if status=='ready' and url else 'failed',preview_url=url if status=='ready' else None)
                self.ledger.put('renders',digest,dict(candidate_id=candidate_id,manifest_hash=digest,url=url),candidate['preview_status'],self.constraints.constraints_rev)
                self._event(state,'render',f"{candidate['label']} preview {candidate['preview_status']}.",candidate_id)
                if all(c['preview_status']!='rendering' for c in self.workflow['candidates']):
                    self._question(state,self.workflow['candidates'])
                self._save(state)
            return True
