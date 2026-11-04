"""Read-only source audit and credential-free W4 report replay extraction."""
from pathlib import Path
import difflib
import json
import sqlite3
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    best: list[dict[str, Any]] = []
    source = ''
    for path in (ROOT / 'data/backups').glob('*.sqlite'):
        with sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True) as connection:
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone():
                continue
            row = connection.execute("SELECT value FROM meta WHERE key='state'").fetchone()
        if row:
            state = json.loads(row[0])
            reports = [c for c in state['changes'] if c['field'] == 'report']
            if len(reports) > len(best):
                best, source = reports, path.name
    if best:
        fixture = dict(source=f'W4 ledger backup {source}; exact persisted report values', messages=[
            dict(sender='maya' if c['value'] == 'Sorry, I have to leave at 6.' else
                 'director' if c['value'].startswith('A') and 'q1=' in c['value'] else
                 '@switch-agent-self:localhost', body=c['value']) for c in reversed(best)])
        (ROOT / 'fixtures/w5-room-chatter.json').write_text(json.dumps(fixture, ensure_ascii=False, indent=2),
            encoding='utf-8', newline='\n')
        print('W4 replay report rows:', len(best))
    baseline = ROOT / 'data/w5-baseline'
    diffs: list[str] = []
    changed: list[str] = []
    paths = [*ROOT.glob('coordinator/**/*.py'), *ROOT.glob('scripts/**/*.py'),
             ROOT / 'pyproject.toml', ROOT / 'docs/UI-CONTRACT.md']
    for path in paths:
        relative = path.relative_to(ROOT)
        old = baseline / relative
        before = old.read_text(encoding='utf-8') if old.exists() else ''
        after = path.read_text(encoding='utf-8')
        if before != after:
            changed.append(str(relative))
            assert len(after.splitlines()) < 500, relative
            assert b'\r' not in path.read_bytes(), relative
            diffs.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                fromfile='before/' + relative.as_posix(), tofile='after/' + relative.as_posix()))
    (ROOT / 'data/w5-diff.txt').write_text(''.join(diffs), encoding='utf-8', newline='\n')
    print('Changed files:', ', '.join(changed))


if __name__ == '__main__':
    main()
