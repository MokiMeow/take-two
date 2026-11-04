"""Persistence properties rather than SQLite implementation details."""
import pytest

from coordinator.ledger import Ledger


def test_rollback_keeps_revision_and_effect_together(tmp_path):
    db = Ledger(tmp_path / 'ledger.sqlite')
    with pytest.raises(RuntimeError):
        with db.transaction():
            db.set_meta('revision', 2)
            db.enqueue('message', {'body': 'hold'}, 'hold:2', 2)
            raise RuntimeError('crash before commit')
    assert db.get_meta('revision') is None
    assert db.pending_effects() == []


def test_outcome_duplicate_survives_restart(tmp_path):
    path = tmp_path / 'ledger.sqlite'
    db = Ledger(path)
    with db.transaction():
        assert db.record_outcome('session', 'request', {'answer': 'A'})
    db.close()
    db = Ledger(path)
    with db.transaction():
        assert not db.record_outcome('session', 'request', {'answer': 'A'})


def test_inbox_deduplication_and_position_atomic(tmp_path):
    db = Ledger(tmp_path / 'ledger.sqlite')
    with db.transaction():
        assert db.record_event('event-1', {'room': 3}, {'event': 'message'})
        assert not db.record_event('event-1', {'room': 3}, {'event': 'message'})
    assert db.get_meta('event_position') == {'room': 3}


def test_subscribers_only_see_committed_state(tmp_path):
    db = Ledger(tmp_path / 'ledger.sqlite')
    seen = []
    db.subscribe(lambda: seen.append(db.get_meta('revision')))
    with db.transaction():
        db.set_meta('revision', 3)
        assert seen == []
    assert seen == [3]
    with pytest.raises(ValueError):
        with db.transaction():
            db.set_meta('revision', 4)
            raise ValueError('rollback')
    assert seen == [3]


def test_outbox_unique_key_and_inflight_recovery(tmp_path):
    path = tmp_path / 'ledger.sqlite'
    db = Ledger(path)
    with db.transaction():
        one = db.enqueue('message', {'body': 'r2'}, 'r2:crew', 2)
        two = db.enqueue('message', {'body': 'r2'}, 'r2:crew', 2)
    assert one == two
    db.effect_status(one, 'sending')
    db.close()
    db = Ledger(path)
    assert db.pending_effects() == []
    assert db.effects('uncertain')[0]['id'] == one


def test_mutation_requires_transaction(tmp_path):
    db = Ledger(tmp_path / 'ledger.sqlite')
    with pytest.raises(RuntimeError):
        db.set_meta('revision', 2)


def test_sparse_positions_merge_and_never_regress(tmp_path):
    db = Ledger(tmp_path/'ledger.sqlite')
    with db.transaction():
        db.record_event('1', {'s': 8}, {})
        db.record_event('2', {'r:crew': 12}, {})
        db.record_event('3', {'s': 7}, {})
    assert db.get_meta('event_position') == {'s': 8, 'r:crew': 12}


def test_existing_effect_can_be_retried_at_capacity(tmp_path):
    db = Ledger(tmp_path/'ledger.sqlite')
    with db.transaction():
        first = db.enqueue('message', {'body': 'a'}, 'first', 1)
        for i in range(999):
            db.enqueue('message', {'body': 'a'}, str(i), 1)
        assert db.enqueue('message', {'body': 'a'}, 'first', 1) == first


def test_failing_observer_does_not_disguise_successful_commit(tmp_path):
    db = Ledger(tmp_path/'ledger.sqlite')
    def fail():
        raise RuntimeError('observer failed')
    db.subscribe(fail)
    with db.transaction():
        db.set_meta('committed', True)
    assert db.get_meta('committed') is True
    assert db.get_meta('observer_failure') == 'RuntimeError'


def test_processing_marker_commits_with_effect_or_rolls_back(tmp_path):
    db = Ledger(tmp_path/'ledger.sqlite')
    with db.processing_event('m1', {'s': 9}, {'body': 'change'}):
        with pytest.raises(RuntimeError):
            with db.transaction():
                db.enqueue('message', {}, 'no', 1)
                raise RuntimeError('crash')
        assert not db.has_event('m1')
        with db.transaction():
            db.enqueue('message', {}, 'yes', 1)
    assert db.has_event('m1')
    assert db.get_meta('event_position') == {'s': 9}


def test_release_publications_and_acks_have_durable_table_rows(tmp_path):
    import json
    from pathlib import Path
    fixture = Path(__file__).resolve().parents[2]/'fixtures/ui-state/05-released.json'
    db = Ledger(tmp_path/'ledger.sqlite')
    with db.transaction():
        db.save_state(json.loads(fixture.read_text()))
    assert db.connection.execute('SELECT count(*) FROM publications').fetchone()[0] > 0
    assert db.connection.execute('SELECT count(*) FROM acks').fetchone()[0] > 0
