"""Validate the two real rehearsals and the review server without printing credentials."""
import json
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
import httpx

from coordinator.switch_models import Identity
from coordinator.ui_models import State
from coordinator.unicode_text import require_unicode


ROOT = Path(__file__).resolve().parents[1]


def verify(state: dict[str, Any]) -> dict[str, Any]:
    state = State.model_validate(state).model_dump(mode='json', exclude_none=True)
    require_unicode(state)
    raw = json.dumps(state, ensure_ascii=False)
    assert '\\udc' not in raw.lower()
    identities = [Identity.model_validate_json(p.read_text(encoding='utf-8'))
                  for p in (ROOT / 'data/w4-demo').glob('w4-*.json')]
    secrets = [i.api_key.get_secret_value() for i in identities]
    for path in (ROOT / '.env', ROOT / 'data/w4-demo/.env'):
        secrets.extend(value for key, value in dotenv_values(path).items() if value
                       and any(word in key.upper() for word in ('KEY', 'TOKEN', 'PASSWORD')))
    assert not any(value in raw for value in secrets if len(value) >= 8), 'Credential found in state'
    settings = json.loads((ROOT / 'data/w4-demo/settings.json').read_text(encoding='utf-8'))
    coordinator = Identity.model_validate_json((ROOT / 'data/w4-demo/w4-coordinator.json').read_text(encoding='utf-8'))
    own = {settings['take_two_coordinator_sender_id'], coordinator.agent_id}
    assert not any(c['reporter'] in own for c in state['changes'])
    assert len(state['changes']) == 3
    assert sorted(c['reporter_name'] for c in state['changes']) == ['Isha', 'Maya', 'Nila']
    assert len([c for c in state['changes'] if c['field'] == 'report']) == 1
    hard_stop = next(c for c in state['changes'] if c['field'] == 'hard_stop')
    assert hard_stop['at'] == '2026-11-06T18:00:00+05:30' and hard_stop['value'] == '18:00'
    assert hard_stop['recorded_at']
    assert state['decision']['authority_name'] == 'Arun'
    assert state['decision']['answer']['answered_by_name'] == 'Arun'
    assert state['decision']['must_keep'] and state['decision']['requirements_note']
    assert all(c['role_label'] for c in state['crew'])
    assert all(p['room_name'] == '#production' for r in state['releases'] for p in r['publications'])
    assert [r['release_id'] for r in state['releases']] == ['r2', 'r1']
    assert state['releases'][0]['status'] == 'published'
    assert len(state['releases'][0]['acks']['confirmed']) == 3
    assert not any('@switch-' in t['text'] for t in state['timeline'])
    assert len([t for t in state['timeline'] if 'reported a change' in t['text']]) == 1
    return state


def main() -> None:
    runs = [json.loads((ROOT / f'data/w5-final-run-{i}.json').read_text(encoding='utf-8')) for i in (1, 2)]
    for run in runs:
        verify(run['state'])
    assert runs[0]['summary'] == runs[1]['summary']
    assert runs[0]['state']['releases'][0]['manifest_hash'] == runs[1]['state']['releases'][0]['manifest_hash']
    with httpx.Client(base_url='http://127.0.0.1:8787', timeout=10) as client:
        response = client.get('/api/state')
        response.raise_for_status()
        state = verify(response.json())
        codes = {path: client.get(path).status_code for path in (
            '/', state['releases'][0]['call_sheet_url'], state['releases'][0]['preview_url'])}
        assert all(code == 200 for code in codes.values())
    (ROOT / 'work/W5-state.json').write_text(json.dumps(state, ensure_ascii=False, separators=(',', ':')) + '\n',
        encoding='utf-8', newline='\n')
    proof = dict(tests='data/w5-final-tests.txt', runs=2, changes=3, coordinator_reports=0,
        lone_surrogates=0, hard_stop_at='2026-11-06T18:00:00+05:30',
        matching_summary=True, matching_manifest_hash=True, http=codes,
        timeline_count=len(state['timeline']), release_hash=state['releases'][0]['manifest_hash'])
    (ROOT / 'data/w5-verification.json').write_text(json.dumps(proof, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
