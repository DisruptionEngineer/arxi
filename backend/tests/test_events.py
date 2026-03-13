import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arxi.events import Event, EventBus, event_bus


def _make_event(**overrides) -> Event:
    defaults = {
        "type": "prescription.status_changed",
        "resource_id": "rx-001",
        "data": {"status": "approved", "patient_name": "John Doe"},
        "actor_id": "test-user",
    }
    defaults.update(overrides)
    return Event(**defaults)


async def test_event_serialization():
    evt = _make_event()
    payload = evt.to_json()
    parsed = json.loads(payload)
    assert parsed["type"] == "prescription.status_changed"
    assert parsed["resource_id"] == "rx-001"
    assert parsed["data"]["status"] == "approved"
    assert parsed["actor_id"] == "test-user"
    assert "timestamp" in parsed


async def test_event_from_json():
    evt = _make_event()
    payload = evt.to_json()
    restored = Event.from_json(payload)
    assert restored.type == evt.type
    assert restored.resource_id == evt.resource_id
    assert restored.data == evt.data
    assert restored.actor_id == evt.actor_id


async def test_publish_calls_redis_publish():
    bus = EventBus()
    bus._redis = AsyncMock()
    bus._redis.publish = AsyncMock()
    evt = _make_event()
    await bus.publish(evt)
    bus._redis.publish.assert_called_once()
    channel, payload = bus._redis.publish.call_args[0]
    assert channel == "arxi:events"
    parsed = json.loads(payload)
    assert parsed["type"] == "prescription.status_changed"


async def test_publish_swallows_redis_errors(caplog):
    bus = EventBus()
    bus._redis = AsyncMock()
    bus._redis.publish = AsyncMock(side_effect=ConnectionError("Redis down"))
    evt = _make_event()
    await bus.publish(evt)


async def test_publish_noop_when_not_connected():
    bus = EventBus()
    bus._redis = None
    evt = _make_event()
    await bus.publish(evt)


async def test_event_bus_singleton():
    assert isinstance(event_bus, EventBus)
