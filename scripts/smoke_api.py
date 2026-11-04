"""Exercise the live local API and SSE; prints no credentials or report content."""
import asyncio
import json
import httpx
from coordinator.ui_models import State


async def main() -> None:
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8787', timeout=10) as client:
        response = await client.get('/api/state')
        response.raise_for_status()
        before = State.model_validate(response.json())
        async with client.stream('GET', '/api/events') as stream:
            lines = stream.aiter_lines()
            async def next_state() -> State:
                async for line in lines:
                    if line.startswith('data: '):
                        return State.model_validate_json(line[6:])
                raise RuntimeError('SSE ended before a State arrived.')
            await next_state()
            change = await client.post('/api/changes', json=dict(entity='location', target='rooftop',
                field='permission', value='refused', reporter='local-smoke-report'))
            change.raise_for_status()
            expected_id = change.json()['change_id']
            for _ in range(5):
                after = await asyncio.wait_for(next_state(), timeout=10)
                if any(item.id == expected_id for item in after.changes):
                    print(json.dumps(dict(state_http=response.status_code, state_valid=True,
                        change_http=change.status_code, change_status=change.json()['status'], sse_update=True,
                        constraints_unchanged=before.revisions.constraints == after.revisions.constraints)))
                    return
            raise RuntimeError('No committed change appeared on SSE.')


if __name__ == '__main__':
    asyncio.run(main())
