"""Read-only W9 snapshot, card wording, file-format and review-server checks."""
from pathlib import Path
import hashlib
import json
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coordinator.ui_models import State


def main() -> None:
    originals = json.loads((ROOT/'data/w9-before/top-fixture-hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p, h in originals.items())
    paths = sorted((ROOT/'fixtures/ui-state/day').glob('*.json'))
    assert len(paths) == 26
    for path in paths:
        state = State.model_validate_json(path.read_text(encoding='utf-8')).model_dump(exclude_none=True)
        for report in state['changes']:
            if report.get('resolution') == 'recorded':
                recorded = next(c for c in state['changes'] if c['id'] == report['resolved_by_change'])
                assert recorded['status'] == 'recorded' and not recorded.get('resolution')
                assert report['resolved_at'] == recorded['recorded_at']
        for release in state['releases']:
            for lines in release['duty_changes'].values():
                for line in lines:
                    assert all(t not in line for t in ('camera_sound', 'sound_recorder', 'kit none', 'was unconfirmed'))
                    if line.startswith('Call ') and '(was ' in line:
                        assert line.split()[1] != line.split('(was ')[1].rstrip(')')
    final = json.loads(paths[-1].read_text(encoding='utf-8'))
    cannot = json.loads(paths[10].read_text(encoding='utf-8'))
    assert any(c['reporter_name'] == 'Dev' and c['field'] == 'report' and not c.get('resolution')
        for c in cannot['changes'])
    reports = [c for c in final['changes'] if c['field'] == 'report']
    assert {r['reporter_name'] for r in reports} == {'Maya', 'Dev'}
    assert all(r['resolution'] == 'recorded' for r in reports)
    cards = json.loads((ROOT/'data/w8-demo/cards.json').read_text(encoding='utf-8'))
    assert any('Record Maya: hard stop 18:00?' in c['prompt'] for c in cards)
    assert any('kit sound recorder → lav mic' in c['prompt'] for c in cards)
    for card in cards:
        assert all(t not in card['prompt'] for t in ('camera_sound', 'sound_recorder', 'kit none', 'was unconfirmed'))
    # Historical W8 spellings remain readable without being emitted on the wire.
    legacy = dict(reports[0], resolution='dismissed')
    legacy_state = dict(final, changes=[legacy])
    assert State.model_validate(legacy_state).changes[0].resolution == 'ignored'
    changed = [Path(p.relative_to(ROOT/'data/w9-before')) for p in (ROOT/'data/w9-before').rglob('*')
        if p.is_file() and p.parts[-2] != 'w9-before']
    changed += [Path('coordinator/tests/test_w9_reports_text.py'), Path('coordinator/tests/test_w5_state.py'),
        Path('work/W9-verify.py'), Path('work/W9-browser.mjs')]
    for path in changed + [p.relative_to(ROOT) for p in paths]:
        if not (ROOT/path).is_file():
            continue
        raw = (ROOT/path).read_bytes()
        assert b'\r\n' not in raw, path
        assert len(raw.decode('utf-8').splitlines()) < 500, path
    with httpx.Client(base_url='http://127.0.0.1:8787', timeout=10) as http:
        assert http.get('/').status_code == 200
        response = http.get('/api/state')
        response.raise_for_status()
        current = State.model_validate(response.json())
        assert current.releases[0].release_id == 'r5'
        for url in (current.releases[0].call_sheet_url, current.releases[0].preview_url):
            assert url and http.get(url).status_code == 200
    print('26 strict day snapshots; linked reports; native card wording; unchanged original fixtures; LF/<500 lines; review r5/media HTTP 200')


if __name__ == '__main__':
    main()
