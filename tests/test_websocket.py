from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cerebro.api.app import create_app
from cerebro.events.repository import SqliteEventRepository


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

def test_job_transition_broadcasts_persisted_event(tmp_path: Path) -> None:
    database_path = tmp_path / "cerebro.sqlite3"
    client = TestClient(create_app(database_path))

    with client.websocket_connect("/ws/events") as websocket:
        create_response = client.post(
            "/api/jobs",
            json={
                "objective": "Test WebSocket event delivery",
                "project": "test-project",
            },
        )
        assert create_response.status_code == 201

        job = create_response.json()

        transition_response = client.post(
            f"/api/jobs/{job['id']}/transition",
            json={"target_state": "UNDERSTANDING"},
        )
        assert transition_response.status_code == 200

        message = websocket.receive_json()

    persisted_events = SqliteEventRepository(database_path).list(
        job_id=job["id"],
    )

    assert len(persisted_events) == 1
    assert message == persisted_events[0].to_dict()
