"""Native crew cards are personal, durable and never implicit decisions."""
from datetime import datetime, timedelta
from pathlib import Path

from coordinator.tests.test_w4_workflow import runtime, initial
from coordinator.tests.test_w8_duties import release_stairs


def card(rt: object, person: str = 'maya') -> dict:
    return next(q for q in rt.loop.workflow.get('cards', {}).values()
        if q['kind'] == 'duty' and q['person'] == person and q['status'] == 'open')


def outcome(q: dict, person: str = 'maya', choice: str = 'confirm', **kw: object) -> dict:
    return dict(session_id=q['session_id'], request_id=q['request_id'],
        answered_by=person, candidate_id=choice, **kw)


async def test_personal_confirm_and_duplicate_after_restart(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    q = card(rt)
    assert q['release_id'] == 'r1' and q['constraints_rev'] == 1
    assert [o['label'] for o in q['payload']['questions'][0]['options']] == ['Confirm', "Can't make it"]
    assert await rt.loop.handle_outcome(outcome(q))
    await rt.close()
    rt = runtime(tmp_path)
    assert not await rt.loop.handle_outcome(outcome(q))
    assert rt.ledger.snapshot_state()['releases'][0]['acks']['confirmed'] == [dict(person='maya', at=rt.ledger.snapshot_state()['releases'][0]['acks']['confirmed'][0]['at'])]
    assert not any(c['person'] == 'maya' and c['status'] == 'open' for c in rt.loop.workflow['cards'].values())
    await rt.close()


async def test_wrong_person_replaced_only_once_with_same_expiry(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    q = card(rt)
    assert not await rt.loop.handle_outcome(outcome(q, 'dev'))
    replacement = card(rt)
    assert replacement['request_id'] != q['request_id']
    assert replacement['expires_at'] == q['expires_at']
    assert not await rt.loop.handle_outcome(outcome(replacement, 'leela'))
    assert not any(c['person'] == 'maya' and c['status'] == 'open' for c in rt.loop.workflow['cards'].values())
    assert not rt.ledger.snapshot_state()['releases'][0]['acks']['confirmed']
    await rt.close()


async def test_cannot_make_it_note_is_pending_and_never_changes_facts(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    before = rt.loop.constraints.model_dump()
    assert await rt.loop.handle_outcome(outcome(card(rt), choice='cannot', note='Running 20 min late'))
    state = rt.ledger.snapshot_state()
    assert state['changes'][0]['status'] == 'pending_confirmation'
    assert state['changes'][0]['reporter'] == 'maya'
    assert state['changes'][0]['value'] == 'Running 20 min late'
    assert not state['releases'][0]['acks']['confirmed']
    assert rt.loop.constraints.model_dump() == before
    await rt.close()


async def test_superseded_cards_and_revision_stale_answers_do_nothing(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    old = card(rt)
    await release_stairs(rt)
    assert old['request_id'] != card(rt)['request_id']
    assert rt.loop.workflow['cards'][old['request_id']]['status'] == 'closed_outdated'
    assert not await rt.loop.handle_outcome(outcome(old))
    assert not rt.ledger.snapshot_state()['releases'][0]['acks']['confirmed']
    await rt.close()


async def test_expiry_never_confirms_and_text_fallback_closes_card(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    q = card(rt)
    rt.loop.clock = lambda: datetime.fromisoformat(q['expires_at']) + timedelta(seconds=1)
    await rt.loop.tick()
    assert not await rt.loop.handle_outcome(outcome(q, state='expired'))
    assert not rt.ledger.snapshot_state()['releases'][0]['acks']['confirmed']
    assert await rt.loop.confirm('dev', 'r1')
    assert not any(c['person'] == 'dev' and c['status'] == 'open' for c in rt.loop.workflow['cards'].values())
    await rt.close()


async def test_uncertain_card_open_retries_exact_request_after_restart(tmp_path: Path) -> None:
    from coordinator.tests.test_dispatcher import setup
    import httpx
    opened = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        if request.url.path.endswith('/approvals'):
            opened.append(json.loads(request.content))
        return httpx.Response(200, json=dict(session_id='session', request_id='personal', kind='questions', state='open'))

    ledger, production, client, dispatcher = await setup(tmp_path, handler)
    payload = dict(request_id='personal', turn_id='turn', kind='questions', title='Maya', room_id='production',
        questions=[dict(id='choice', title='Maya', prompt='Confirm your duties', options=[dict(id='confirm', label='Confirm')])],
        expires_at='2026-11-06T20:00:00+05:30')
    with ledger.transaction():
        effect = ledger.enqueue('open_question', dict(payload=payload), 'question:personal', 1)
    ledger.effect_status(effect, 'sending')
    ledger.effect_status(effect, 'uncertain')
    await dispatcher.run_once()
    assert len(opened) == 1
    assert opened[0]['request_id'] == 'personal'
    assert ledger.effect(effect)['status'] == 'sent'
    await client.aclose()
    ledger.close()


async def test_cannot_make_it_with_whitespace_note_remains_a_valid_pending_report(tmp_path: Path) -> None:
    rt = runtime(tmp_path)
    await initial(rt.loop)
    assert await rt.loop.handle_outcome(outcome(card(rt), choice='cannot', note='   '))
    assert rt.ledger.snapshot_state()['changes'][0]['value'] == "Can't make it"
    await rt.close()
