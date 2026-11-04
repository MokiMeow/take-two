from typing import Any
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import httpx
import pytest

from coordinator.dispatcher import Dispatcher
from coordinator.render_props import callsheet_props, release_text
from coordinator.schedules import check_schedule
from coordinator.constraints import Manifest
from coordinator.switch_models import Identity, SwitchFrame
from coordinator.tests.test_w4_workflow import runtime, initial, change, reply, manifest
from scripts.reset_demo import reset_ledger


async def test_decision_uploads_two_bound_previews_before_native_card(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    rt.loop.renderer=object()
    await reply(rt.loop,must_keep=['Keep the confession private'])
    await reply(rt.loop,candidates=[dict(candidate_id=name,label=label,story_cost='Keeps confidentiality',
        manifest=manifest(location=location,revision=2)) for name,label,location in (
            ('stairs','Stairwell','stairwell'),('park','Park bench','park'))])
    for c in list(rt.loop.workflow['candidates']):
        path=tmp_path/(c['candidate_id']+'.mp4')
        path.write_bytes(b'\x00\x00\x00\x18ftypisomactual-test-bytes')
        await rt.loop.preview_result(c['candidate_id'],c['manifest_hash'],'/media/'+path.name,'ready')
    q=rt.loop.workflow['question']
    for effect in rt.ledger.pending_effects():
        if effect['kind']!='open_question' or effect['payload']['payload']['request_id']!=q['request_id']:
            rt.ledger.effect_status(effect['id'],'cancelled')
    sent=[]
    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        if request.url.path.endswith('/media'):
            return httpx.Response(200,json=dict(ok=True,event_id='preview-'+str(len(sent)),attachments=[]))
        return httpx.Response(200,json=dict(sessionId=rt.loop.session_id,requestId=q['request_id'],kind='questions',state='open'))
    rt.client.http=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    rt.client._identity=Identity(agent_id='coordinator',api_key='test-secret')
    rt.client.production_room_id='production'
    d=Dispatcher(rt.ledger,rt.loop,rt.client,production_room_id='production',crew_room_ids=['production'],renderer=SimpleNamespace(artifacts_dir=tmp_path))
    await d.run_once()
    assert [r.url.path.rsplit('/',1)[-1] for r in sent]==['media','media','approvals']
    card=json.loads(sent[-1].content)
    assert 'not machine-checked' in card['questions'][0]['prompt']
    assert 'A · Stairwell' in card['questions'][0]['options'][0]['description']
    assert 'B · Park bench' in card['questions'][0]['options'][1]['description']
    assert len([k for k in rt.ledger.connection.execute("SELECT key FROM meta WHERE key LIKE 'presentation:%'")])==2
    await rt.close()


async def test_uncertain_preview_upload_never_opens_or_retries_card(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    for effect in rt.ledger.pending_effects():
        rt.ledger.effect_status(effect['id'],'cancelled')
    file=tmp_path/'option.mp4'
    file.write_bytes(b'\x00\x00\x00\x18ftypisombytes')
    q=rt.loop.workflow['question']
    q['status']='open'
    payload=dict(payload=q['payload'],presentations=[dict(candidate_id='initial',preview_url='/media/option.mp4',summary='Checked A')])
    with rt.ledger.transaction():
        eid=rt.ledger.enqueue('open_question',payload,'uncertain-presentation',1)
    calls=[]
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout('Unknown delivery',request=request)
    rt.client.http=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    rt.client._identity=Identity(agent_id='coordinator',api_key='test-secret')
    rt.client.production_room_id='production'
    d=Dispatcher(rt.ledger,rt.loop,rt.client,production_room_id='production',crew_room_ids=['production'],renderer=SimpleNamespace(artifacts_dir=tmp_path),retry_delay=0)
    await d.run_once()
    assert len([r for r in calls if r.url.path.endswith('/media')])==1
    assert all(not r.url.path.endswith('/approvals') for r in calls)
    assert rt.ledger.effect(eid)['status']=='uncertain'
    await rt.close()


async def test_oversized_worker_frame_gets_one_retry_instead_of_quarantine(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    rt.client._identity=Identity(agent_id='coordinator',api_key='test-secret')
    rt.loop.coordinator_id='coordinator'
    rt.loop.worker_ids={'script-supervisor':'supervisor'}
    for i in range(2):
        await rt.accept_frame(SwitchFrame(event='message',data=dict(room_id='production',payload=dict(
            sender='supervisor',body='x'*65537,message_id=f'oversize-{i}'))))
    assert rt.loop.workflow['jobs'][-1]['status']=='failed'
    assert not any('quarantined' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
    await rt.close()


async def test_complete_release_is_immutable_and_text_uses_trusted_metadata(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    saved=deepcopy(rt.loop.workflow['releases']['r1']['envelope'])
    await change(rt.loop)
    assert rt.loop.workflow['releases']['r1']['envelope']==saved
    text=release_text(saved)
    assert 'TAKE TWO · Release 1 (white pages) · The Last Light, Day 1' in text
    assert 'Sc 2* · A promise · EXT. COURTYARD · 15:25–15:35' in text
    assert 'Maya 15:25' in text and 'Dev 15:00' in text
    assert '2026-' not in text
    assert 'Replies about release 1' not in text
    assert rt.ledger.snapshot_state()['production']['day']=='Day 1 - 6 November'
    await rt.close()


async def test_replacing_scene_frees_its_old_commitment(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    proposed=Manifest.model_validate(manifest('s2','courtyard','15:00','15:10'))
    # s2's old 15:25 duty is replaced; the genuine s1 conflict still fails.
    retained=list(rt.loop.workflow['plans'].values())
    assert check_schedule([proposed],rt.loop.constraints,retained).result=='fail'
    proposed=Manifest.model_validate(manifest('s2','courtyard','15:20','15:40'))
    assert check_schedule([proposed],rt.loop.constraints,retained).result=='pass'
    await rt.close()


def test_reset_backs_up_ledger_and_preserves_identity(tmp_path: Path) -> None:
    database=tmp_path/'ledger.sqlite'
    identity=tmp_path/'identity.json'
    identity.write_bytes(b'identity-must-not-change')
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE meta (key TEXT PRIMARY KEY,value TEXT)')
        connection.execute("INSERT INTO meta VALUES ('decision','answered')")
    backup=reset_ledger(database,tmp_path/'backups')
    with sqlite3.connect(backup) as connection:
        assert connection.execute('SELECT value FROM meta').fetchone()[0]=='answered'
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT count(*) FROM meta').fetchone()[0]==0
    assert identity.read_bytes()==b'identity-must-not-change'


async def test_no_discord_bridge_is_visible_and_idempotent(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    async def operation(name: Any) -> Any:
        assert name=='list_bridges'
        return []
    rt.client.operation=operation
    await rt.provision_day()
    await rt.provision_day()
    assert rt.ledger.get_meta('day_room_status')=='no_discord_bridge'
    assert len([e for e in rt.ledger.pending_effects() if e['key']=='no-discord-bridge'])==1
    assert any('No Discord bridge yet' in t['text'] for t in rt.ledger.snapshot_state()['timeline'])
    await rt.close()


async def test_discord_day_room_uses_template_and_owns_document(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    rt.settings.take_two_day_actor='maya_demo'
    rt.settings.take_two_day_camera='dev_demo'
    rt.settings.take_two_day_sound='leela_demo'
    rt.client._identity=Identity(agent_id='coordinator',api_key='test-secret')
    calls=[]
    async def operation(name: Any) -> Any:
        return [dict(id='discord',type='discord',display_name='Shoot Discord',status='active',can_create_channels=True)]
    async def rooms() -> Any:
        return []
    async def provision(template: Any, inputs: Any) -> Any:
        import yaml
        assert yaml.safe_load(template)['room']['channel_type']=='channel_private'
        assert inputs['bridge']=='Shoot Discord'
        calls.append('template')
        return SimpleNamespace(room_id='day-room',failed_attachments=[])
    async def connect(room: Any) -> Any:
        calls.append(room)
        return dict(documents=[])
    async def document(*args: Any) -> Any:
        calls.append('owned-document')
        return SimpleNamespace(document_id='day-doc')
    rt.client.operation=operation
    rt.client.member_rooms=rooms
    rt.client.create_room_from_yaml=provision
    rt.client.connect_to_production=connect
    rt.client.create_room_document=document
    await rt.provision_day()
    assert calls==['template','day-room','owned-document','production']
    assert rt.ledger.get_meta('day_room_id')=='day-room'
    assert rt.ledger.get_meta('day_room_status')=='ready'
    assert 'day-room' in rt.loop.destinations
    await rt.close()


@pytest.mark.parametrize('collection,count', [('locations',9),('people',31),('scenes',21)])
def test_trusted_fixture_counts_fit_renderer(collection: str, count: int) -> None:
    from pydantic import ValidationError
    from coordinator.constraints import Constraints
    from coordinator.runtime import read_yaml
    facts=read_yaml('constraints-r1.yaml')
    sample=facts[collection][0]
    facts[collection]=[dict(sample,id=f'item-{i}') for i in range(count)]
    with pytest.raises(ValidationError):
        Constraints.model_validate(facts)


async def test_long_failure_diagnostic_fits_state_instead_of_crashing(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    with rt.ledger.transaction():
        rt.ledger.timeline('error','render-error: '+'x'*2048)
    item=rt.ledger.snapshot_state()['timeline'][0]
    assert len(item['text'])==512
    assert item['text'].startswith('render-error: ')
    await rt.close()


async def test_identical_manifests_with_distinct_labels_do_not_strand_previews(tmp_path: Path) -> None:
    rt=runtime(tmp_path)
    await initial(rt.loop)
    await change(rt.loop)
    rt.loop.renderer=object()
    await reply(rt.loop,must_keep=['Keep confession private'])
    await reply(rt.loop,candidates=[dict(candidate_id=cid,label=label,story_cost='Same plan, different label',
        manifest=manifest(location='stairwell',revision=2)) for cid,label in [('a','First sketch'),('b','Second sketch')]])
    effects=[e for e in rt.ledger.pending_effects() if e['kind']=='preview']
    assert len(effects)==2
    first,second=rt.loop.workflow['candidates']
    await rt.loop.preview_result('a',first['manifest_hash'],'/media/a.mp4','ready')
    assert rt.loop.workflow['question'] is None
    await rt.loop.preview_result('b',second['manifest_hash'],'/media/b.mp4','ready')
    assert rt.loop.workflow['question'] is not None
    await rt.close()
