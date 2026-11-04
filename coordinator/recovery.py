"""Source-position fence plus authoritative member-room history catch-up.

Switch has no caught_up frame. Own events can include native commands absent
from read_context, so history alone is insufficient: drain the own-event source
through a separately sampled authoritative head before consuming outcomes.
"""
import asyncio

from coordinator.ledger import now_iso
from coordinator.switch_models import RoomContext, SwitchFrame


class Recovery:
    def transport_lost(self) -> None:
        self.ready = False
        self.catching_up = True
        self.transport_epoch += 1
        self.catchup_through = None

    async def begin_catchup(self) -> None:
        epoch=self.transport_epoch
        self.catching_up = True
        self.replay_fence = await self.client.head_position()
        self.catchup_deadline = asyncio.get_running_loop().time()+45
        through = now_iso()  # Never advance the next lower bound past a history read.
        since = self.ledger.get_meta('history_since',through)
        rooms = await self.client.member_rooms()
        if len(rooms)>20:
            raise ValueError('Catch-up exceeds 20 member rooms; effects remain paused')
        pending=[]
        size=0
        for room in rooms:
            room_id = room.get('room_id',room.get('id'))
            context = RoomContext.model_validate(await self.client.read_context(room_id,since))
            if context.truncated:
                raise ValueError('Catch-up history is truncated; effects remain paused')
            entries = [e for t in context.threads for e in [t.root,*t.replies]]
            pending.extend((entry.timestamp or 0,room_id,entry) for entry in entries if entry.kind=='message' and entry.body)
            size+=sum(len((entry.body or '').encode()) for entry in entries)
            if len(pending)>1000 or size>4*1024*1024:
                raise ValueError('Catch-up exceeds 1000 entries; effects remain paused')
        for _,room_id,entry in sorted(pending,key=lambda item:(item[0],item[1],item[2].id)):
            frame = SwitchFrame(event='message',data=dict(room_id=room_id,payload=dict(
                sender=entry.sender,sender_name=entry.sender_name,body=entry.body,message_id=entry.id)))
            await self.accept_frame(frame)
        if epoch!=self.transport_epoch:
            raise ConnectionError('Transport changed during history reconciliation')
        self.catchup_through = through

    async def finish_catchup(self) -> None:
        if not self.catching_up or not getattr(self,'catchup_through',None):
            return
        committed = self.ledger.get_meta('event_position',{})
        if committed.get('s',0)<self.replay_fence.get('s',0):
            return
        epoch=self.transport_epoch
        outcomes=await self.client.get_outcomes()
        if epoch!=self.transport_epoch:
            return
        for outcome in outcomes:
            await self.loop.handle_outcome(outcome)
        if epoch!=self.transport_epoch:
            return
        with self.ledger.transaction():
            self.ledger.set_meta('history_since',self.catchup_through)
        self.catching_up=False
        self.ready=True
