"""Real Switch/Mattermost transports for the isolated FLOW rehearsal.

Prior art: Switch console/packages/switch-agent-runtime/src/event-stream.ts,
core/switch_core/bridges/agent/api/{handlers,activity_routes}.py and
bridges/collaboration/session/text.py. Apache-2.0 with modified Commons Clause.
No server implementation is copied; all requests use the public transports.
"""
import asyncio
from pathlib import Path
import re
import secrets
from datetime import datetime
from typing import Any, Callable

from dotenv import dotenv_values
import httpx
from pydantic import BaseModel, Field, SecretStr
import yaml

from coordinator.config import Settings
from coordinator.switch_client import SwitchClient, _write_json
from coordinator.switch_models import Identity, Registration, RegistrationResponse, SwitchFrame

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'data/w4-demo'


class Person(BaseModel):
    id: str
    username: str


class Login(BaseModel):
    username: str
    password: SecretStr


class Posts(BaseModel):
    order: list[str] = Field(max_length=200)
    posts: dict[str,Any]


class Mattermost:
    def __init__(self) -> None:
        self.http=httpx.AsyncClient(base_url='http://127.0.0.1:8065/api/v4',timeout=30)
        self.tokens: dict[str,str]={}
        self.users: dict[str,Person]={}
        self.channel=''

    async def request(self, method: str, path: str, *, actor: str='admin', **kwargs: Any) -> httpx.Response:
        response=await self.http.request(method,path,headers={'Authorization':'Bearer '+self.tokens[actor]},**kwargs)
        response.raise_for_status()
        return response

    async def initialize(self) -> None:
        config=dotenv_values(ROOT/'scripts/switch/.env')
        response=await self.http.post('/users/login',json=dict(login_id=config['MATTERMOST_ADMIN_USER'],password=config['MATTERMOST_ADMIN_PASSWORD']))
        response.raise_for_status()
        self.tokens['admin']=response.headers['Token']
        team=(await self.request('GET','/teams/name/'+config.get('MATTERMOST_TEAM_NAME','switch'))).json()['id']
        cache=DIRECTORY/'.env'
        saved=dotenv_values(cache) if cache.exists() else {}
        people={}
        for role in ('director','producer','ad-human','maya','dev','leela'):
            prefix='W4_'+role.replace('-','_').upper()
            if saved.get(prefix+'_PASSWORD'):
                people[role]=Login(username=saved[prefix+'_USER'],password=saved[prefix+'_PASSWORD'])
        old_cache=DIRECTORY/'people.json'
        if not people and old_cache.exists():
            people={k:Login.model_validate(v) for k,v in __import__('json').loads(old_cache.read_text(encoding='utf-8')).items()}
            self._save_people(cache,people)
            # Preserve the legacy file: this run did not create it.
        for role in ('director','producer','ad-human','maya','dev','leela'):
            login=people.get(role) or Login(username='w4-'+role,password=secrets.token_urlsafe(24))
            if role not in people:
                created=await self.request('POST','/users',json=dict(username=login.username,email=login.username+'@take-two.local',password=login.password.get_secret_value()))
                person=Person.model_validate(created.json())
                people[role]=login
                self._save_people(cache,people)
            response=await self.http.post('/users/login',json=dict(login_id=login.username,password=login.password.get_secret_value()))
            response.raise_for_status()
            self.tokens[role]=response.headers['Token']
            person=Person.model_validate(response.json())
            self.users[role]=person
            added=await self.http.post(f'/teams/{team}/members',headers={'Authorization':'Bearer '+self.tokens['admin']},json=dict(team_id=team,user_id=person.id))
            if added.status_code not in (200,201,400):
                added.raise_for_status()
        self.team=team

    @staticmethod
    def _save_people(path: Path, people: dict[str,Login]) -> None:
        lines=[]
        for role,login in people.items():
            prefix='W4_'+role.replace('-','_').upper()
            lines += [prefix+'_USER='+login.username,prefix+'_PASSWORD='+login.password.get_secret_value()]
        director=people.get('director')
        if director:
            lines += ['TAKE_TWO_DIRECTOR_MM_USER='+director.username,'TAKE_TWO_DIRECTOR_MM_PASSWORD='+director.password.get_secret_value()]
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')

    async def join_channel(self, name: str) -> str:
        response=await self.request('GET',f'/teams/{self.team}/channels/name/{name}')
        self.channel=response.json()['id']
        for person in self.users.values():
            await self.request('POST',f'/channels/{self.channel}/members',json=dict(user_id=person.id))
        return self.channel

    async def post(self, actor: str, body: str, *, root_id: str | None=None) -> str:
        payload=dict(channel_id=self.channel,message=body)
        if root_id:
            payload['root_id']=root_id
        return (await self.request('POST','/posts',actor=actor,json=payload)).json()['id']

    async def card_handle(self, decision: dict[str,Any], position: int=1) -> str:
        choices=[c for c in decision['candidates'] if c['check']['result']=='pass']
        expected_hash=choices[position-1]['manifest_hash']
        earliest=int(datetime.fromisoformat(decision['opened_at']).timestamp()*1000)-1000
        async def find() -> str | None:
            response=Posts.model_validate((await self.request('GET',f'/channels/{self.channel}/posts?per_page=100')).json())
            import json
            for post in response.posts.values():
                encoded=json.dumps(post,ensure_ascii=False)
                if expected_hash not in encoded or post.get('create_at',0)<earliest or not post.get('props',{}).get('switch_publication'):
                    continue
                match=re.search(r'\bA[1-9][0-9]*\b',encoded)
                if match:
                    return match[0]
            return None
        return await wait_for(find,timeout=45,label='native Mattermost card')

    async def answer(self, decision: dict[str,Any], position: int, note: str | None=None) -> None:
        handle=await self.card_handle(decision,position)
        suffix=f', "{note}"' if note else ''
        await self.post('director',f'{handle} q1={position}{suffix}')

    async def answer_personal(self, card: dict[str,Any], actor: str, position: int, note: str | None=None) -> str:
        """Use the bridge's published native handle, exactly as a Mattermost person does."""
        import json
        earliest=int(datetime.fromisoformat(card['opened_at']).timestamp()*1000)-1000
        async def find() -> str | None:
            response=Posts.model_validate((await self.request('GET',f'/channels/{self.channel}/posts?per_page=100')).json())
            for post in sorted(response.posts.values(),key=lambda p:p.get('create_at',0),reverse=True):
                encoded=json.dumps(post,ensure_ascii=False)
                if post.get('create_at',0)<earliest or not post.get('props',{}).get('switch_publication'):
                    continue
                if card['request_id'] not in encoded and card['title'] not in encoded:
                    continue
                match=re.search(r'\bA[1-9][0-9]*\b',encoded)
                if match:
                    return match[0]
            return None
        handle=await wait_for(find,timeout=45,label='personal native Mattermost card')
        suffix=', '+json.dumps(note,ensure_ascii=False) if note else ''
        await self.post(actor,f'{handle} q1={position}{suffix}')
        return handle

    async def close(self) -> None:
        await self.http.aclose()


async def wait_for(read: Callable, *, timeout: float=180, label: str='state') -> Any:
    deadline=asyncio.get_running_loop().time()+timeout
    for _ in range(int(timeout*2)+1):
        value=await read()
        if value:
            return value
        if asyncio.get_running_loop().time()>=deadline:
            break
        await asyncio.sleep(0.5)
    raise TimeoutError('Timed out waiting for '+label)


async def identity(name: str, directory: Path = DIRECTORY) -> SwitchClient:
    settings=Settings()
    path=directory/(name+'.json')
    client=SwitchClient(settings.switch_api_url,path)
    if not path.exists():
        response=RegistrationResponse.model_validate(await client._exchange('POST','/agents',
            headers={'Authorization':'Bearer '+settings.switch_registration_key.get_secret_value()},
            json=Registration(name=name,connector_type='take-two-demo').model_dump(mode='json')))
        value=Identity(agent_id=response.id,api_key=response.api_key)
        _write_json(path,dict(**value.model_dump(mode='json',exclude={'api_key'}),api_key=value.api_key.get_secret_value()))
    await client.initialize()
    return client


class Stream:
    def __init__(self, client: SwitchClient) -> None:
        self.client=client
        self.opened=asyncio.Event()
        self.queue: asyncio.Queue[SwitchFrame]=asyncio.Queue(maxsize=256)
        self.task: asyncio.Task | None=None
        self.role: str | None=None

    def check(self) -> None:
        if self.task and self.task.done():
            self.task.result()
            raise ConnectionError('Rehearsal worker stream ended')

    async def claim_role(self, role: str, room_id: str) -> None:
        self.check()
        await asyncio.wait_for(self.opened.wait(),20)
        await self.client.connect_to_production(room_id)
        await self.client.operation('assume_role',dict(role=role))
        self.role=role

    async def start(self) -> None:
        # Each rehearsal starts fresh work; retain credentials, not old simulated jobs.
        self.client.resume_from({})
        self.client.on_transport_lost=self.opened.clear
        async def consume() -> None:
            async for frame in self.client.events():
                if frame.event=='connection_state':
                    if self.role:
                        await self.client.operation('assume_role',dict(role=self.role))
                    self.opened.set()
                elif frame.event in ('gap','evicted','refused'):
                    raise RuntimeError('Demo stream requires reconciliation: '+frame.event+' '+str(frame.data.get('code','')))
                elif frame.event=='message':
                    self.queue.put_nowait(frame)
        self.task=asyncio.create_task(consume())
        await asyncio.wait_for(self.opened.wait(),20)

    async def close(self) -> None:
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task,return_exceptions=True)
        await self.client.aclose()


async def provision(coordinator: SwitchClient, mm: Mattermost) -> str:
    rooms=await coordinator.member_rooms()
    room=next((r['room_id'] for r in rooms if r['name']=='w4-production'),None)
    if room:
        return room
    template=yaml.safe_load((ROOT/'templates/production.yaml').read_text(encoding='utf-8'))
    template['room']['users'] += [p.username for p in mm.users.values()]
    result=await coordinator.create_room_from_yaml(yaml.safe_dump(template),dict(name='w4-production',
        bridge='Mattermost',coordinator='w4-coordinator',script_supervisor='w4-supervisor',first_ad='w4-first-ad'))
    if result.failed_attachments:
        raise RuntimeError('Demo room has failed attachments')
    return result.room_id


async def allow_demo_people(agent_id: str, room_id: str, workers: list[str]) -> None:
    """Scope the rehearsal agent's addressing policy to its private test room.

    New Switch agents default to owner-only people. The coordinator separately
    validates the named director even when Switch accepts another member's answer.
    """
    config=dotenv_values(ROOT/'scripts/switch/.env')
    base=Settings().switch_api_url+'/gateway'
    async with httpx.AsyncClient(timeout=30) as http:
        login=await http.post(base+'/auth/login',json=dict(email=config['GATEWAY_ADMIN_EMAIL'],password=config['GATEWAY_ADMIN_PASSWORD']))
        login.raise_for_status()
        response=await http.put(base+f'/agents/{agent_id}/addressing-policy',json=dict(policy=dict(rules=[dict(
            rooms=[room_id],users='*',agents=workers,owner=True,owner_agents=True)])))
        response.raise_for_status()


async def close_old_demo_cards(client: SwitchClient) -> None:
    questions=client._questions()
    if len(questions)>400:
        raise ValueError('Rehearsal question history exceeds 400; archive it before another run')
    for key in questions:
        session,request=key.split(':',1)
        await client.close_question(request,session_id=session)
