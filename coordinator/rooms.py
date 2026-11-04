"""Idempotent shoot-day provisioning; a missing Discord bridge is explicit."""
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Bridge(BaseModel):
    id: str
    type: str
    display_name: str
    status: str
    can_create_channels: bool = False


class DayRooms:
    async def provision_day(self) -> None:
        bridges = [Bridge.model_validate(b) for b in await self.client.operation('list_bridges')]
        discord = [b for b in bridges if b.type=='discord' and b.status=='active' and b.can_create_channels]
        if not discord:
            if self.ledger.get_meta('day_room_status')!='no_discord_bridge':
                with self.ledger.transaction():
                    self.ledger.set_meta('day_room_status','no_discord_bridge')
                    text = 'No Discord bridge yet. Day 1 room is pending; releases use configured destinations.'
                    self.ledger.timeline('error',text)
                    self.ledger.enqueue('message',dict(room_id=self.settings.switch_production_room_id,body=text),
                        'no-discord-bridge',self.loop.constraints.constraints_rev)
            return
        selected = next((b for b in discord if b.display_name==self.settings.take_two_discord_bridge),None)
        if selected is None and len(discord)==1:
            selected = discord[0]
        if selected is None:
            raise ValueError('Choose TAKE_TWO_DISCORD_BRIDGE when several Discord bridges exist')
        room_id = self.ledger.get_meta('day_room_id')
        if self.ledger.get_meta('day_room_status')=='attachment_failed':
            raise ValueError('Day room attachments need human reconciliation before publication')
        if room_id and self.ledger.get_meta('day_room_status')=='ready':
            if room_id not in self.loop.destinations:
                self.loop.destinations.append(room_id)
            if self.dispatcher and room_id not in self.dispatcher.crew_room_ids:
                self.dispatcher.crew_room_ids.append(room_id)
            return
        if not room_id:
            members = await self.client.member_rooms()
            matches = [r for r in members if r.get('name')=='day-1']
            if len(matches)>1:
                raise ValueError('Multiple day-1 rooms require operator reconciliation')
            if matches:
                room_id=matches[0]['room_id']
            elif self.ledger.get_meta('day_room_status')=='creating':
                raise ValueError('Day room creation is uncertain; reconcile membership before retrying')
            else:
                inputs = dict(bridge=selected.display_name,coordinator=self.settings.take_two_coordinator_name,
                    actor=self.settings.take_two_day_actor,camera=self.settings.take_two_day_camera,
                    sound=self.settings.take_two_day_sound)
                if not all(inputs.values()):
                    raise ValueError('Discord day-room crew usernames must be configured')
                with self.ledger.transaction():
                    self.ledger.set_meta('day_room_status','creating')
                root = Path(__file__).resolve().parents[1]
                result = await self.client.create_room_from_yaml((root/'templates/shoot-day.yaml').read_text(encoding='utf-8'),inputs)
                room_id=result.room_id
                with self.ledger.transaction():
                    self.ledger.set_meta('day_room_id',room_id)
                if result.failed_attachments:
                    with self.ledger.transaction():
                        self.ledger.set_meta('day_room_status','attachment_failed')
                    raise ValueError('Day room has failed attachments; inspect the room before publishing')
            with self.ledger.transaction():
                self.ledger.set_meta('day_room_id',room_id)
        try:
            room = await self.client.connect_to_production(room_id)
            name='day-1-plan'
            docs=[d for d in room.get('documents',[]) if d.get('name')==name]
            content='Approved complete releases appear here. Follow active holds; confirm the explicit current release ID.'
            if docs:
                if len(docs)!=1 or docs[0].get('created_by_agent_id')!=self.client.identity.agent_id:
                    raise ValueError('Day document ownership does not match coordinator')
            else:
                await self.client.create_room_document(name,'Day 1 instructions','Coordinator owned',content)
        finally:
            await self.client.connect_to_production(self.settings.switch_production_room_id)
        if room_id not in self.loop.destinations:
            self.loop.destinations.append(room_id)
        if self.dispatcher and room_id not in self.dispatcher.crew_room_ids:
            self.dispatcher.crew_room_ids.append(room_id)
        with self.ledger.transaction():
            self.ledger.set_meta('day_room_status','ready')
