import json
from pathlib import Path

import pytest

from coordinator.commands import parse_command
from coordinator.config import Settings
from coordinator.render_bridge import RenderBridge, RenderError


def test_settings_loads_dotenv_without_exposing_secret(tmp_path):
    env = tmp_path / '.env'
    env.write_text('SWITCH_REGISTRATION_KEY=private-value\n', encoding='utf-8')
    settings = Settings(_env_file=env)
    assert settings.switch_registration_key.get_secret_value() == 'private-value'
    assert 'private-value' not in repr(settings)


def test_parse_command_and_pending_report():
    result = parse_command('/change person maya hard_stop 18:00', 'ad', 'm1')
    assert result.command.target == 'maya'
    assert result.command.value == '18:00'
    assert result.status == 'recorded'
    assert parse_command('I have to leave at six', 'maya', 'm2').status == 'pending_confirmation'
    assert parse_command('/change person maya', 'ad', 'm3').status == 'rejected'


def test_command_bounds():
    assert parse_command('x' * 9000, 'ad', 'm').status == 'rejected'


@pytest.mark.asyncio
async def test_missing_renderer_placeholder_is_explicit(tmp_path):
    bridge = RenderBridge(tmp_path / 'out', cli=tmp_path / 'missing.mjs')
    result = await bridge.render('preview', {'scene_id': 's3'})
    assert result.placeholder is True
    assert result.path.suffix == '.txt'
    assert 'PLACEHOLDER' in result.path.read_text()


@pytest.mark.asyncio
async def test_renderer_never_accepts_oversize_manifest(tmp_path):
    bridge = RenderBridge(tmp_path / 'out')
    with pytest.raises(RenderError):
        await bridge.render('preview', {'text': 'a' * 300000})


@pytest.mark.asyncio
async def test_render_hash_matches_checker_for_unicode_and_self_hash(tmp_path):
    from coordinator.constraints import Manifest
    from coordinator.checker import manifest_hash
    manifest = Manifest(scene_id='s3', location='café', start='2026-11-06T16:00:00+05:30',
        end='2026-11-06T17:00:00+05:30', setup_min=0, wrap_min=0,
        people=['maya'], shots=['wide'], script_rev=1, constraints_rev=1)
    digest = manifest_hash(manifest)
    payload = manifest.model_dump(mode='json')
    payload['manifest_hash'] = digest
    result = await RenderBridge(tmp_path, cli=tmp_path/'missing.mjs').render('preview', payload)
    assert result.manifest_hash == digest
