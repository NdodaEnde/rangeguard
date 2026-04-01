"""
Zone engine — defines spatial zones on camera views and detects zone transitions.
Each camera view has polygon regions mapped to named zones (range, short_game, transition).
"""

import time
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from loguru import logger

from src.tracking.tracker import Track


class ZoneType(str, Enum):
    RANGE = "range"
    SHORT_GAME = "short_game"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


@dataclass
class ZoneEvent:
    """Records a person entering or exiting a zone."""
    person_id: int          # Global person ID (from Re-ID)
    local_track_id: int     # Camera-local track ID
    camera_id: str
    zone: str
    event_type: str         # "enter" or "exit"
    timestamp: float
    position: tuple[float, float]  # Center point when event occurred


@dataclass
class ZoneDefinition:
    """A named zone defined by a polygon on a camera view."""
    name: str
    zone_type: ZoneType
    camera_id: str
    polygon: np.ndarray     # Polygon vertices in pixel coordinates
    color: tuple[int, int, int] = (0, 255, 0)

    def contains(self, point: tuple[float, float]) -> bool:
        """Check if a point (x, y) is inside this zone polygon."""
        result = cv2.pointPolygonTest(
            self.polygon.astype(np.float32),
            (float(point[0]), float(point[1])),
            measureDist=False,
        )
        return result >= 0

    def draw_on(self, frame: np.ndarray, alpha: float = 0.2) -> np.ndarray:
        """Draw this zone as a semi-transparent overlay on a frame."""
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.polygon.astype(np.int32)], self.color)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.polylines(frame, [self.polygon.astype(np.int32)], True, self.color, 2)
        cv2.putText(
            frame, self.name,
            tuple(self.polygon[0].astype(int)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color, 2,
        )
        return frame


class ZoneEngine:
    """
    Manages zone definitions and tracks person-zone relationships.
    Emits ZoneEvents when people enter or exit zones.
    """

    def __init__(self):
        self._zones: dict[str, list[ZoneDefinition]] = {}  # camera_id -> zones
        self._person_zones: dict[int, str] = {}            # track_id -> current zone name
        self._events: list[ZoneEvent] = []
        self._max_events = 10000

    def add_zone(self, zone: ZoneDefinition):
        """Register a zone definition for a camera."""
        if zone.camera_id not in self._zones:
            self._zones[zone.camera_id] = []
        self._zones[zone.camera_id].append(zone)
        logger.info(f"Zone added: {zone.name} on {zone.camera_id}")

    def add_zone_from_normalized(
        self, name: str, zone_type: ZoneType, camera_id: str,
        normalized_polygon: list[list[float]], frame_size: tuple[int, int],
        color: tuple[int, int, int] = (0, 255, 0),
    ):
        """
        Add a zone using normalized (0-1) coordinates.
        Converts to pixel coordinates based on frame_size (width, height).
        """
        w, h = frame_size
        pixel_coords = np.array([[p[0] * w, p[1] * h] for p in normalized_polygon])
        zone = ZoneDefinition(
            name=name,
            zone_type=ZoneType(zone_type),
            camera_id=camera_id,
            polygon=pixel_coords,
            color=color,
        )
        self.add_zone(zone)

    def get_zone_for_point(self, camera_id: str, point: tuple[float, float]) -> str | None:
        """Determine which zone a point falls in for a given camera."""
        zones = self._zones.get(camera_id, [])
        for zone in zones:
            if zone.contains(point):
                return zone.name
        return None

    def update(self, camera_id: str, tracks: list[Track],
               global_id_map: dict[int, int] | None = None) -> list[ZoneEvent]:
        """
        Check all tracked people against zones and emit enter/exit events.

        Args:
            camera_id: Which camera these tracks are from
            tracks: Current confirmed tracks
            global_id_map: Optional mapping from local track_id -> global person_id

        Returns:
            List of new ZoneEvents generated this update
        """
        now = time.time()
        new_events = []
        zones = self._zones.get(camera_id, [])

        if not zones:
            return new_events

        current_track_ids = set()

        for track in tracks:
            # Use global ID if available, otherwise local track ID
            person_id = (global_id_map or {}).get(track.track_id, track.track_id)
            tracking_key = (camera_id, track.track_id)
            current_track_ids.add(tracking_key)

            center = track.center
            current_zone = self.get_zone_for_point(camera_id, center)
            previous_zone = self._person_zones.get(tracking_key)

            if current_zone != previous_zone:
                # Zone transition detected
                if previous_zone is not None:
                    exit_event = ZoneEvent(
                        person_id=person_id,
                        local_track_id=track.track_id,
                        camera_id=camera_id,
                        zone=previous_zone,
                        event_type="exit",
                        timestamp=now,
                        position=center,
                    )
                    new_events.append(exit_event)
                    self._events.append(exit_event)

                if current_zone is not None:
                    enter_event = ZoneEvent(
                        person_id=person_id,
                        local_track_id=track.track_id,
                        camera_id=camera_id,
                        zone=current_zone,
                        event_type="enter",
                        timestamp=now,
                        position=center,
                    )
                    new_events.append(enter_event)
                    self._events.append(enter_event)

                self._person_zones[tracking_key] = current_zone

        # Clean up tracks that are no longer active
        stale_keys = [
            k for k in self._person_zones
            if k[0] == camera_id and k not in current_track_ids
        ]
        for key in stale_keys:
            del self._person_zones[key]

        # Trim event history
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        return new_events

    def get_events(self, person_id: int | None = None,
                   zone: str | None = None,
                   since: float | None = None) -> list[ZoneEvent]:
        """Query zone events with optional filters."""
        events = self._events
        if person_id is not None:
            events = [e for e in events if e.person_id == person_id]
        if zone is not None:
            events = [e for e in events if e.zone == zone]
        if since is not None:
            events = [e for e in events if e.timestamp >= since]
        return events

    def get_zone_occupancy(self, camera_id: str | None = None) -> dict[str, int]:
        """Count how many people are currently in each zone."""
        occupancy: dict[str, int] = {}
        for key, zone_name in self._person_zones.items():
            if zone_name is None:
                continue
            if camera_id and key[0] != camera_id:
                continue
            occupancy[zone_name] = occupancy.get(zone_name, 0) + 1
        return occupancy

    def draw_zones(self, frame: np.ndarray, camera_id: str) -> np.ndarray:
        """Draw all zones for a camera onto a frame."""
        for zone in self._zones.get(camera_id, []):
            frame = zone.draw_on(frame)
        return frame
