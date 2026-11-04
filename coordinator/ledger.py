"""SQLite authority: state and effects commit together before remote acknowledgments."""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo


TABLES = ('changes', 'jobs', 'questions', 'renders', 'releases', 'publications', 'acks')


def now_iso() -> str:
    return datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()


def encode(value: Any) -> str:
    result = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(result.encode()) > 1048576:
        raise ValueError('Ledger payload exceeds 1 MiB.')
    return result


class Ledger:
    def __init__(self, path: str | Path, *, initial_state: dict | None = None) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA synchronous=FULL')
        self.connection.execute('PRAGMA busy_timeout=5000')
        self._subscribers: list[Callable] = []
        self._in_transaction = False
        self._processing: ContextVar[tuple[str, dict, dict] | None] = ContextVar('processing_event', default=None)
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS inbox (
              source_id TEXT PRIMARY KEY, position TEXT NOT NULL, payload TEXT NOT NULL, at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outcomes (
              session_id TEXT, request_id TEXT, payload TEXT NOT NULL, at TEXT NOT NULL,
              PRIMARY KEY(session_id,request_id));
            CREATE TABLE IF NOT EXISTS outbox (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
              key TEXT UNIQUE NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0, error TEXT, at TEXT NOT NULL);
        ''')
        for table in TABLES:
            self.connection.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, revision INTEGER NOT NULL)''')
        with self.transaction():
            self.connection.execute("UPDATE outbox SET status='uncertain' WHERE status='sending'")
            if initial_state is not None and self.get_meta('state') is None:
                self.save_state(initial_state)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        if self._in_transaction:
            raise RuntimeError('Nested ledger transaction is not supported.')
        self.connection.execute('BEGIN IMMEDIATE')
        self._in_transaction = True
        try:
            yield self.connection
            event = self._processing.get()
            if event is not None:
                self.record_event(*event)
            self.connection.execute('COMMIT')
        except BaseException:
            self.connection.execute('ROLLBACK')
            raise
        finally:
            self._in_transaction = False
        for callback in tuple(self._subscribers):
            try:
                callback()
            except Exception as error:
                # The data already committed. Report observer failure without disguising success.
                self._subscribers.remove(callback)
                self.connection.execute('BEGIN IMMEDIATE')
                self._in_transaction = True
                try:
                    self.set_meta('observer_failure', type(error).__name__)
                    self.timeline('error', 'A state observer failed; reconnect the Control Room.')
                    self.connection.execute('COMMIT')
                except BaseException:
                    self.connection.execute('ROLLBACK')
                    raise
                finally:
                    self._in_transaction = False

    @contextmanager
    def processing_event(self, source_id: str, position: dict, payload: dict) -> Iterator[None]:
        """Attach inbox progress to the handler's own atomic state/effect transaction."""
        token = self._processing.set((source_id, position, payload))
        try:
            yield
        finally:
            self._processing.reset(token)

    def has_event(self, source_id: str) -> bool:
        return self.connection.execute('SELECT 1 FROM inbox WHERE source_id=?', (source_id,)).fetchone() is not None

    def _require_transaction(self) -> None:
        if not self._in_transaction:
            raise RuntimeError('Ledger mutations require an explicit transaction.')

    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self.connection.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row['value']) if row else deepcopy(default)

    def set_meta(self, key: str, value: Any) -> None:
        self._require_transaction()
        self.connection.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                                (key, encode(value)))

    def snapshot_state(self) -> dict:
        state = self.get_meta('state')
        if state is None:
            raise RuntimeError('Ledger has no initialized production state.')
        state['production']['now'] = now_iso()
        return state

    def save_state(self, state: dict) -> None:
        self._require_transaction()
        from coordinator.ui_models import State
        clean = State.model_validate(state).model_dump(mode='json', exclude_none=True)
        clean['timeline'] = clean['timeline'][:200]
        self.set_meta('state', clean)
        revision = clean['revisions']['constraints']
        mappings = {'changes': ('id', clean['changes']), 'jobs': ('job_id', clean['jobs']),
                    'releases': ('release_id', clean['releases'])}
        for table, (key, rows) in mappings.items():
            for row in rows:
                self.put(table, row[key], row, row.get('status', 'recorded'), revision)
        for release in clean['releases']:
            release_id = release['release_id']
            for publication in release['publications']:
                self.put('publications', release_id + ':' + publication['room'],
                    dict(release_id=release_id, **publication), publication['status'], revision)
            confirmed = {item['person']: item['at'] for item in release['acks']['confirmed']}
            for person in release['acks']['expected']:
                self.put('acks', release_id + ':' + person,
                    dict(release_id=release_id, person=person, at=confirmed.get(person), policy=release['acks']['policy']),
                    'confirmed' if person in confirmed else 'pending', revision)

    def put(self, table: str, item_id: str, payload: dict, status: str, revision: int) -> None:
        self._require_transaction()
        if table not in TABLES:
            raise ValueError('Unknown ledger table.')
        self.connection.execute(f'''INSERT INTO {table} VALUES (?,?,?,?) ON CONFLICT(id)
            DO UPDATE SET payload=excluded.payload,status=excluded.status,revision=excluded.revision''',
            (item_id, encode(payload), status, revision))

    def record_event(self, source_id: str, position: dict, payload: dict) -> bool:
        self._require_transaction()
        cursor = self.connection.execute('INSERT OR IGNORE INTO inbox VALUES (?,?,?,?)',
                                         (source_id, encode(position), encode(payload), now_iso()))
        if cursor.rowcount:
            merged = self.get_meta('event_position', {})
            for source, seq in position.items():
                merged[source] = max(merged.get(source, 0), seq)
            self.set_meta('event_position', merged)
        return bool(cursor.rowcount)

    def record_outcome(self, session_id: str, request_id: str, payload: dict) -> bool:
        self._require_transaction()
        cursor = self.connection.execute('INSERT OR IGNORE INTO outcomes VALUES (?,?,?,?)',
                                         (session_id, request_id, encode(payload), now_iso()))
        return bool(cursor.rowcount)

    def timeline(self, kind: str, text: str, ref: str | None = None) -> None:
        self._require_transaction()
        state = self.get_meta('state')
        if state is None:
            return
        item = {'at': now_iso(), 'kind': kind, 'text': text[:512]}
        if ref:
            item['ref'] = ref
        state['timeline'] = [item, *state['timeline']][:200]
        self.save_state(state)

    def enqueue(self, kind: str, payload: dict, key: str, revision: int) -> str:
        self._require_transaction()
        existing = self.connection.execute('SELECT id FROM outbox WHERE key=?', (key,)).fetchone()
        if existing:
            return existing['id']
        if self.connection.execute("SELECT count(*) FROM outbox WHERE status IN ('pending','sending','uncertain')").fetchone()[0] >= 1000:
            raise ValueError('Outbox capacity reached; resolve pending failures before continuing.')
        effect_id = str(uuid4())
        self.connection.execute('INSERT OR IGNORE INTO outbox VALUES (?,?,?,?,?,?,0,NULL,?)',
                                (effect_id, kind, encode(payload), key, revision, 'pending', now_iso()))
        return self.connection.execute('SELECT id FROM outbox WHERE key=?', (key,)).fetchone()['id']

    def effects(self, status: str) -> list[dict]:
        result = []
        for row in self.connection.execute('SELECT * FROM outbox WHERE status=? ORDER BY at,id LIMIT 1000', (status,)):
            item = dict(row)
            item['payload'] = json.loads(item['payload'])
            result.append(item)
        return result

    def pending_effects(self) -> list[dict]:
        return self.effects('pending')

    def effect(self, effect_id: str) -> dict | None:
        row = self.connection.execute('SELECT * FROM outbox WHERE id=?', (effect_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item['payload'] = json.loads(item['payload'])
        return item

    def effect_status(self, effect_id: str, status: str, *, error: str | None = None) -> None:
        if status not in ('pending', 'sending', 'sent', 'uncertain', 'failed', 'cancelled'):
            raise ValueError('Invalid publication status.')
        def update() -> None:
            self.connection.execute('UPDATE outbox SET status=?,error=?,attempts=attempts+? WHERE id=?',
                                    (status, error[:500] if error else None, int(status == 'sending'), effect_id))
        if self._in_transaction:
            update()
        else:
            with self.transaction():
                update()

    def subscribe(self, callback: Callable) -> Callable[[], None]:
        self._subscribers.append(callback)
        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        return unsubscribe

    def close(self) -> None:
        self.connection.close()
