"""Adapted from deploy/local/generate-env-secrets.sh (Switch 989225d8).

Copyright (c) 2026 SB Technology, Inc. dba SandboxAQ.
Source license: Apache-2.0 limited by modified Commons Clause; see LICENSE.switch.
Changed: Windows-native generation, no credential printing, project-owned paths.
"""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('E:/DevDrive/switch')
EXPECTED_COMMIT = '989225d8a13f6f36359c54f52d86aec01c4e0826'


def prepare() -> None:
    """Create fresh env files only; an existing secret is never rotated."""
    head = (SOURCE / '.git/HEAD').read_text().strip()
    actual = (SOURCE / '.git' / head.removeprefix('ref: ')).read_text().strip() if head.startswith('ref: ') else head
    if actual != EXPECTED_COMMIT:
        raise RuntimeError('Switch checkout differs from the required commit; refusing to build.')
    destination = ROOT / 'scripts/switch/.env'
    if not destination.exists():
        values = dict(
            SWITCH_VERSION='take-two-989225d8', SWITCH_BIND_ADDR='127.0.0.1',
            DB_USER='switch_app', DB_OWNER_USER='postgres', DB_NAME='switch',
            GATEWAY_ADMIN_EMAIL='admin@switch.local', MATTERMOST_ADMIN_USER='admin',
            MATTERMOST_TEAM_NAME='switch', MATTERMOST_USER='user',
            SECRET_KEYS='local:' + secrets.token_hex(32),
        )
        for name in ('DB_PASSWORD', 'DB_OWNER_PASSWORD', 'AGENT_REGISTRATION_TOKEN',
                     'GATEWAY_ADMIN_PASSWORD', 'MATTERMOST_ADMIN_PASSWORD', 'MATTERMOST_USER_PASSWORD'):
            values[name] = secrets.token_hex(24)
        destination.write_text(''.join(f'{key}={value}\n' for key, value in values.items()), encoding='utf-8', newline='\n')
    else:
        lines = destination.read_text(encoding='utf-8').splitlines()
        lines = [('SWITCH_VERSION=take-two-989225d8') if line.startswith('SWITCH_VERSION=') else line for line in lines]
        if not any(line.startswith('SWITCH_VERSION=') for line in lines):
            lines.append('SWITCH_VERSION=take-two-989225d8')
        destination.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    env = ROOT / '.env'
    if not env.exists():
        env.write_text(
            'SWITCH_API_URL=http://127.0.0.1:8000\nSWITCH_REGISTRATION_KEY=\n'
            'SWITCH_PRODUCTION_ROOM_ID=\nSWITCH_CREW_ROOM_IDS=\n'
            'TAKE_TWO_DIRECTOR_ID=\nTAKE_TWO_PRODUCER_ID=\nTAKE_TWO_AD_ID=\n'
            'TAKE_TWO_DB=./data/ledger.sqlite\nTAKE_TWO_ARTIFACTS=./out\n', encoding='utf-8', newline='\n')
    (ROOT / 'scripts/switch/LICENSE.switch').write_bytes((SOURCE / 'LICENSE').read_bytes())
    print('Prepared local configuration; secret values were not printed.')


if __name__ == '__main__':
    prepare()
