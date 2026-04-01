"""
Database models and Pydantic schemas for the API.
"""

from pydantic import BaseModel


# --- API Response Schemas ---

class ZoneOccupancy(BaseModel):
    zone: str
    count: int


class PersonInfo(BaseModel):
    global_id: int
    current_zone: str | None
    last_camera: str
    first_seen: float
    last_seen: float
    duration_seconds: float


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    person_id: int
    message: str
    timestamp: float
    camera_id: str | None
    zone_path: list[str]
    acknowledged: bool


class SystemStatus(BaseModel):
    cameras_online: int
    cameras_total: int
    persons_tracked: int
    active_alerts: int
    total_alerts_today: int
    zone_occupancy: list[ZoneOccupancy]
    uptime_seconds: float


class CameraInfo(BaseModel):
    id: str
    name: str
    zone: str
    is_online: bool


class ZoneEventResponse(BaseModel):
    person_id: int
    camera_id: str
    zone: str
    event_type: str
    timestamp: float


class DashboardData(BaseModel):
    status: SystemStatus
    recent_alerts: list[AlertResponse]
    persons: list[PersonInfo]
    cameras: list[CameraInfo]
