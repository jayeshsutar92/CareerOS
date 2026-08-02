from __future__ import annotations

import asyncio
import logging
import signal

from app.agents.bootstrap import register_agents
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.redis import close_redis_client, ping_redis
from app.workers.runner import WorkerRunner
from app.workers.tasks import register_tasks

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    register_tasks()
    register_agents()

    await ping_redis()
    runner = WorkerRunner(queue_name=settings.worker_queue_name)

    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, runner.stop)
        except NotImplementedError:
            signal.signal(signal_name, lambda *_: runner.stop())

    try:
        await runner.run_forever()
    finally:
        await close_redis_client()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
