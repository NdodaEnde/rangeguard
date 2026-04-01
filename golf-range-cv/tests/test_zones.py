"""Tests for the zone engine module."""

import time

import numpy as np
import pytest

from src.tracking.tracker import Track
from src.zones.zone_engine import ZoneDefinition, ZoneEngine, ZoneType


class TestZoneDefinition:
    """Test zone polygon operations."""

    def _make_square_zone(self):
        return ZoneDefinition(
            name="Test Zone",
            zone_type=ZoneType.RANGE,
            camera_id="cam1",
            polygon=np.array([[100, 100], [300, 100], [300, 300], [100, 300]]),
        )

    def test_point_inside_zone(self):
        zone = self._make_square_zone()
        assert zone.contains((200, 200)) is True

    def test_point_outside_zone(self):
        zone = self._make_square_zone()
        assert zone.contains((50, 50)) is False

    def test_point_on_edge_is_inside(self):
        zone = self._make_square_zone()
        assert zone.contains((100, 200)) is True

    def test_point_at_corner_is_inside(self):
        zone = self._make_square_zone()
        assert zone.contains((100, 100)) is True


class TestZoneEngine:
    """Test zone engine tracking and events."""

    def _make_track(self, track_id, cx, cy, camera_id="cam1"):
        half_w, half_h = 25, 50
        return Track(
            track_id=track_id,
            bbox=np.array([cx - half_w, cy - half_h,
                           cx + half_w, cy + half_h], dtype=float),
            confidence=0.9,
            camera_id=camera_id,
        )

    def _setup_engine(self):
        engine = ZoneEngine()
        engine.add_zone(ZoneDefinition(
            name="Driving Range",
            zone_type=ZoneType.RANGE,
            camera_id="cam1",
            polygon=np.array([[0, 0], [500, 0], [500, 400], [0, 400]]),
        ))
        engine.add_zone(ZoneDefinition(
            name="Short Game Area",
            zone_type=ZoneType.SHORT_GAME,
            camera_id="cam2",
            polygon=np.array([[0, 0], [400, 0], [400, 300], [0, 300]]),
        ))
        return engine

    def test_get_zone_for_point_inside(self):
        engine = self._setup_engine()
        zone = engine.get_zone_for_point("cam1", (250, 200))
        assert zone == "Driving Range"

    def test_get_zone_for_point_outside(self):
        engine = self._setup_engine()
        zone = engine.get_zone_for_point("cam1", (600, 600))
        assert zone is None

    def test_get_zone_for_unknown_camera(self):
        engine = self._setup_engine()
        zone = engine.get_zone_for_point("cam_unknown", (100, 100))
        assert zone is None

    def test_enter_event_on_first_detection(self):
        engine = self._setup_engine()
        track = self._make_track(1, 250, 200, "cam1")
        events = engine.update("cam1", [track])

        assert len(events) == 1
        assert events[0].event_type == "enter"
        assert events[0].zone == "Driving Range"
        assert events[0].local_track_id == 1

    def test_no_event_when_staying_in_same_zone(self):
        engine = self._setup_engine()
        track = self._make_track(1, 250, 200, "cam1")

        engine.update("cam1", [track])  # First enter
        events = engine.update("cam1", [track])  # Same position

        assert len(events) == 0

    def test_zone_occupancy_count(self):
        engine = self._setup_engine()
        tracks = [
            self._make_track(1, 100, 100, "cam1"),
            self._make_track(2, 200, 100, "cam1"),
        ]
        engine.update("cam1", tracks)

        occupancy = engine.get_zone_occupancy()
        assert occupancy.get("Driving Range") == 2

    def test_add_zone_from_normalized(self):
        engine = ZoneEngine()
        engine.add_zone_from_normalized(
            name="Test",
            zone_type="range",
            camera_id="cam1",
            normalized_polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            frame_size=(1920, 1080),
        )
        zone = engine.get_zone_for_point("cam1", (960, 540))
        assert zone == "Test"

    def test_event_query_filters(self):
        engine = self._setup_engine()
        track = self._make_track(1, 250, 200, "cam1")
        engine.update("cam1", [track])

        # Query by person_id
        events = engine.get_events(person_id=1)
        assert len(events) == 1

        # Query non-existent person
        events = engine.get_events(person_id=999)
        assert len(events) == 0

    def test_stale_tracks_cleaned_up(self):
        engine = self._setup_engine()
        track = self._make_track(1, 250, 200, "cam1")

        engine.update("cam1", [track])
        assert engine.get_zone_occupancy().get("Driving Range") == 1

        # Track disappears
        engine.update("cam1", [])
        assert engine.get_zone_occupancy().get("Driving Range", 0) == 0
