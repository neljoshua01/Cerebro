from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Cerebro API", version="0.1.0")

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
            "jobs": "scaffold",
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
