"""External effects use the real durable ledger and an in-memory Switch transport."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from coordinator.dispatcher import Dispatcher
from coordinator.ledger import Ledger
from coordinator.switch_client import SwitchClient


class Production:
    def __init__(self):
        self.current = True
        self.results = []
        self.previews = []

    def effect_current(self, effect):
        return self.current

    async def publication_result(self, release_id, room, status):
        self.results.append((release_id, room, status))

    async def preview_result(self, candidate_id, manifest_hash, url, status):
        self.previews.append((candidate_id, manifest_hash, url, status))


class Renderer:
    def __init__(self, root, *, placeholder=False, callback=None):
        self.artifacts_dir = root
        self.placeholder = placeholder
        self.callback = callback

    async def render(self, kind, manifest):
        self.last_manifest = manifest
        if self.callback:
            self.callback()
        path = self.artifacts_dir / ('call.placeholder.txt' if self.placeholder else 'call.png')
        path.write_bytes(b'placeholder' if self.placeholder else b'\x89PNG\r\n\x1a\nimage')
        return SimpleNamespace(path=path, placeholder=self.placeholder, manifest_hash='sha256:approved')


async def setup(tmp_path, handler, **kwargs):
    identity = tmp_path / 'identity.json'
    identity.write_text(json.dumps(dict(agent_id='coordinator', api_key='secret',
        connection_id='connection', session_id='session', position={}, cursor=0)))
    client = SwitchClient('http://switch.test', identity,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        production_room_id='production')
    await client.initialize()
    initial = json.loads((Path(__file__).resolve().parents[2] / 'fixtures/ui-state/01-normal.json').read_text(encoding='utf-8'))
    ledger = Ledger(tmp_path / 'ledger.sqlite', initial_state=initial)
    production = Production()
    renderer = Renderer(tmp_path, **kwargs)
    dispatcher = Dispatcher(ledger, production, client, production_room_id='production',
        crew_room_ids=['crew'], renderer=renderer, retry_delay=0)
    return ledger, production, client, dispatcher


def queue(ledger, kind, payload):
    with ledger.transaction():
        return ledger.enqueue(kind, payload, 'test:' + kind, 2)


@pytest.mark.asyncio
async def test_claim_is_durable_before_message_and_timeout_is_never_replayed(tmp_path):
    calls = []
    ledger = None
    def handler(request):
        calls.append(request)
        assert ledger.effects('sending')
        raise httpx.ReadTimeout('delivery unknown', request=request)
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'hold', dict(body='Scene 3 ON HOLD', scene_ids=['s3']))
    await dispatcher.run_once()
    assert len([request for request in calls if json.loads(request.content)['room_id'] == 'crew']) == 1
    assert len([effect for effect in ledger.effects('uncertain') if effect['kind'] == 'hold_message']) == 1
    await dispatcher.run_once()
    assert len(calls) == 2  # One hold and one production failure notice, neither replayed.
    await client.aclose()


@pytest.mark.asyncio
async def test_stale_effect_never_reaches_switch(tmp_path):
    calls = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: calls.append(request) or httpx.Response(200, json={'ok': True}))
    queue(ledger, 'role_message', dict(role='first-ad', body='old job', expected_holder='ad', job_id='j1'))
    production.current = False
    await dispatcher.run_once()
    assert calls == []
    assert len(ledger.effects('cancelled')) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_render_completion_rechecks_revision_before_any_publication(tmp_path):
    calls = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: calls.append(request) or httpx.Response(200, json={'ok': True}))
    dispatcher.renderer.callback = lambda: setattr(production, 'current', False)
    queue(ledger, 'release', dict(release_id='r2', manifest={'scenes': []},
        manifest_hash='sha256:approved', summary='Current plan', preview_url=None))
    await dispatcher.run_once()
    assert calls == []
    assert len(ledger.effects('cancelled')) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_placeholder_is_visible_text_fallback_and_never_uploaded(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200, json={'ok': True, 'event_id': 'm1'}), placeholder=True)
    queue(ledger, 'release', dict(release_id='r2', manifest={'scenes': []},
        manifest_hash='sha256:approved', summary='New plan', preview_url=None))
    for _ in range(3):
        await dispatcher.run_once()
    assert not any(request.url.path.endswith('/media') for request in requests)
    bodies = [json.loads(request.content).get('content', '') for request in requests]
    assert any('r2' in body and 'call sheet' in body.lower() and 'unavailable' in body.lower() for body in bodies)
    assert any('call sheet unavailable' in item['text'] for item in ledger.snapshot_state()['timeline'])
    assert ('r2', 'crew', 'sent') in production.results
    await client.aclose()


@pytest.mark.asyncio
async def test_release_uploads_call_sheet_before_text_with_durable_file_checkpoint(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('/message'):
            raise httpx.ReadTimeout('text unknown', request=request)
        return httpx.Response(200, json={'ok': True})
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'release', dict(release_id='r2', manifest={'scenes': []},
        manifest_hash='sha256:approved', summary='New plan', preview_url=None))
    for _ in range(4):
        await dispatcher.run_once()
    assert [request.url.path.rsplit('/', 1)[-1] for request in requests] == ['media', 'message', 'message']
    assert json.loads(requests[1].content)['room_id'] == 'crew'
    assert json.loads(requests[2].content)['room_id'] == 'production'
    assert ledger.effects('uncertain')
    assert ('r2', 'crew', 'uncertain') in production.results
    await client.aclose()


@pytest.mark.asyncio
async def test_exact_question_retry_is_bounded_and_identical(tmp_path):
    payloads = []
    def handler(request):
        if request.url.path.endswith('/approvals'):
            payloads.append(request.content)
            raise httpx.ReadTimeout('question response unknown', request=request)
        return httpx.Response(200, json={'ok': True, 'event_id': 'notice'})
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    from datetime import datetime
    from coordinator.switch_models import QuestionOption
    payload = client.question_payload('Pick', 'Which?', [QuestionOption(id='a', label='A')],
        datetime.fromisoformat('2026-11-06T18:00:00+05:30'), request_id='q1').model_dump(mode='json')
    queue(ledger, 'open_question', {'payload': payload})
    await dispatcher.run_once()
    await dispatcher.run_once()
    assert len(payloads) == 2
    assert payloads[0] == payloads[1]
    assert json.loads(payloads[0]) == payload
    assert next(effect for effect in ledger.effects('uncertain') if effect['kind'] == 'open_question')['attempts'] == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_restart_does_not_resend_uncertain_media_and_reports_room(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200, json={'ok': True}))
    path = tmp_path / 'call.png'
    path.write_bytes(b'\x89PNG\r\n\x1a\nimage')
    effect_id = queue(ledger, 'publication_media', dict(release_id='r2', room_id='crew',
        path=str(path), media_kind='callsheet'))
    ledger.effect_status(effect_id, 'sending')
    ledger.close()
    dispatcher.ledger = Ledger(tmp_path / 'ledger.sqlite')
    await dispatcher.run_once()
    assert all(request.url.path.endswith('/message') and json.loads(request.content)['room_id'] == 'production' for request in requests)
    assert ('r2', 'crew', 'uncertain') in production.results
    await client.aclose()


@pytest.mark.asyncio
async def test_restart_can_retry_local_render_without_replaying_external_posts(tmp_path):
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: httpx.Response(200, json={'ok': True, 'event_id': 'm1'}), placeholder=True)
    effect_id = queue(ledger, 'release', dict(release_id='r2', manifest={'scene_id': 's3'},
        snapshot={'scenes': [{'scene_id': 's1', 'location': 'street'}]},
        manifest_hash='sha256:approved', summary='New plan', preview_url=None))
    ledger.effect_status(effect_id, 'sending')
    ledger.close()
    dispatcher.ledger = Ledger(tmp_path / 'ledger.sqlite')
    await dispatcher.run_once()
    assert dispatcher.renderer.last_manifest == {'scenes': [{'scene_id': 's1', 'location': 'street'}]}
    assert ('r2', 'crew', 'sent') in production.results
    await client.aclose()


@pytest.mark.asyncio
async def test_preview_placeholder_completes_as_visible_failure(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200), placeholder=True)
    queue(ledger, 'preview', dict(candidate_id='stairs', manifest={}, manifest_hash='sha256:approved'))
    await dispatcher.run_once()
    assert len(requests) == 1
    assert json.loads(requests[0].content)['room_id'] == 'production'
    assert production.previews == [('stairs', 'sha256:approved', None, 'failed')]
    await client.aclose()


@pytest.mark.asyncio
async def test_new_revision_cancels_slow_render_so_holds_are_not_delayed(tmp_path):
    ledger, production, client, dispatcher = await setup(tmp_path, lambda request: httpx.Response(200))
    started, cancelled = asyncio.Event(), asyncio.Event()
    async def slow_render(kind, manifest):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    dispatcher.renderer.render = slow_render
    queue(ledger, 'preview', dict(candidate_id='stairs', manifest={}, manifest_hash='sha256:approved'))
    task = asyncio.create_task(dispatcher.run_once())
    await started.wait()
    production.current = False
    try:
        await asyncio.wait_for(task, timeout=1)
    except TimeoutError:
        pytest.fail('a stale render delayed pending hold dispatch')
    assert cancelled.is_set()
    assert ledger.effects('cancelled')
    await client.aclose()


@pytest.mark.asyncio
async def test_stale_dependent_publication_is_cancelled_even_when_parent_uncertain(tmp_path):
    ledger, production, client, dispatcher = await setup(tmp_path, lambda request: httpx.Response(200))
    parent = queue(ledger, 'publication_media', dict(release_id='r2', room_id='crew', path='unused', media_kind='callsheet'))
    ledger.effect_status(parent, 'uncertain')
    queue(ledger, 'publication_text', dict(release_id='r2', room_id='crew', body='old', depends_on=parent))
    production.current = False
    await dispatcher.run_once()
    assert ledger.pending_effects() == []
    assert ledger.effects('cancelled')
    await client.aclose()


@pytest.mark.asyncio
async def test_traversal_preview_is_reported_and_external_file_is_never_uploaded(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200, json={'ok': True, 'event_id': 'm1'}))
    dispatcher.renderer.artifacts_dir = tmp_path / 'out'
    dispatcher.renderer.artifacts_dir.mkdir()
    (tmp_path / 'outside.mp4').write_bytes(b'\x00\x00\x00\x18ftypisomoutside-private-bytes')
    queue(ledger, 'release', dict(release_id='r2', manifest={'scenes': []},
        manifest_hash='sha256:approved', summary='New plan', preview_url='/media/../outside.mp4'))
    await dispatcher.run_once()
    assert len([request for request in requests if request.url.path.endswith('/media')]) == 1
    assert all(b'outside-private-bytes' not in request.content for request in requests)
    assert any('preview file is unavailable' in item['text'] for item in ledger.snapshot_state()['timeline'])
    await client.aclose()


@pytest.mark.asyncio
async def test_dependency_lookup_is_not_limited_to_first_thousand_sent_effects(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200, json={'ok': True, 'event_id': 'm1'}))
    with ledger.transaction():
        for index in range(1000):
            parent = ledger.enqueue('publication_media', {}, f'old:{index}', 2)
            ledger.effect_status(parent, 'sent')
    await asyncio.sleep(0.05)  # Later than Windows' clock resolution, independent of UUID sort order.
    with ledger.transaction():
        parent = ledger.enqueue('publication_media', {}, 'latest-media', 2)
        ledger.effect_status(parent, 'sent')
    queue(ledger, 'publication_text', dict(release_id='r2', room_id='crew', body='new', depends_on=parent))
    await dispatcher.run_once()
    assert len(requests) == 1
    assert ledger.pending_effects() == []
    await client.aclose()


@pytest.mark.asyncio
async def test_change_during_send_records_uncertainty_and_unblocks_holds_promptly(tmp_path):
    started = asyncio.Event()
    async def handler(request):
        started.set()
        await asyncio.Event().wait()
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'publication_text', dict(release_id='r2', room_id='crew', body='plan'))
    task = asyncio.create_task(dispatcher.run_once())
    await started.wait()
    production.current = False
    try:
        await asyncio.wait_for(task, timeout=1)
    except TimeoutError:
        pytest.fail('in-flight publication blocked the newer hold')
    assert ledger.effects('uncertain')
    assert ('r2', 'crew', 'uncertain') in production.results
    await client.aclose()


@pytest.mark.asyncio
async def test_disabled_dispatch_keeps_effect_pending_until_stream_reconciles(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200, json={'ok': True, 'event_id': 'm1'}))
    dispatcher.enabled = lambda: False
    queue(ledger, 'hold', dict(body='Hold', scene_ids=['s3']))
    assert await dispatcher.run_once() == 0
    assert requests == []
    assert len(ledger.pending_effects()) == 1
    dispatcher.enabled = lambda: True
    await dispatcher.run_once()
    assert len(requests) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_document_create_timeout_reconciles_owned_document_instead_of_duplicate(tmp_path):
    operations, documents = [], []
    def handler(request):
        operation = request.url.path.rsplit('/', 1)[-1]
        operations.append(operation)
        if operation == 'list_references':
            result = {'documents': documents}
        elif operation == 'create_room_document':
            documents.append(dict(id='doc1', name='constraints-r2', scope='room', created_by_agent_id='coordinator'))
            raise httpx.ReadTimeout('create response unknown', request=request)
        elif operation == 'update_room_document':
            assert json.loads(request.content)['document_id'] == 'doc1'
            result = {'document_id': 'doc1'}
        else:
            pytest.fail('Unexpected operation ' + operation)
        return httpx.Response(200, json={'result': result})
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'document', dict(name='constraints-r2', content='confirmed facts'))
    await dispatcher.run_once()
    assert operations == ['list_references', 'create_room_document', 'list_references', 'update_room_document']
    assert ledger.get_meta('doc:constraints-r2') == 'doc1'
    assert len(ledger.effects('sent')) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_gap_during_role_presence_check_preserves_job_without_sending(tmp_path):
    operations = []
    def handler(request):
        operation = request.url.path.rsplit('/', 1)[-1]
        operations.append(operation)
        dispatcher.enabled = lambda: False
        return httpx.Response(200, json={'result': [dict(name='first-ad', exclusive=True,
            held_by=[dict(name='ad', present_here=True)])]})
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'role_message', dict(role='first-ad', body='job', job_id='j1', expected_holder='ad'))
    await dispatcher.run_once()
    assert operations == ['list_roles']
    assert len(ledger.pending_effects()) == 1
    assert not ledger.effects('cancelled')
    await client.aclose()


@pytest.mark.asyncio
async def test_hold_precedes_older_nonurgent_document_work(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        result = {'documents': []} if request.url.path.endswith('list_references') else {'document_id': 'd1'}
        return httpx.Response(200, json={'ok': True, 'event_id': 'm1', 'result': result})
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'document', dict(name='facts', content='facts'))
    await asyncio.sleep(0.05)
    queue(ledger, 'hold', dict(body='Hold now', scene_ids=['s3']))
    await dispatcher.run_once(limit=2)
    assert requests[0].url.path.endswith('/message')
    await client.aclose()


@pytest.mark.asyncio
async def test_publication_receipt_is_saved_for_explicit_old_thread_corrections(tmp_path):
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: httpx.Response(200, json={'ok': True, 'event_id': 'release-message'}))
    queue(ledger, 'publication_text', dict(release_id='r2', room_id='crew', body='Plan'))
    await dispatcher.run_once()
    assert ledger.get_meta('publication_message:release-message') == 'r2'
    assert len(ledger.effects('sent')) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_failure_is_visible_in_production_and_notice_failure_does_not_recurse(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout('notice transport down', request=request)
    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    queue(ledger, 'unsupported', {})
    await dispatcher.run_once()
    assert len(requests) == 1
    assert json.loads(requests[0].content)['room_id'] == 'production'
    assert 'failed' in json.loads(requests[0].content)['content']
    assert ledger.pending_effects() == []
    await client.aclose()


@pytest.mark.asyncio
async def test_restart_finishes_local_publication_callback_without_resending_text(tmp_path):
    requests = []
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: requests.append(request) or httpx.Response(200, json={'ok': True, 'event_id': 'release-post'}))
    async def crash_callback(*args):
        raise RuntimeError('process stopped after sent checkpoint')
    original = production.publication_result
    production.publication_result = crash_callback
    queue(ledger, 'publication_text', dict(release_id='r2', room_id='crew', body='Plan'))
    with pytest.raises(RuntimeError):
        await dispatcher.run_once()
    assert len(ledger.effects('sent')) == 1
    production.publication_result = original
    restarted = Dispatcher(ledger, production, client, production_room_id='production',
        crew_room_ids=['crew'], renderer=dispatcher.renderer)
    await restarted.run_once()
    assert len(requests) == 1
    assert ('r2', 'crew', 'sent') in production.results
    await client.aclose()


@pytest.mark.asyncio
async def test_release_without_destinations_fails_visibly_instead_of_marking_sent(tmp_path):
    ledger, production, client, dispatcher = await setup(tmp_path,
        lambda request: httpx.Response(200, json={'ok': True, 'event_id': 'notice'}))
    dispatcher.crew_room_ids = []
    queue(ledger, 'release', dict(release_id='r2', manifest={}, destinations=[], summary='Plan'))
    await dispatcher.run_once()
    assert any(effect['kind'] == 'release' for effect in ledger.effects('failed'))
    assert not any(effect['kind'] == 'release' for effect in ledger.effects('sent'))
    assert any('no crew destinations' in item['text'].lower() for item in ledger.snapshot_state()['timeline'])
    await client.aclose()


def test_text_snapshot_includes_held_scene_without_stale_location_instructions():
    text = Dispatcher._release_text(dict(release_id='r2', summary='Stairwell plan', snapshot=dict(scenes=[
        dict(scene_id='s1', validity='held', hold_reason='Permission refused', location='rooftop'),
        dict(scene_id='s3', location='stairwell', start='16:00', end='17:00', people=['maya'])])))
    assert 's1: ON HOLD' in text and 'Permission refused' in text
    assert 'rooftop' not in text
    assert 's3: stairwell' in text
