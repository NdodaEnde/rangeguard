"""
Multi-object tracker using a simplified ByteTrack-style approach.
Tracks people within a single camera view using IoU + Kalman filtering.
"""

import time
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from src.detection.detector import Detection


@dataclass
class Track:
    """A tracked person within a single camera."""
    track_id: int
    bbox: np.ndarray              # Current [x1, y1, x2, y2]
    confidence: float
    camera_id: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    age: int = 0                  # Frames since creation
    hits: int = 1                 # Total successful associations
    misses: int = 0               # Consecutive frames without association
    state: str = "tentative"      # tentative | confirmed | lost

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def duration(self) -> float:
        """Seconds since first seen."""
        return self.last_seen - self.first_seen


def iou(bbox_a: np.ndarray, bbox_b: np.ndarray) -> float:
    """Compute IoU between two bounding boxes [x1,y1,x2,y2]."""
    x1 = max(bbox_a[0], bbox_b[0])
    y1 = max(bbox_a[1], bbox_b[1])
    x2 = min(bbox_a[2], bbox_b[2])
    y2 = min(bbox_a[3], bbox_b[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
    area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0


def iou_cost_matrix(tracks: list[Track], detections: list[Detection]) -> np.ndarray:
    """Build cost matrix based on 1 - IoU."""
    cost = np.zeros((len(tracks), len(detections)))
    for i, track in enumerate(tracks):
        for j, det in enumerate(detections):
            cost[i, j] = 1 - iou(track.bbox, det.bbox)
    return cost


class PersonTracker:
    """
    Single-camera multi-person tracker.

    Uses IoU-based association with the Hungarian algorithm.
    Manages track lifecycle: tentative -> confirmed -> lost.
    """

    def __init__(self, camera_id: str, max_age: int = 30, min_hits: int = 3,
                 iou_threshold: float = 0.3):
        self.camera_id = camera_id
        self.max_age = max_age          # Max missed frames before removal
        self.min_hits = min_hits        # Min hits to confirm a track
        self.iou_threshold = iou_threshold
        self._tracks: list[Track] = []
        self._next_id = 1

    @property
    def tracks(self) -> list[Track]:
        """Return confirmed tracks only."""
        return [t for t in self._tracks if t.state == "confirmed"]

    @property
    def all_tracks(self) -> list[Track]:
        return list(self._tracks)

    def update(self, detections: list[Detection]) -> list[Track]:
        """
        Update tracks with new detections.

        Args:
            detections: Person detections from current frame

        Returns:
            List of confirmed tracks after update
        """
        now = time.time()

        if not self._tracks:
            # No existing tracks — create new ones from all detections
            for det in detections:
                self._create_track(det, now)
            return self.tracks

        if not detections:
            # No detections — age all tracks
            self._age_tracks()
            return self.tracks

        # Build cost matrix and solve assignment
        cost = iou_cost_matrix(self._tracks, detections)
        row_indices, col_indices = linear_sum_assignment(cost)

        matched_tracks = set()
        matched_dets = set()

        for row, col in zip(row_indices, col_indices):
            if cost[row, col] > (1 - self.iou_threshold):
                continue  # IoU too low — not a valid match

            track = self._tracks[row]
            det = detections[col]

            # Update track with matched detection
            track.bbox = det.bbox
            track.confidence = det.confidence
            track.last_seen = now
            track.hits += 1
            track.misses = 0
            track.age += 1

            if track.state == "tentative" and track.hits >= self.min_hits:
                track.state = "confirmed"

            matched_tracks.add(row)
            matched_dets.add(col)

        # Handle unmatched tracks (missed detections)
        for i, track in enumerate(self._tracks):
            if i not in matched_tracks:
                track.misses += 1
                track.age += 1
                if track.misses > self.max_age:
                    track.state = "lost"

        # Handle unmatched detections (new people)
        for j, det in enumerate(detections):
            if j not in matched_dets:
                self._create_track(det, now)

        # Remove lost tracks
        self._tracks = [t for t in self._tracks if t.state != "lost"]

        return self.tracks

    def _create_track(self, detection: Detection, timestamp: float):
        """Create a new track from a detection."""
        track = Track(
            track_id=self._next_id,
            bbox=detection.bbox.copy(),
            confidence=detection.confidence,
            camera_id=self.camera_id,
            first_seen=timestamp,
            last_seen=timestamp,
        )
        if track.hits >= self.min_hits:
            track.state = "confirmed"
        self._tracks.append(track)
        self._next_id += 1

    def _age_tracks(self):
        """Age all tracks when no detections arrive."""
        for track in self._tracks:
            track.misses += 1
            track.age += 1
            if track.misses > self.max_age:
                track.state = "lost"
        self._tracks = [t for t in self._tracks if t.state != "lost"]

    def get_track(self, track_id: int) -> Track | None:
        """Get a track by ID."""
        for track in self._tracks:
            if track.track_id == track_id:
                return track
        return None
