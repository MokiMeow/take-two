"""Back up and reset an OFFLINE local ledger; identities and rooms are untouched."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def reset_ledger(path: Path, backup_dir: Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[1]/'data'
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Reset ledger must be inside the project data directory')
    path.parent.mkdir(parents=True,exist_ok=True)
    backups = (backup_dir or root/'backups').resolve()
    if not backups.is_relative_to(root.resolve()):
        raise ValueError('Backups must stay inside data')
    backups.mkdir(parents=True,exist_ok=True)
    backup = backups/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite')
    with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
        names = [row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        allowed = {'meta','inbox','outcomes','outbox','changes','jobs','questions','renders','releases','publications','acks'}
        if set(names)-allowed:
            raise ValueError('Unknown tables; refusing to reset a different application database')
        source.execute('BEGIN EXCLUSIVE')
        for name in names:
            source.execute(f'DELETE FROM "{name}"')
        source.commit()
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=Path('data/ledger.sqlite'))
    args = parser.parse_args()
    print('Ledger backed up to',reset_ledger(args.db))


if __name__=='__main__':
    main()
