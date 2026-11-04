"""Simulated people/proposals for a real Switch transport rehearsal only.

Prior art: scripts/demo_dry_run.py and Switch
console/packages/switch-agent-runtime/src/event-stream.ts (public protocol).
Switch license: Apache-2.0 with modified Commons Clause; no server code copied.
"""
import asyncio
from copy import deepcopy
from typing import Any
import json

from coordinator.worker_text import extract_reply
from coordinator.switch_models import RoomContext
from coordinator.ledger import now_iso
from scripts.demo_dry_run import scene
from scripts.demo_switch import Stream, Mattermost, wait_for


def candidates(job: dict[str, Any]) -> list[dict[str, Any]]:
    rev=job['constraints_rev']
    if job.get('initial_plan'):
        rows=[scene('s1','stairwell','15:00','15:15',rev),
              scene('s2','courtyard','15:25','15:35',rev,setup=0),
              scene('s3','rooftop','16:45','18:15',rev)]
        label='Initial three-scene schedule'
    else:
        rows=[dict(deepcopy(m),constraints_rev=rev) for m in job['current_schedule'] if m['scene_id'] in job['scene_ids']]
        by_id={m['scene_id']:m for m in rows}
        change=job['change']
        if change['field'] in ('permission','light_until'):
            by_id['s3'].update(location='stairwell',start='2026-11-06T16:45:00+05:30',
                end='2026-11-06T18:00:00+05:30',requires_light=False)
            label='Stairwell confession, keep early work'
        elif change['field'] in ('late_by','available'):
            by_id['s1'].update(start='2026-11-06T15:40:00+05:30',end='2026-11-06T15:55:00+05:30')
            by_id['s2'].update(start='2026-11-06T16:05:00+05:30',end='2026-11-06T16:15:00+05:30')
            label='Wait for Dev, move early scenes'
        elif change['entity']=='capability':
            for m in rows:
                m['capabilities']=['lav']
            label='Use the confirmed lav, keep every call'
        elif change['field']=='overrun':
            by_id['s1']['end']='2026-11-06T16:20:00+05:30'
            by_id['s2'].update(start='2026-11-06T16:20:00+05:30',end='2026-11-06T16:30:00+05:30')
            label='Record the overrun, move the promise'
        else:
            raise ValueError('Unexpected rehearsal change')
    return [dict(candidate_id=f'day-{rev}',label=label,story_cost='Keep reviewed dialogue; the director reviews the schedule.',manifests=rows)]


async def worker(stream: Stream, role: str, room_id: str) -> None:
    handled: set[tuple[str,int]]=set()
    for _ in range(200):
        frame=await asyncio.wait_for(stream.queue.get(),300)
        body=frame.data.get('payload',{}).get('body','')
        if '@'+role not in body:
            continue
        try:
            job=extract_reply(body)
        except ValueError:
            continue
        if 'constraints' not in job or not job.get('job_id'):
            continue
        key=(job['job_id'],job.get('attempt',0))
        if key in handled:
            continue
        handled.add(key)
        reply={k:job[k] for k in ('job_id','script_rev','constraints_rev','addressed_to')}
        if role=='script-supervisor':
            reply.update(must_keep=['Keep all reviewed dialogue intelligible; the confession remains confidential in the story.'],
                summary='Use confirmed audio; do not drop sound or required cast.')
        else:
            reply['candidates']=candidates(job)
        await stream.client.send_message(room_id,'@w6-coordinator\n```json\n'+json.dumps(reply)+'\n```')
    raise RuntimeError('Day worker exceeded 200 frames')


async def identities(bootstrap: Stream, mm: Mattermost, workers: list[Stream], room: str) -> dict[str,str]:
    since=now_iso()
    receipt=await bootstrap.client.send_message(room,'W6 rehearsal identity')
    async def own() -> str | None:
        history=RoomContext.model_validate(await bootstrap.client.read_context(room,since))
        if history.truncated:
            raise ValueError('Identity history truncated')
        return next((e.sender for t in history.threads for e in [t.root,*t.replies] if e.id==receipt.event_id),None)
    found={'coordinator':await wait_for(own,timeout=30,label='coordinator identity')}
    names={person.username:role for role,person in mm.users.items()}
    for role,person in mm.users.items():
        await mm.post(role,'W6 rehearsal identity: '+person.username)
    for name,stream in zip(('w6-supervisor','w6-first-ad'),workers,strict=True):
        names[name]=name
        await stream.client.send_message(room,'W6 rehearsal identity: '+name)
    for _ in range(100):
        frame=await asyncio.wait_for(bootstrap.queue.get(),30)
        payload=frame.data.get('payload',{})
        if payload.get('sender_name') in names:
            found[names[payload['sender_name']]]=payload['sender']
        if len(found)==len(names)+1:
            return found
    raise RuntimeError('Rehearsal identities not resolved')
