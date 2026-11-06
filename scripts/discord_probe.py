"""Live Discord check: create #crew through Switch, post a message and an image."""
import asyncio
import json
import sys

from coordinator.config import Settings
from coordinator.switch_client import SwitchClient

YAML = """
params:
  name: {type: string, default: crew}
  bridge: {type: bridge}
  coordinator: {type: agent, default: take-two-coordinator}
room:
  name: "{name}"
  description: Approved Take Two plans, holds and crew confirmations
  bridge: "{bridge}"
  channel_type: channel_private
  read_visibility: private
  write_visibility: private
  agents: ["{coordinator}"]
  users: ["{$creator}"]
"""


async def main(name: str) -> None:
    s = Settings()
    c = SwitchClient(s.switch_api_url, s.take_two_identity, s.switch_registration_key.get_secret_value())
    await c.initialize()
    ready = asyncio.Event()
    async def observe():
        async for f in c.events():
            if f.event == 'connection_state':
                ready.set()
    obs = asyncio.create_task(observe())
    try:
        await asyncio.wait_for(ready.wait(), 20)
        bridges = await c.operation('list_bridges')
        print('bridges:', [(b['type'], b['display_name'], b.get('can_create_channels')) for b in bridges])
        rooms = [r for r in await c.member_rooms() if r.get('name') == name]
        if rooms:
            room_id = rooms[0]['room_id']
            print('room exists:', room_id)
        else:
            r = await c.create_room_from_yaml(YAML, dict(name=name, bridge='Discord crew',
                coordinator=s.take_two_coordinator_name or 'take-two-coordinator'))
            room_id = r.room_id
            print('created:', r.room_name, room_id, 'failed:', r.failed_attachments)
        msg = await c.send_message(room_id, f'Take Two check: the coordinator can post in #{name} through Switch.')
        print('message:', msg)
        media = await c.send_media(room_id, 'docs/explainer/how-it-works.png', caption='How Take Two works')
        print('media:', json.dumps(media)[:300])
    finally:
        obs.cancel()
        await c.aclose()


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'crew'))
