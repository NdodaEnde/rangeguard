"""Tests for the person detection module."""

import numpy as np
import pytest

from src.detection.detector import Detection


class TestDetection:
    """Test the Detection dataclass."""

    def test_center_calculation(self):
        det = Detection(bbox=np.array([100, 200, 300, 400]), confidence=0.9)
        cx, cy = det.center
        assert cx == 200.0
        assert cy == 300.0

    def test_width_height(self):
        det = Detection(bbox=np.array([10, 20, 50, 80]), confidence=0.8)
        assert det.width == 40.0
        assert det.height == 60.0

    def test_area(self):
        det = Detection(bbox=np.array([0, 0, 100, 200]), confidence=0.7)
        assert det.area == 20000.0

    def test_crop_from_frame(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:200, 50:150] = 255  # White region

        det = Detection(bbox=np.array([50, 100, 150, 200]), confidence=0.9)
        crop = det.crop_from(frame)

        assert crop.shape == (100, 100, 3)
        assert np.all(crop == 255)

    def test_crop_clamps_to_frame_bounds(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        det = Detection(bbox=np.array([-10, -10, 110, 110]), confidence=0.9)
        crop = det.crop_from(frame)

        assert crop.shape == (100, 100, 3)

    def test_default_class_id_is_person(self):
        det = Detection(bbox=np.array([0, 0, 1, 1]), confidence=0.5)
        assert det.class_id == 0


class TestPersonDetector:
    """Test PersonDetector initialization (without loading model)."""

    def test_lazy_model_not_loaded_on_init(self):
        from src.detection.detector import PersonDetector
        detector = PersonDetector(model_path="yolov8n.pt", confidence=0.6)
        assert detector._model is None
        assert detector.confidence == 0.6
