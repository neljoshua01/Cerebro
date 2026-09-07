from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cerebro.api.jobs import router as jobs_router
from cerebro.api.tasks import router as tasks_router
from cerebro.core.sqlite import SqliteTransaction
from cerebro.events.broadcaster import EventBroadcaster
from cerebro.events.repository import SqliteEventRepository
from cerebro.tasks.repository import SqliteTaskRepository
from cerebro.tasks.service import TaskService
from cerebro.jobs.repository import SqliteJobRepository
from cerebro.jobs.service import JobService


def create_app(database_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Cerebro API", version="0.1.0")
    app.state.database_path = database_path or Path(
        os.environ.get("CEREBRO_DATABASE_PATH", "workspace/data/cerebro.sqlite3")
    )

    app.state.event_broadcaster = EventBroadcaster()

    app.state.job_service = JobService(
        SqliteJobRepository(app.state.database_path),
        SqliteEventRepository(app.state.database_path),
        SqliteTransaction(app.state.database_path),
    )

    app.state.task_service = TaskService(
        SqliteTaskRepository(app.state.database_path)
    )
    app.include_router(jobs_router)
    app.include_router(tasks_router)

    # In development, the frontend is mounted into the container at /app/frontend.
    # Keeping the API and static UI in the same service avoids CORS complexity in V1.
    app.mount("/assets", StaticFiles(directory="/app/frontend/assets"), name="assets") if False else None

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "cerebro"}

    @app.get("/api/system/health")
    def system_health() -> dict[str, object]:
        return {
            "status": "healthy",
            "components": {
                "api": "online",
                "core": "scaffold",
                "jobs": "available",
                "agents": "scaffold",
                "memory": "scaffold",
            },
        }

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse("/app/frontend/index.html")

    @app.websocket("/ws/events")
    async def events(websocket: WebSocket) -> None:
        broadcaster = app.state.event_broadcaster

        await websocket.accept()
        await broadcaster.connect(websocket)

        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await broadcaster.disconnect(websocket)

    return app

app = create_app()
