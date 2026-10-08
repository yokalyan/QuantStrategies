from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import yaml

from dashboard.analytics import compute_dashboard_analytics
from dashboard.runner import runner


app = FastAPI(title="TQQQ Midpoint ORB Quant Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONFIG_FILE = Path("configs/midpoint_stop_orb_intraday.yaml")

# Connected websockets
connected_clients: list[WebSocket] = []
main_loop: asyncio.AbstractEventLoop | None = None


@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()


def _broadcast_to_clients(payload: dict[str, Any]) -> None:
    if not connected_clients:
        return

    async def _send():
        for ws in list(connected_clients):
            try:
                await ws.send_json(payload)
            except Exception:
                if ws in connected_clients:
                    connected_clients.remove(ws)

    global main_loop
    if main_loop is None:
        try:
            main_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

    if main_loop and main_loop.is_running():
        try:
            current_loop = None
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if current_loop is main_loop:
                asyncio.create_task(_send())
            else:
                asyncio.run_coroutine_threadsafe(_send(), main_loop)
        except Exception:
            pass


runner.register_callback(_broadcast_to_clients)


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    data = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    return data


@app.post("/api/config")
def update_config(payload: dict[str, Any]) -> dict[str, Any]:
    data = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    params = data.setdefault("strategy", {}).setdefault("params", {})

    if "opening_range_minutes" in payload:
        params["opening_range_minutes"] = int(payload["opening_range_minutes"])
    if "or_atr_min" in payload:
        params["or_atr_min"] = float(payload["or_atr_min"])
    if "or_atr_max" in payload:
        params["or_atr_max"] = float(payload["or_atr_max"])
    if "atr_lookback" in payload:
        params["atr_lookback"] = int(payload["atr_lookback"])
    if "capital" in payload:
        data["signal_capital"] = float(payload["capital"])
    if "risk_per_trade" in payload:
        params["risk_per_trade"] = float(payload["risk_per_trade"])
    if "profit_target_r" in payload:
        params["profit_target_r"] = float(payload["profit_target_r"])
    if "breakeven_r" in payload:
        params["breakeven_r"] = float(payload["breakeven_r"])
    if "entry_cutoff_time" in payload:
        params["entry_cutoff_time"] = str(payload["entry_cutoff_time"])
    if "flatten_time" in payload:
        params["flatten_time"] = str(payload["flatten_time"])

    CONFIG_FILE.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return {"status": "ok", "config": data}


@app.get("/api/stats")
def get_stats() -> dict[str, Any]:
    return compute_dashboard_analytics()


@app.get("/api/status")
def get_status() -> dict[str, Any]:
    return runner.get_status()


@app.post("/api/strategy/start")
def start_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    started = runner.start(payload)
    return {"status": "started" if started else "already_running", "state": runner.get_status()}


@app.post("/api/strategy/stop")
def stop_strategy() -> dict[str, Any]:
    runner.stop()
    return {"status": "stopped", "state": runner.get_status()}


@app.post("/api/strategy/reset")
def reset_strategy() -> dict[str, Any]:
    runner.reset()
    return {"status": "reset", "state": runner.get_status()}


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    global main_loop
    if main_loop is None:
        main_loop = asyncio.get_running_loop()
    await websocket.accept()
    connected_clients.append(websocket)
    # Send current state immediately
    await websocket.send_json({"type": "init", "data": runner.get_status()})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# Mount static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


def run_dashboard(host: str = "0.0.0.0", port: int = 8060) -> None:
    uvicorn.run("dashboard.server:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    run_dashboard()
