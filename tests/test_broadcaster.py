from __future__ import annotations

import pytest

from cerebro.events.broadcaster import EventBroadcaster


class FakeWebSocket:
    def __init__(self, *, fail_on_send: bool = False) -> None:
        self.messages: list[dict[str, object]] = []
        self.fail_on_send = fail_on_send

    async def send_json(self, message: dict[str, object]) -> None:
        if self.fail_on_send:
            raise RuntimeError("WebSocket disconnected")

        self.messages.append(message)


@pytest.mark.anyio
async def test_connect_registers_client() -> None:
    broadcaster = EventBroadcaster()
    websocket = FakeWebSocket()

    await broadcaster.connect(websocket)

    await broadcaster.broadcast({"type": "test"})

    assert websocket.messages == [{"type": "test"}]


@pytest.mark.anyio
async def test_disconnect_unregisters_client() -> None:
    broadcaster = EventBroadcaster()
    websocket = FakeWebSocket()

    await broadcaster.connect(websocket)
    await broadcaster.disconnect(websocket)

    await broadcaster.broadcast({"type": "test"})

    assert websocket.messages == []


@pytest.mark.anyio
async def test_broadcast_sends_to_one_client() -> None:
    broadcaster = EventBroadcaster()
    websocket = FakeWebSocket()

    await broadcaster.connect(websocket)

    message = {
        "type": "JOB_STATE_CHANGED",
        "job_id": "job-123",
    }

    await broadcaster.broadcast(message)

    assert websocket.messages == [message]


@pytest.mark.anyio
async def test_broadcast_sends_to_multiple_clients() -> None:
    broadcaster = EventBroadcaster()
    websocket_one = FakeWebSocket()
    websocket_two = FakeWebSocket()

    await broadcaster.connect(websocket_one)
    await broadcaster.connect(websocket_two)

    message = {
        "type": "JOB_STATE_CHANGED",
        "job_id": "job-123",
    }

    await broadcaster.broadcast(message)

    assert websocket_one.messages == [message]
    assert websocket_two.messages == [message]


@pytest.mark.anyio
async def test_disconnected_client_is_not_broadcast_to() -> None:
    broadcaster = EventBroadcaster()
    websocket_one = FakeWebSocket()
    websocket_two = FakeWebSocket()

    await broadcaster.connect(websocket_one)
    await broadcaster.connect(websocket_two)

    await broadcaster.disconnect(websocket_one)

    message = {"type": "TEST"}

    await broadcaster.broadcast(message)

    assert websocket_one.messages == []
    assert websocket_two.messages == [message]


@pytest.mark.anyio
async def test_failed_client_does_not_block_other_clients() -> None:
    broadcaster = EventBroadcaster()
    failing_websocket = FakeWebSocket(fail_on_send=True)
    healthy_websocket = FakeWebSocket()

    await broadcaster.connect(failing_websocket)
    await broadcaster.connect(healthy_websocket)

    message = {"type": "TEST"}

    await broadcaster.broadcast(message)

    assert failing_websocket.messages == []
    assert healthy_websocket.messages == [message]

    # Failed connection should have been removed.
    await broadcaster.broadcast({"type": "SECOND"})

    assert healthy_websocket.messages == [message, {"type": "SECOND"}]