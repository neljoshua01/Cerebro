from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cerebro.api.app import create_app


def test_websocket_events_connects_and_stays_open(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "cerebro.sqlite3"))

    with client.websocket_connect("/ws/events") as websocket:
        websocket.send_text("ping")


def test_websocket_events_disconnects_cleanly(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "cerebro.sqlite3"))

    with client.websocket_connect("/ws/events") as websocket:
        websocket.send_text("ping")

    # Exiting the context closes the client connection.
    # The endpoint should handle WebSocketDisconnect without error.
