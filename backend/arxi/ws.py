"""WebSocket endpoint for real-time event streaming."""

import logging

from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError

from arxi.config import settings
from arxi.events import event_bus

logger = logging.getLogger("arxi.ws")

WS_CLOSE_AUTH_FAILED = 4001


def _validate_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None


async def ws_events(websocket: WebSocket, token: str | None = None):
    username = _validate_token(token)
    if not username:
        await websocket.close(code=WS_CLOSE_AUTH_FAILED)
        return

    await websocket.accept()
    logger.info("WebSocket connected: %s", username)

    try:
        async for event in event_bus.subscribe():
            try:
                await websocket.send_text(event.to_json())
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("WebSocket disconnected: %s", username)
