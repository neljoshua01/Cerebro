from __future__ import annotations

from typing import Protocol


class WebSocketConnection(Protocol):
    async def send_json(self, message: dict[str, object]) -> None:
        ...


class EventBroadcaster:
    """Manage in-memory WebSocket connections and broadcast messages."""

    def __init__(self) -> None:
        self._connections: set[WebSocketConnection] = set()

    async def connect(self, websocket: WebSocketConnection) -> None:
        self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocketConnection) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, object]) -> None:
        disconnected: list[WebSocketConnection] = []

        for websocket in self._connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self._connections.discard(websocket)