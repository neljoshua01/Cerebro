from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cerebro.api.app import create_app


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "tasks.sqlite3"))


def create_job(client: TestClient) -> dict:
    response = client.post(
        "/api/jobs",
        json={
            "objective": "Build task support",
            "project": "cerebro",
        },
    )

    assert response.status_code == 201

    return response.json()


def test_task_api_create_list_and_retrieve(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    job = create_job(client)

    first_response = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "First task",
            "description": "First task description",
            "position": 1,
        },
    )

    assert first_response.status_code == 201

    first = first_response.json()

    assert first["job_id"] == job["id"]
    assert first["title"] == "First task"
    assert first["description"] == "First task description"
    assert first["status"] == "PENDING"
    assert first["position"] == 1
    assert first["version"] == 1

    second_response = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Second task",
            "position": 2,
        },
    )

    assert second_response.status_code == 201

    second = second_response.json()

    assert second["description"] is None
    assert second["position"] == 2

    listed_response = client.get(
        f"/api/jobs/{job['id']}/tasks"
    )

    assert listed_response.status_code == 200

    listed = listed_response.json()

    assert [task["id"] for task in listed] == [
        first["id"],
        second["id"],
    ]

    assert [task["position"] for task in listed] == [1, 2]

    retrieved_response = client.get(
        f"/api/tasks/{first['id']}"
    )

    assert retrieved_response.status_code == 200
    assert retrieved_response.json() == first


def test_task_api_valid_transitions(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    job = create_job(client)

    response = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Lifecycle task",
            "position": 1,
        },
    )

    assert response.status_code == 201

    task = response.json()

    response = client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"target_state": "READY"},
    )

    assert response.status_code == 200

    task = response.json()

    assert task["status"] == "READY"
    assert task["version"] == 2

    response = client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"target_state": "RUNNING"},
    )

    assert response.status_code == 200

    task = response.json()

    assert task["status"] == "RUNNING"
    assert task["version"] == 3

    response = client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"target_state": "COMPLETED"},
    )

    assert response.status_code == 200

    task = response.json()

    assert task["status"] == "COMPLETED"
    assert task["version"] == 4


def test_task_api_rejects_invalid_transitions(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    job = create_job(client)

    response = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Invalid transition task",
            "position": 1,
        },
    )

    assert response.status_code == 201

    task = response.json()

    # PENDING cannot jump directly to RUNNING.
    response = client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"target_state": "RUNNING"},
    )

    assert response.status_code == 409

    # PENDING cannot jump directly to COMPLETED.
    response = client.post(
        f"/api/tasks/{task['id']}/transition",
        json={"target_state": "COMPLETED"},
    )

    assert response.status_code == 409


def test_task_api_rejects_missing_resources(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    missing_job_response = client.post(
        "/api/jobs/missing-job/tasks",
        json={
            "title": "Orphan task",
            "position": 1,
        },
    )

    assert missing_job_response.status_code == 404

    missing_task_response = client.get(
        "/api/tasks/missing-task"
    )

    assert missing_task_response.status_code == 404

    missing_task_transition = client.post(
        "/api/tasks/missing-task/transition",
        json={"target_state": "READY"},
    )

    assert missing_task_transition.status_code == 404

    missing_job_list = client.get(
        "/api/jobs/missing-job/tasks"
    )

    assert missing_job_list.status_code == 404


def test_task_api_validates_input(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    job = create_job(client)

    blank_title = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "   ",
            "position": 1,
        },
    )

    assert blank_title.status_code == 422

    missing_position = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Missing position",
        },
    )

    assert missing_position.status_code == 422

    invalid_position = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Invalid position",
            "position": 0,
        },
    )

    assert invalid_position.status_code == 422

    blank_description = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Description normalization",
            "description": "   ",
            "position": 1,
        },
    )

    assert blank_description.status_code == 201
    assert blank_description.json()["description"] is None


def test_task_persists_through_app_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "tasks.sqlite3"

    client = TestClient(create_app(database_path))

    job = create_job(client)

    created_response = client.post(
        f"/api/jobs/{job['id']}/tasks",
        json={
            "title": "Persistent task",
            "description": "Must survive recreation",
            "position": 1,
        },
    )

    assert created_response.status_code == 201

    created = created_response.json()

    transitioned_response = client.post(
        f"/api/tasks/{created['id']}/transition",
        json={"target_state": "READY"},
    )

    assert transitioned_response.status_code == 200

    transitioned = transitioned_response.json()

    # Create a completely new FastAPI application against the same database.
    second_client = TestClient(create_app(database_path))

    retrieved_response = second_client.get(
        f"/api/tasks/{created['id']}"
    )

    assert retrieved_response.status_code == 200
    assert retrieved_response.json() == transitioned
