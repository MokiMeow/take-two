"""Local configuration; secret values never participate in repr or logs."""
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)
    switch_api_url: str = 'http://127.0.0.1:8000'
    switch_registration_key: SecretStr = SecretStr('')
    switch_production_room_id: str = ''
    switch_crew_room_ids: str = ''
    take_two_director_id: str = ''
    take_two_producer_id: str = ''
    take_two_ad_id: str = ''
    take_two_safety_id: str = ''
    take_two_capability_authority_id: str = ''
    take_two_supervisor_agent_id: str = ''
    take_two_ad_agent_id: str = ''
    take_two_supervisor_sender_id: str = ''
    take_two_ad_sender_id: str = ''
    take_two_supervisor_agent_name: str = ''
    take_two_ad_agent_name: str = ''
    take_two_tz: str = 'Asia/Kolkata'
    take_two_db: Path = Path('data/ledger.sqlite')
    take_two_artifacts: Path = Path('out')
    take_two_identity: Path = Path('data/identity.json')
    take_two_dev: bool = False
    take_two_render_timeout: int = Field(default=120, ge=1, le=300)

    @property
    def crew_room_ids(self) -> list[str]:
        return [item.strip() for item in self.switch_crew_room_ids.split(',') if item.strip()][:20]
