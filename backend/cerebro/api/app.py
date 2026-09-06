from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cerebro.api.jobs import router as jobs_router
from cerebro.jobs.repository import SqliteJobRepository
from cerebro.jobs.service import JobService


def create_app(database_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Cerebro API", version="0.1.0")
    app.state.database_path = database_path or Path(
        os.environ.get("CEREBRO_DATABASE_PATH", "workspace/data/cerebro.sqlite3")
    )
    app.state.job_service = JobService(SqliteJobRepository(app.state.database_path))
    app.include_router(jobs_router)

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
        await websocket.accept()
        await websocket.send_json({"type": "connected", "service": "cerebro"})
        await websocket.close()

    return app

app = create_app()
