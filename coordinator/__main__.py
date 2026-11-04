"""uv run python -m coordinator: one loopback-only coordinator process."""
import asyncio
import uvicorn

from coordinator.api import create_app
from coordinator.config import Settings
from coordinator.runtime import Runtime


async def main() -> None:
    settings = Settings()
    runtime = Runtime(settings)
    app = create_app(runtime.ledger, runtime.handle_ui_change, artifacts_dir=settings.take_two_artifacts,
                     dev=settings.take_two_dev)
    await runtime.start()
    try:
        await uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8787, log_level='warning')).serve()
    finally:
        await runtime.close()


if __name__ == '__main__':
    asyncio.run(main())
