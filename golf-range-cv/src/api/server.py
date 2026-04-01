"""
FastAPI server — REST API + WebSocket for the dashboard.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.models import (
    AlertResponse, CameraInfo, DashboardData, PersonInfo,
    SystemStatus, ZoneOccupancy,
)

# These will be injected by the main pipeline
_pipeline = None
_start_time = time.time()


def set_pipeline(pipeline):
    """Inject the running pipeline for API access."""
    global _pipeline
    _pipeline = pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("API server starting")
    yield
    logger.info("API server shutting down")


app = FastAPI(
    title="Golf Range CV — Revenue Protection System",
    description="Computer vision-powered monitoring for golf range revenue leakage prevention",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configured per deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST Endpoints ---

@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get current system status."""
    if _pipeline is None:
        return SystemStatus(
            cameras_online=0, cameras_total=0, persons_tracked=0,
            active_alerts=0, total_alerts_today=0, zone_occupancy=[],
            uptime_seconds=time.time() - _start_time,
        )

    occupancy = _pipeline.zone_engine.get_zone_occupancy()
    zone_list = [ZoneOccupancy(zone=z, count=c) for z, c in occupancy.items()]

    return SystemStatus(
        cameras_online=len(_pipeline.stream_manager.camera_ids),
        cameras_total=len(_pipeline.stream_manager.camera_ids),
        persons_tracked=_pipeline.reid.gallery_size,
        active_alerts=_pipeline.rule_engine.active_alerts,
        total_alerts_today=_pipeline.rule_engine.total_alerts,
        zone_occupancy=zone_list,
        uptime_seconds=time.time() - _start_time,
    )


@app.get("/api/alerts", response_model=list[AlertResponse])
async def get_alerts(
    limit: int = 50,
    unacknowledged_only: bool = False,
    person_id: int | None = None,
):
    """Get alerts with optional filters."""
    if _pipeline is None:
        return []

    alerts = _pipeline.rule_engine.get_alerts(
        person_id=person_id,
        unacknowledged_only=unacknowledged_only,
    )
    return [
        AlertResponse(**a.to_dict())
        for a in alerts[-limit:]
    ]


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    if _pipeline is None:
        return JSONResponse({"error": "Pipeline not running"}, status_code=503)

    success = _pipeline.rule_engine.acknowledge_alert(alert_id)
    if success:
        return {"status": "acknowledged", "alert_id": alert_id}
    return JSONResponse({"error": "Alert not found"}, status_code=404)


@app.get("/api/persons", response_model=list[PersonInfo])
async def get_persons():
    """Get all currently tracked persons."""
    if _pipeline is None:
        return []

    now = time.time()
    persons = _pipeline.reid.get_all_persons()
    return [
        PersonInfo(
            global_id=p.global_id,
            current_zone=p.last_zone,
            last_camera=p.last_camera_id,
            first_seen=p.first_seen,
            last_seen=p.last_seen,
            duration_seconds=now - p.first_seen,
        )
        for p in persons
    ]


@app.get("/api/persons/{person_id}/history")
async def get_person_history(person_id: int):
    """Get movement history for a specific person."""
    if _pipeline is None:
        return JSONResponse({"error": "Pipeline not running"}, status_code=503)

    history = _pipeline.rule_engine.get_person_history(person_id)
    if history is None:
        return JSONResponse({"error": "Person not found"}, status_code=404)

    return {
        "person_id": person_id,
        "current_zone": history.current_zone,
        "zone_sequence": [
            {"zone": z, "timestamp": t}
            for z, t in history.zone_sequence
        ],
    }


@app.get("/api/cameras", response_model=list[CameraInfo])
async def get_cameras():
    """Get camera status."""
    if _pipeline is None:
        return []

    cameras = []
    for cam_id in _pipeline.stream_manager.camera_ids:
        stream = _pipeline.stream_manager.get_stream(cam_id)
        cameras.append(CameraInfo(
            id=cam_id,
            name=stream.config.name if stream else cam_id,
            zone=stream.config.zone if stream else "unknown",
            is_online=stream.is_running if stream else False,
        ))
    return cameras


@app.get("/api/zones/occupancy")
async def get_zone_occupancy():
    """Get current zone occupancy counts."""
    if _pipeline is None:
        return {}
    return _pipeline.zone_engine.get_zone_occupancy()


@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard():
    """Get all dashboard data in one call."""
    status = await get_status()
    alerts = await get_alerts(limit=20)
    persons = await get_persons()
    cameras = await get_cameras()
    return DashboardData(
        status=status,
        recent_alerts=alerts,
        persons=persons,
        cameras=cameras,
    )


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()

    if _pipeline:
        _pipeline.alert_manager.register_ws_client(websocket)

    try:
        # Send initial state
        dashboard = await get_dashboard()
        await websocket.send_json({
            "type": "init",
            "data": dashboard.model_dump(),
        })

        # Keep connection alive
        while True:
            # Wait for client messages (pings, acknowledgements)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if _pipeline:
            _pipeline.alert_manager.unregister_ws_client(websocket)
