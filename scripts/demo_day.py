"""A four-failure shoot day over real Switch; never calls Loop transitions.

Run twice with `uv run python -m scripts.demo_day`. Each run backs up/reset its
own offline ledger and compares normalized HTTP results with the previous run.
Prior art: scripts/demo_dry_run.py; Switch public clients referenced there.
"""
import asyncio
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import httpx
import uvicorn
import yaml
from pydantic import BaseModel, Field

from coordinator.api import create_app
from coordinator.config import Settings
from coordinator.runtime import Runtime
from coordinator.ui_models import State
from coordinator.unicode_text import require_unicode
from scripts.day_workers import identities, worker
from scripts.demo_switch import (ROOT, Mattermost, Stream,
    identity, wait_for, allow_demo_people, close_old_demo_cards, Posts)
from scripts.prepare_renderer import prepare
from scripts.reset_demo import reset_ledger

DIRECTORY=ROOT/'data/w8-demo'
FIXTURES=ROOT/'fixtures/ui-state/day'


class Beat(BaseModel):
    number: int
    name: str
    state: dict[str, Any]


class ChatProof(BaseModel):
    scenario: str
    hold: str=Field(max_length=4000)
    release: str=Field(max_length=4000)


def normalized(state: dict[str,Any]) -> dict[str,Any]:
    """Discard transport IDs/wall clocks; preserve all operational decisions."""
    decision=state.get('decision')
    return dict(revisions=state['revisions'],scenes=state['scenes'],
        changes=[{k:c.get(k) for k in ('entity','target','field','value','status','constraints_rev','resolution')} for c in state['changes']],
        jobs=[dict(role=j['role'],status=j['status']) for j in state['jobs']],
        decision=None if not decision else dict(status=decision['status'],bound=decision['bound'],
            candidates=[{k:c.get(k) for k in ('candidate_id','check','manifest_hash','manifest','schedule','preview_status')} for c in decision['candidates']],
            chosen=(decision.get('answer') or {}).get('candidate_id')),
        releases=[dict(number=r['number'],status=r['status'],manifest_hash=r['manifest_hash'],summary=r['summary'],
            publications=[dict(platform=p['platform'],status=p['status']) for p in r['publications']],
            duty_changes=r.get('duty_changes'),expected=r['acks']['expected'],confirmed=sorted(a['person'] for a in r['acks']['confirmed'])) for r in state['releases']],
        crew=[{k:p.get(k) for k in ('id','call_time','affected','acked_release','since_confirmed')} for p in state['crew']])


async def main(*, light_only: bool=False) -> None:
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    fixtures=ROOT/'fixtures/ui-state/light' if light_only else FIXTURES
    fixtures.mkdir(parents=True,exist_ok=True)
    cli=await asyncio.to_thread(prepare)
    mm=Mattermost()
    streams: list[Stream]=[]
    tasks: list[asyncio.Task]=[]
    runtime=None
    server=None
    api_task=None
    beats: list[Beat]=[]
    proofs: list[ChatProof]=[]
    clients=[]
    card_proofs: list[dict[str,Any]]=[]
    recorded_paths: set[Path]=set()
    try:
        await mm.initialize()
        clients=[await identity(name,DIRECTORY) for name in ('w8-coordinator','w8-supervisor','w8-first-ad')]
        bootstrap=Stream(clients[0])
        streams.append(bootstrap)
        await bootstrap.start()
        rooms=await clients[0].member_rooms()
        room=next((r['room_id'] for r in rooms if r['name']=='w8-production'),None)
        if not room:
            template=yaml.safe_load((ROOT/'templates/production.yaml').read_text(encoding='utf-8'))
            template['room']['users'] += [p.username for p in mm.users.values()]
            result=await clients[0].create_room_from_yaml(yaml.safe_dump(template),dict(name='w8-production',bridge='Mattermost',
                coordinator='w8-coordinator',script_supervisor='w8-supervisor',first_ad='w8-first-ad'))
            if result.failed_attachments:
                raise RuntimeError('Day room attachments failed')
            room=result.room_id
        await clients[0].connect_to_production(room)
        await allow_demo_people(clients[0].identity.agent_id,room,[c.identity.agent_id for c in clients[1:]])
        await close_old_demo_cards(clients[0])
        await mm.join_channel('w8-production')
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
        reset_ledger(database)
        settings=Settings(_env_file=None,switch_api_url=clients[0].base_url,
            take_two_db=database,take_two_identity=DIRECTORY/'w8-coordinator.json',
            take_two_artifacts=DIRECTORY/'artifacts',take_two_renderer_cli=cli,take_two_render_timeout=240,
            switch_production_room_id=room,switch_crew_room_ids=room,take_two_coordinator_name='w8-coordinator',
            take_two_coordinator_sender_id=senders['coordinator'],
            take_two_director_id=senders['director'],take_two_producer_id=senders['producer'],take_two_ad_id=senders['ad-human'],
            take_two_supervisor_sender_id=senders['w8-supervisor'],take_two_ad_sender_id=senders['w8-first-ad'],
            take_two_supervisor_agent_name='w8-supervisor',take_two_ad_agent_name='w8-first-ad',
            take_two_crew_identities={senders[role]:role for role in ('maya','dev','leela')})
        (DIRECTORY/'settings.json').write_text(settings.model_dump_json(exclude={'switch_registration_key'}),encoding='utf-8',newline='\n')
        runtime=Runtime(settings)
        await runtime.start()
        app=create_app(runtime.ledger,runtime.handle_ui_change,artifacts_dir=settings.take_two_artifacts)
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8789,log_level='error'))
        api_task=asyncio.create_task(server.serve())
        tasks=[asyncio.create_task(worker(stream,role,room)) for stream,role in zip(streams,('script-supervisor','first-ad'),strict=True)]
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8789',timeout=10) as api:
            started_at=int(datetime.now(timezone.utc).timestamp()*1000)
            async def state() -> dict[str,Any]:
                response=await api.get('/api/state')
                response.raise_for_status()
                State.model_validate(response.json())
                return response.json()
            async def capture(name: str) -> dict[str,Any]:
                current=await state()
                require_unicode(current)
                index=len(beats)+1
                # Write the actual HTTP JSON, not an invented projection.
                path=fixtures/f'{index:02}-{name}.json'
                path.write_text(json.dumps(current,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
                recorded_paths.add(path.resolve())
                beats.append(Beat(number=index,name=name,state=deepcopy(current)))
                print(f'Beat {index:02}: {name}',flush=True)
                return current
            async def ready() -> bool:
                return runtime.ready and server.started
            await wait_for(ready,timeout=60,label='day readiness')
            for stream,role in zip(streams,('script-supervisor','first-ad'),strict=True):
                await stream.claim_role(role,room)
            async def decision(rev: int) -> dict[str,Any] | None:
                for stream in streams:
                    stream.check()
                for task in tasks:
                    if task.done():
                        task.result()
                q=(await state())['decision']
                return q if q and q['status']=='open' and q['bound']['constraints']==rev else None
            async def published(number: int) -> dict[str,Any] | None:
                current=await state()
                r=current['releases'][0] if current['releases'] else None
                return current if r and r['number']==number and r['status']=='published' else None
            async def open_card(kind: str, person: str | None=None) -> dict[str,Any] | None:
                return next((q for q in runtime.loop.workflow.get('cards',{}).values()
                    if q['kind']==kind and q['status']=='open' and (person is None or q.get('person')==person)),None)
            async def answer_card(q: dict[str,Any], actor: str, position: int, note: str | None=None) -> None:
                handle=await mm.answer_personal(q,actor,position,note)
                card_proofs.append(dict(kind=q['kind'],person=q.get('person'),prompt=q['prompt'],
                    options=[o['label'] for o in q['options']],actor=actor,position=position,note=note,handle=handle))
            async def record_proposal() -> None:
                q=await wait_for(lambda:open_card('proposal'),timeout=60,label='authority proposal card')
                await answer_card(q,'ad-human',1)
                async def recorded_proposal() -> bool:
                    return runtime.loop.workflow['cards'][q['request_id']]['status']=='answered'
                await wait_for(recorded_proposal,timeout=30,label='authority record')
                current=await state()
                report=next(c for c in current['changes'] if c['id']==q['report_id'])
                recorded=next(c for c in current['changes'] if c['id']==report['resolved_by_change'])
                assert report['resolution']=='recorded' and recorded['status']=='recorded'
                assert report['resolved_at']==recorded['recorded_at']
            async def confirmations(number: int) -> None:
                release=(await state())['releases'][0]
                for person in release['acks']['expected']:
                    q=await wait_for(lambda:open_card('duty',person),timeout=30,label='duty card')
                    await answer_card(q,person,1)
                async def all_confirmed() -> bool:
                    r=(await state())['releases'][0]
                    return set(r['acks']['expected'])=={a['person'] for a in r['acks']['confirmed']}
                await wait_for(all_confirmed,timeout=30,label='current confirmations')
            async def matching_post(text: str, prefix: bool=False) -> str | None:
                posts=Posts.model_validate((await mm.request('GET',f'/channels/{mm.channel}/posts?per_page=100')).json())
                return next((p['message'] for p in posts.posts.values() if p.get('create_at',0)>=started_at
                    and p.get('message','').startswith(text) and (prefix or p['message']==text)),None)
            await mm.post('director','/plan day-1')
            q=await wait_for(lambda:decision(1),timeout=300,label='initial day decision')
            await capture('initial-decision')
            await mm.answer(q,1)
            await wait_for(lambda:published(1),timeout=300,label='initial release')
            await capture('r1-release')
            await confirmations(1)
            await capture('r1-confirmed')
            scenarios=[('rooftop','producer','/change location rooftop permission refused'),
                ('late-actor','ad-human','/change person dev late_by 40'),
                ('kit-failure','ad-human','/change capability sound_recorder unavailable'),
                ('overrun','ad-human','/change scene s1 overrun 25')]
            if light_only:
                scenarios=[('losing-light','producer','/change location rooftop light_until 17:20')]
            for number,(name,actor,command) in enumerate(scenarios,2):
                before=(await state())['revisions']['constraints']
                if name=='late-actor':
                    q=await wait_for(lambda:open_card('duty','dev'),timeout=30,label='Dev duty card')
                    await answer_card(q,'dev',2,'Running 40 min late')
                    async def report_received() -> bool:
                        return any(c['id']=='duty-report:'+q['request_id'] for c in (await state())['changes'])
                    await wait_for(report_received,timeout=30,label='Dev pending report')
                    await capture('dev-cannot-make-it')
                    await record_proposal()
                else:
                    await mm.post(actor,command)
                async def recorded() -> bool:
                    current=await state()
                    return current['revisions']['constraints']==before+1 and current['changes'][0]['status']=='recorded'
                await wait_for(recorded,timeout=30,label=name+' recorded')
                current=await capture(name+'-recorded')
                hold=next(t['text'] for t in current['timeline'] if t['kind']=='hold' and t['ref']==current['changes'][0]['id'])
                await wait_for(lambda:matching_post(hold),timeout=30,label='HOLD accepted in chat')
                await capture(name+'-hold')
                q=await wait_for(lambda:decision(before+1),timeout=300,label=name+' decision')
                if name=='rooftop':
                    await capture('rooftop-before-maya-report')
                    await mm.post('maya','I have to leave at 6')
                    await record_proposal()
                    q=await wait_for(lambda:decision(before+2),timeout=300,label='updated rooftop decision')
                    await capture('maya-change-confirmed')
                assert all(c['check']['result']=='pass' for c in q['candidates'])
                await capture(name+'-decision')
                await mm.answer(q,1)
                await wait_for(lambda:published(number),timeout=300,label=name+' release')
                current=await capture(f'r{number}-release')
                text=await wait_for(lambda:matching_post(f'TAKE TWO · Release {number} ',True),timeout=30,label='release chat')
                proofs.append(ChatProof(scenario=name,hold=hold,release=text))
                if name!='rooftop' or light_only:
                    await confirmations(number)
                current=await capture(f'r{number}-'+('awaiting-crew' if name=='rooftop' and not light_only else 'confirmed'))
                assert all(s['validity']=='valid' for s in current['scenes'])
            assert sum(c['status']=='recorded' for c in current['changes'])==len(scenarios)+(0 if light_only else 1)
            assert [r['number'] for r in current['releases']]==list(range(len(scenarios)+1,0,-1))
            assert not [c for c in current['changes'] if c['status']=='pending_confirmation' and not c.get('resolution')]
            for release in current['releases']:
                for lines in release['duty_changes'].values():
                    assert not any(token in line for line in lines for token in ('camera_sound','sound_recorder','kit none','was unconfirmed'))
            results=[dict(number=b.number,name=b.name,result=normalized(b.state)) for b in beats]
            # Worker statuses at record/hold can race network delivery, so compare
            # those beats by the committed facts/holds; decision/release beats retain jobs.
            for item in results:
                if item['name'].endswith(('-recorded','-hold')):
                    item['result'].pop('jobs',None)
                    item['result'].pop('decision',None)
            result=dict(beats=results,chat=[p.model_dump() for p in proofs])
            suffix='-light' if light_only else ''
            previous=DIRECTORY/f'normalized{suffix}.json'
            compared=previous.exists()
            if compared:
                assert json.loads(previous.read_text(encoding='utf-8'))==result,'Normalized day differs from previous reset run'
            previous.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
            (DIRECTORY/f'cards{suffix}.json').write_text(json.dumps(card_proofs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
            (DIRECTORY/f'chat{suffix}.json').write_text(json.dumps([p.model_dump() for p in proofs],ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
            (DIRECTORY/f'last-run{suffix}.json').write_text(json.dumps(dict(state=current,compared=compared,beats=len(beats)),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
            # Preserve prior fixture files with obsolete names; never delete them.
            archive=DIRECTORY/'fixture-archive'/datetime.now().strftime('%Y%m%d%H%M%S%f')
            for old in fixtures.glob('*.json'):
                if old.resolve() in recorded_paths:
                    continue
                target=archive/old.name
                if not old.resolve().is_relative_to(FIXTURES.parent.resolve()) or not target.resolve().is_relative_to(DIRECTORY.resolve()):
                    raise ValueError('Fixture archive must remain inside the workspace')
                archive.mkdir(parents=True,exist_ok=True)
                old.replace(target)
            print(json.dumps(dict(release=current['releases'][0]['release_id'],beats=len(beats),normalized_match=compared,expected=current['releases'][0]['acks']['expected'])),flush=True)
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
        for client in clients:
            await client.aclose()
        await mm.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--light-only',action='store_true',help='Separate real-loop exterior light rehearsal; writes light/ fixtures')
    asyncio.run(main(light_only=parser.parse_args().light_only))
