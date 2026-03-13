"""EventBus — fire-and-forget event publishing via Redis pub/sub."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import redis.asyncio as aioredis

logger = logging.getLogger("arxi.events")

CHANNEL = "arxi:events"


@dataclass
class Event:
    type: str
    resource_id: str
    data: dict
    actor_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, payload: str) -> "Event":
        return cls(**json.loads(payload))


class EventBus:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None

    async def connect(self, redis_url: str) -> None:
        try:
            self._redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await self._redis.ping()
            logger.info("EventBus connected to Redis")
        except Exception:
            logger.error("EventBus failed to connect to Redis — events disabled")
            self._redis = None

    async def disconnect(self) -> None:
        if self._pubsub:
            await self._pubsub.unsubscribe(CHANNEL)
            await self._pubsub.close()
            self._pubsub = None
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("EventBus disconnected")

    async def publish(self, event: Event) -> None:
        if not self._redis:
            return
        try:
            await self._redis.publish(CHANNEL, event.to_json())
        except Exception:
            logger.warning("EventBus publish failed", exc_info=True)

    async def subscribe(self):
        if not self._redis:
            return
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(CHANNEL)
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                try:
                    yield Event.from_json(message["data"])
                except Exception:
                    logger.warning("EventBus: malformed message skipped")


event_bus = EventBus()
