"""Prepare a local personal registration key without displaying credentials.

Prior art: Switch core/switch_core/gateway/api_keys.py and gateway/auth.py,
989225d8. Apache-2.0 with modified Commons Clause. Uses public HTTP APIs only.
"""
import asyncio
from pathlib import Path

from dotenv import dotenv_values
import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

ROOT = Path(__file__).resolve().parents[1]


class LocalConfig(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    GATEWAY_ADMIN_EMAIL: str
    GATEWAY_ADMIN_PASSWORD: SecretStr


class KeyInfo(BaseModel):
    id: str
    label: str | None = None
    type: str


class PersonalKey(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    key: SecretStr


class KeyRequest(BaseModel):
    label: str = Field(default='Take Two judge rehearsal', max_length=200)


async def main() -> None:
    destination = ROOT / 'data/judge.env'
    if destination.exists() and dotenv_values(destination).get('SWITCH_REGISTRATION_KEY'):
        print('Local judge credentials already prepared (values hidden).')
        return
    config = LocalConfig.model_validate(dotenv_values(ROOT / 'scripts/switch/.env'))
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000/gateway', timeout=30) as client:
        login = await client.post('/auth/login', json=dict(email=config.GATEWAY_ADMIN_EMAIL,
            password=config.GATEWAY_ADMIN_PASSWORD.get_secret_value()))
        login.raise_for_status()
        response = await client.get('/api-keys')
        response.raise_for_status()
        keys = [KeyInfo.model_validate(k) for k in response.json()]
        request = KeyRequest()
        existing = next((k for k in keys if k.label == request.label and k.type == 'registration'), None)
        response = await client.get(f'/api-keys/{existing.id}/reveal') if existing else await client.post('/api-keys', json=request.model_dump())
        response.raise_for_status()
        key = PersonalKey.model_validate(response.json())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('SWITCH_REGISTRATION_KEY=' + key.key.get_secret_value() + '\n', encoding='utf-8', newline='\n')
    print('Prepared data/judge.env with a personal registration key (values hidden).')


if __name__ == '__main__':
    asyncio.run(main())
