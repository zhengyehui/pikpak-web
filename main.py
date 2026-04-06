import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from database import init_db, get_file_count, get_scanned_folder_count, clear_all
from scanner import PikPakScanner
from stats_cache import StatsCache

app = FastAPI(title="PikPak Storage Analyzer")
scanner = PikPakScanner()
cache = StatsCache()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup():
    await init_db()
    # Pre-build cache from existing DB data
    if await get_file_count() > 0:
        await cache.rebuild()


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/scan/start")
async def scan_start(full_rescan: bool = False):
    if scanner.is_scanning:
        return {"status": "already_scanning"}
    if full_rescan:
        await clear_all()

    async def scan_and_rebuild():
        await scanner.scan(full_rescan=full_rescan)
        await cache.rebuild()

    asyncio.create_task(scan_and_rebuild())
    return {"status": "started"}


@app.post("/api/scan/stop")
async def scan_stop():
    await scanner.stop()
    return {"status": "stopping"}


@app.get("/api/scan/status")
async def scan_status():
    return {
        "is_scanning": scanner.is_scanning,
        "scanned_files": scanner.scanned_files,
        "scanned_folders": scanner.scanned_folders,
        "current_path": scanner.current_path,
        "cached_files": await get_file_count(),
        "cached_folders": await get_scanned_folder_count(),
    }


@app.get("/api/stats/size-distribution")
async def size_distribution():
    return cache.size_distribution if cache.ready else []


@app.get("/api/stats/type-distribution")
async def type_distribution():
    return cache.type_distribution if cache.ready else []


@app.get("/api/stats/treemap")
async def treemap(parent_id: str = ""):
    if not cache.ready:
        return {"id": "", "name": "PikPak", "total_size": 0, "children": []}
    return cache.get_treemap(parent_id)


@app.get("/api/stats/top-folders")
async def top_folders(limit: int = 100):
    return cache.top_folders[:limit] if cache.ready else []


@app.get("/api/stats/top-files")
async def top_files(limit: int = 100):
    return cache.top_files[:limit] if cache.ready else []


@app.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    await websocket.accept()

    async def send_event(event: dict):
        try:
            await websocket.send_text(json.dumps(event, ensure_ascii=False))
        except Exception:
            pass

    scanner.add_listener(send_event)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        scanner.remove_listener(send_event)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
