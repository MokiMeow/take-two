"""Exercise FLOW over real Switch and Mattermost; never call Loop transitions."""
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from coordinator.api import create_app
from coordinator.config import Settings
from coordinator.runtime import Runtime
from coordinator.ui_models import State
from coordinator.worker_text import extract_reply
from coordinator.switch_models import RoomContext
from coordinator.ledger import now_iso
from scripts.demo_switch import DIRECTORY, Mattermost, Stream, identity, provision, wait_for, allow_demo_people, close_old_demo_cards
from scripts.prepare_renderer import prepare
from scripts.reset_demo import reset_ledger
from scripts.seed_initial_plan import post_plan
from dotenv import dotenv_values
from coordinator.unicode_text import require_unicode


def scene(scene_id: str, location: str, start: str, end: str, rev: int, *, setup: int=15,
          wrap: int=0, reduced: bool=False) -> dict[str,Any]:
    return dict(scene_id=scene_id,location=location,start=f'2026-11-06T{start}:00+05:30',
        end=f'2026-11-06T{end}:00+05:30',setup_min=setup,wrap_min=wrap,
        people=['dev','leela'] if scene_id=='s1' else ['maya','dev','leela'],
        shots=['two-shot','close-up'] if reduced else ['wide','two-shot','close-up'],
        capabilities=['sound_recorder'],requires_light=location in ('park','courtyard','rooftop'),
        script_rev=1,constraints_rev=rev)


def candidates(job: dict[str,Any]) -> list[dict[str,Any]]:
    rev=job['constraints_rev']
    def option(identifier: str, label: str, m: dict[str,Any], cost: str) -> dict[str,Any]:
        return dict(candidate_id=identifier,label=label,story_cost=cost,manifest=m)
    if job.get('initial_plan'):
        return [dict(candidate_id='initial',label='Initial three-scene schedule',story_cost='Reviewed script and locations.',
            manifests=[scene('s1','stairwell','15:00','15:15',rev),scene('s2','courtyard','15:25','15:35',rev,setup=0),
                scene('s3','rooftop','16:45','18:15',rev)])]
    full=option('stairs-full','Stairwell, full coverage',scene('s3','stairwell','16:00','17:15',rev,wrap=10),
        'Loses the sunset silhouette; keeps the confession private.')
    park=option('park','Park bench, sunset',scene('s3','park','16:45','18:15',rev),
        'Keeps sunset; passers-by make it less visually intimate, still confidential in the story.')
    if rev==2:
        courtyard=option('courtyard','Courtyard, late',scene('s3','courtyard','17:15','18:15',rev),
            'Permission window ends too early.')
        return [courtyard,full,park]
    reduced=option('stairs-reduced','Stairwell, reduced coverage',scene('s3','stairwell','16:30','17:15',rev,wrap=10,reduced=True),
        'Keeps the confession private; loses one wide angle and gains setup buffer.')
    return [full,reduced,park]


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
            reply.update(must_keep=['confession is intelligible and confidential in the story'],
                preferences=['visually secluded','sunset'],summary='Preserve the reviewed story and required cast; creative prose needs director review.')
        else:
            reply['candidates']=candidates(job)
        await stream.client.send_message(room_id,'@w4-coordinator Here is my answer:\n```json\n'+json.dumps(reply)+'\n```')
    raise RuntimeError('Simulated worker exceeded its bounded message budget')


async def identities(bootstrap: Stream, mm: Mattermost, workers: list[Stream], room_id: str) -> dict[str,str]:
    names={person.username:role for role,person in mm.users.items()}
    since=now_iso()
    receipt=await bootstrap.client.send_message(room_id,'W5 registered rehearsal identity: w4-coordinator')
    async def own_sender() -> str | None:
        context=RoomContext.model_validate(await bootstrap.client.read_context(room_id,since))
        if context.truncated:
            raise ValueError('Identity history is truncated')
        return next((e.sender for t in context.threads for e in [t.root,*t.replies] if e.id==receipt.event_id),None)
    coordinator_sender=await wait_for(own_sender,timeout=30,label='coordinator transport identity')
    for role,person in mm.users.items():
        await mm.post(role,'W4 registered rehearsal identity: '+person.username)
    for name,stream in zip(('w4-supervisor','w4-first-ad'),workers,strict=True):
        names[name]=name
        await stream.client.send_message(room_id,'W4 registered rehearsal identity: '+name)
    found={}
    for _ in range(100):
        frame=await asyncio.wait_for(bootstrap.queue.get(),30)
        payload=frame.data.get('payload',{})
        name=payload.get('sender_name')
        if name in names:
            found[names[name]]=payload['sender']
        if len(found)==len(names):
            return dict(coordinator=coordinator_sender,**found)
    raise RuntimeError('Could not resolve separate authenticated test identities')


async def main() -> None:
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    cli=await asyncio.to_thread(prepare)
    mm=Mattermost()
    streams: list[Stream]=[]
    tasks: list[asyncio.Task]=[]
    runtime=None
    server=None
    api_task=None
    try:
        await mm.initialize()
        clients=[await identity(name) for name in ('w4-coordinator','w4-supervisor','w4-first-ad')]
        bootstrap=Stream(clients[0])
        streams.append(bootstrap)
        await bootstrap.start()
        room=await provision(clients[0],mm)
        await clients[0].connect_to_production(room)
        await allow_demo_people(clients[0].identity.agent_id,room,[c.identity.agent_id for c in clients[1:]])
        await close_old_demo_cards(clients[0])
        await mm.join_channel('w4-production')
        for client,role in zip(clients[1:],('script-supervisor','first-ad'),strict=True):
            client.production_room_id=room
            stream=Stream(client)
            streams.append(stream)
            await stream.start()
            await stream.claim_role(role,room)
        senders=await identities(bootstrap,mm,streams[1:],room)
        await bootstrap.close()
        streams.remove(bootstrap)
        database=DIRECTORY/'ledger.sqlite'
        backup=await asyncio.to_thread(reset_ledger,database)
        settings=Settings(_env_file=None,switch_api_url=clients[0].base_url,
            take_two_db=database,take_two_identity=DIRECTORY/'w4-coordinator.json',
            take_two_artifacts=DIRECTORY/'artifacts',take_two_renderer_cli=cli,take_two_render_timeout=240,
            switch_production_room_id=room,switch_crew_room_ids=room,take_two_coordinator_name='w4-coordinator',
            take_two_coordinator_sender_id=senders['coordinator'],
            take_two_director_id=senders['director'],take_two_producer_id=senders['producer'],take_two_ad_id=senders['ad-human'],
            take_two_supervisor_sender_id=senders['w4-supervisor'],take_two_ad_sender_id=senders['w4-first-ad'],
            take_two_supervisor_agent_name='w4-supervisor',take_two_ad_agent_name='w4-first-ad',
            take_two_crew_identities={senders[role]:role for role in ('maya','dev','leela')})
        (DIRECTORY/'settings.json').write_text(settings.model_dump_json(exclude={'switch_registration_key'}),encoding='utf-8',newline='\n')
        runtime=await asyncio.to_thread(Runtime,settings)
        await runtime.start()
        app=create_app(runtime.ledger,runtime.handle_ui_change,artifacts_dir=settings.take_two_artifacts)
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8788,log_level='error'))
        api_task=asyncio.create_task(server.serve())
        tasks=[asyncio.create_task(worker(stream,role,room)) for stream,role in zip(streams,('script-supervisor','first-ad'),strict=True)]
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8788',timeout=10) as api:
            async def state() -> dict[str,Any]:
                response=await api.get('/api/state')
                response.raise_for_status()
                return State.model_validate(response.json()).model_dump(mode='json')
            async def ready() -> bool:
                return runtime.ready and server.started
            await wait_for(ready,timeout=60,label='coordinator catch-up readiness')
            for stream,role in zip(streams,('script-supervisor','first-ad'),strict=True):
                await stream.claim_role(role,room)
            credentials=dotenv_values(DIRECTORY/'.env')
            await post_plan(mm.http,'http://127.0.0.1:8065',credentials['TAKE_TWO_DIRECTOR_MM_USER'],
                credentials['TAKE_TWO_DIRECTOR_MM_PASSWORD'],mm.channel)
            async def decision(rev: int) -> dict[str,Any] | None:
                for stream in streams:
                    stream.check()
                current=(await state())['decision']
                if current and current['status']=='open' and current['bound']['constraints']==rev:
                    return current
                for task in tasks:
                    if task.done():
                        task.result()
                return None
            q=await wait_for(lambda:decision(1),label='initial checked schedule')
            await mm.answer(q,1)
            async def published(number: int) -> dict[str,Any] | None:
                current=await state()
                return current if current['releases'] and current['releases'][0]['number']==number and current['releases'][0]['status']=='published' else None
            await wait_for(lambda:published(1),timeout=300,label='release 1 publication')
            for role in ('maya','dev','leela'):
                await mm.post(role,'confirm r1')
            await mm.post('producer','/change location rooftop permission refused')
            q2=await wait_for(lambda:decision(2),timeout=300,label='stairwell and park preview card')
            assert [c['check']['result'] for c in q2['candidates']]==['fail','pass','pass']
            assert sum(c['preview_status']=='ready' for c in q2['candidates'])==2
            await mm.card_handle(q2)
            await mm.post('maya','Sorry, I have to leave at 6.')
            await mm.post('ad-human','/change person maya hard_stop 18:00')
            q3=await wait_for(lambda:decision(3),timeout=300,label='revised stairwell preview card')
            assert q3['request_id']!=q2['request_id']
            assert [c['check']['result'] for c in q3['candidates']]==['pass','pass','fail']
            assert sum(c['preview_status']=='ready' for c in q3['candidates'])==2
            await mm.answer(q3,2,'keep the confession private')
            final=await wait_for(lambda:published(2),timeout=300,label='release 2 publication')
            assert all(s['validity']=='valid' for s in final['scenes'])
            await mm.post('dev','ok see you at rooftop on release 1')
            async def corrected() -> bool:
                current=await state()
                local=any(t['kind']=='stale_reply' and '@Dev' in t['text'] and 'release 2' in t['text'] for t in current['timeline'])
                posts=(await mm.request('GET',f'/channels/{mm.channel}/posts?per_page=30')).json()['posts']
                delivered=any('@Dev that was release 1.' in p.get('message','') and 'release 2' in p.get('message','') for p in posts.values())
                return local and delivered
            await wait_for(corrected,timeout=30,label='Dev stale reply correction')
            for role in final['releases'][0]['acks']['expected']:
                await mm.post(role,'confirm r2')
            async def confirmed() -> dict[str,Any] | None:
                current=await state()
                r=current['releases'][0]
                return current if {a['person'] for a in r['acks']['confirmed']}==set(r['acks']['expected']) else None
            final=await wait_for(confirmed,timeout=30,label='affected-call confirmations')
            assert final['revisions']==dict(script=1,constraints=3)
            assert final['releases'][0]['call_sheet_url'] and final['releases'][0]['preview_url']
            # These assertions inspect the real HTTP state, not local Loop internals.
            require_unicode(final)
            assert len(final['changes']) == 3, 'Room chatter became reported changes'
            assert len([c for c in final['changes'] if c['field']=='report']) == 1
            assert next(c for c in final['changes'] if c['field']=='report')['reporter_name'] == 'Maya'
            hard_stop = next(c for c in final['changes'] if c['field']=='hard_stop')
            assert hard_stop['value']=='18:00' and hard_stop['at']=='2026-11-06T18:00:00+05:30'
            assert final['decision']['authority_name']=='Arun'
            assert final['decision']['answer']['answered_by_name']=='Arun'
            assert all(c['reporter_name'] in ('Nila','Isha','Maya') for c in final['changes'])
            assert all(p['role_label'] for p in final['crew'])
            assert all(p['room_name']=='#production' for r in final['releases'] for p in r['publications'])
            assert not any('@switch-' in t['text'] for t in final['timeline'])
            summary=dict(revisions=final['revisions'],release='r2',status=final['releases'][0]['status'],
                publication='accepted by Switch for relay',room='w4-production (Mattermost)',discord='no Discord bridge yet',
                scenes=[dict(number=s['number'],validity=s['validity'],location=s['plan']['location']) for s in final['scenes']],
                confirmed=sorted(a['person'] for a in final['releases'][0]['acks']['confirmed']),
                dev_stale_reply_corrected=True,preview_counts=[2,2])
            proof=DIRECTORY/'last-run.json'
            proof.write_text(json.dumps(dict(summary=summary,state=final),ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
            print(json.dumps(summary,ensure_ascii=False,indent=2))
    finally:
        if server:
            server.should_exit=True
        if api_task:
            await asyncio.wait_for(api_task,15)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        if runtime:
            await runtime.close()
        for stream in streams:
            await stream.close()
        await mm.close()


if __name__=='__main__':
    asyncio.run(main())
