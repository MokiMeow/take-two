"""Serve the last verified real-server rehearsal ledger on the Control Room port."""
import asyncio
from pathlib import Path

import uvicorn

from coordinator.api import create_app
from coordinator.config import Settings
from coordinator.runtime import Runtime


async def main() -> None:
    path=Path('data/w4-demo/settings.json')
    if path.stat().st_size>65536:
        raise ValueError('Rehearsal settings exceed 64 KiB')
    settings=Settings(_env_file=None,**__import__('json').loads(path.read_text(encoding='utf-8')))
    runtime=Runtime(settings)
    await runtime.start()
    app=create_app(runtime.ledger,runtime.handle_ui_change,artifacts_dir=settings.take_two_artifacts)
    try:
        await uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8787,log_level='warning')).serve()
    finally:
        await runtime.close()


if __name__=='__main__':
    asyncio.run(main())
