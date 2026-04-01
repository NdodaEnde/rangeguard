"""Tests for the multi-object tracking module."""

import numpy as np
import pytest

from src.detection.detector import Detection
from src.tracking.tracker import PersonTracker, Track, iou


class TestIoU:
    """Test IoU calculation."""

    def test_perfect_overlap(self):
        box = np.array([0, 0, 100, 100])
        assert iou(box, box) == 1.0

    def test_no_overlap(self):
        a = np.array([0, 0, 50, 50])
        b = np.array([100, 100, 200, 200])
        assert iou(a, b) == 0.0

    def test_partial_overlap(self):
        a = np.array([0, 0, 100, 100])
        b = np.array([50, 50, 150, 150])
        # Intersection: 50x50 = 2500
        # Union: 10000 + 10000 - 2500 = 17500
        result = iou(a, b)
        assert abs(result - 2500 / 17500) < 1e-6

    def test_one_inside_other(self):
        outer = np.array([0, 0, 200, 200])
        inner = np.array([50, 50, 100, 100])
        # Intersection = inner area = 2500
        # Union = 40000 + 2500 - 2500 = 40000
        result = iou(outer, inner)
        assert abs(result - 2500 / 40000) < 1e-6


class TestPersonTracker:
    """Test the single-camera tracker."""

    def _make_detection(self, x1, y1, x2, y2, conf=0.9):
        return Detection(bbox=np.array([x1, y1, x2, y2], dtype=float),
                         confidence=conf)

    def test_first_detections_create_tracks(self):
        tracker = PersonTracker(camera_id="cam1", min_hits=1)
        dets = [self._make_detection(10, 10, 50, 50)]
        tracks = tracker.update(dets)

        assert len(tracks) == 1
        assert tracks[0].camera_id == "cam1"

    def test_consistent_detection_confirms_track(self):
        tracker = PersonTracker(camera_id="cam1", min_hits=3)

        det = self._make_detection(100, 100, 200, 200)
        for _ in range(3):
            tracks = tracker.update([det])

        assert len(tracks) == 1
        assert tracks[0].state == "confirmed"
        assert tracks[0].hits == 3

    def test_track_id_persists_across_frames(self):
        tracker = PersonTracker(camera_id="cam1", min_hits=1)

        det1 = self._make_detection(100, 100, 200, 200)
        tracks1 = tracker.update([det1])
        tid = tracks1[0].track_id

        # Same location next frame
        det2 = self._make_detection(105, 105, 205, 205)
        tracks2 = tracker.update([det2])

        assert len(tracks2) == 1
        assert tracks2[0].track_id == tid

    def test_multiple_people_tracked_separately(self):
        tracker = PersonTracker(camera_id="cam1", min_hits=1)

        dets = [
            self._make_detection(0, 0, 50, 50),
            self._make_detection(400, 400, 500, 500),
        ]
        tracks = tracker.update(dets)

        assert len(tracks) == 2
        assert tracks[0].track_id != tracks[1].track_id

    def test_lost_track_removed_after_max_age(self):
        tracker = PersonTracker(camera_id="cam1", min_hits=1, max_age=3)

        det = self._make_detection(100, 100, 200, 200)
        tracker.update([det])

        # No detections for max_age + 1 frames
        for _ in range(4):
            tracker.update([])

        assert len(tracker.tracks) == 0

    def test_no_detections_returns_empty(self):
        tracker = PersonTracker(camera_id="cam1")
        tracks = tracker.update([])
        assert len(tracks) == 0

    def test_get_track_by_id(self):
        tracker = PersonTracker(camera_id="cam1", min_hits=1)
        det = self._make_detection(10, 10, 50, 50)
        tracks = tracker.update([det])

        found = tracker.get_track(tracks[0].track_id)
        assert found is not None
        assert found.track_id == tracks[0].track_id

    def test_get_nonexistent_track_returns_none(self):
        tracker = PersonTracker(camera_id="cam1")
        assert tracker.get_track(999) is None
