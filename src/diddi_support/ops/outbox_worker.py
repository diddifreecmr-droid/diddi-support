from __future__ import annotations

import asyncio
import logging

from prometheus_client import start_http_server
from redis.asyncio import Redis

from diddi_support.core.config import settings
from diddi_support.core.database import session_factory
from diddi_support.infrastructure.outbox import OutboxDispatcher, RedisStreamPublisher

logging.basicConfig(level=settings.log_level, format="%(message)s")


async def main() -> None:
    if session_factory is None or not settings.redis_url:
        raise RuntimeError("DATABASE_URL and REDIS_URL are required for the outbox worker")
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    dispatcher = OutboxDispatcher(
        session_factory,
        RedisStreamPublisher(
            redis,
            stream_name=settings.outbox_stream_name,
            maxlen=settings.outbox_stream_maxlen,
        ),
    )
    start_http_server(settings.outbox_metrics_port, registry=dispatcher.metrics.registry)
    try:
        while True:
            processed = await dispatcher.run_once()
            if processed == 0:
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
