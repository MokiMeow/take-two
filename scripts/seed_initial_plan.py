"""Post the initial planning command through Mattermost as the named director."""
import asyncio
import argparse
from pathlib import Path

import httpx
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SeedSettings(BaseSettings):
    model_config=SettingsConfigDict(env_file='.env',extra='ignore')
    take_two_director_mm_user: str
    take_two_director_mm_password: SecretStr
    take_two_mattermost_url: str='http://127.0.0.1:8065'
    take_two_production_channel_id: str


class User(BaseModel):
    id: str


async def post_plan(http: httpx.AsyncClient, base: str, username: str, password: str, channel: str) -> str:
    login=await http.post(base+'/api/v4/users/login',json=dict(login_id=username,password=password))
    login.raise_for_status()
    User.model_validate(login.json())
    token=login.headers['Token']
    response=await http.post(base+'/api/v4/posts',headers={'Authorization':'Bearer '+token},
        json=dict(channel_id=channel,message='/plan day-1'))
    response.raise_for_status()
    return User.model_validate(response.json()).id


async def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,default=Path('.env'))
    args=parser.parse_args()
    settings=SeedSettings(_env_file=args.env_file)
    async with httpx.AsyncClient(timeout=30) as http:
        await post_plan(http,settings.take_two_mattermost_url,settings.take_two_director_mm_user,
            settings.take_two_director_mm_password.get_secret_value(),settings.take_two_production_channel_id)
    print('Initial planning requested in Mattermost. Workers propose; checker checks; director approves the native card.')


if __name__=='__main__':
    asyncio.run(main())
