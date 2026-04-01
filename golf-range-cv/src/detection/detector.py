"""
Person detection using YOLOv8.
Wraps ultralytics for clean integration with the tracking pipeline.
"""

from dataclasses import dataclass

import numpy as np
from loguru import logger


@dataclass
class Detection:
    """A single person detection."""
    bbox: np.ndarray       # [x1, y1, x2, y2] in pixels
    confidence: float
    class_id: int = 0      # 0 = person in COCO

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> float:
        return self.width * self.height

    def crop_from(self, image: np.ndarray) -> np.ndarray:
        """Extract the person crop from a frame."""
        x1, y1, x2, y2 = self.bbox.astype(int)
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        return image[y1:y2, x1:x2]


class PersonDetector:
    """YOLOv8-based person detector."""

    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.5,
                 device: str = "auto"):
        self.confidence = confidence
        self.model_path = model_path
        self._model = None
        self._device = device

    def _load_model(self):
        """Lazy-load the YOLO model."""
        from ultralytics import YOLO
        self._model = YOLO(self.model_path)
        logger.info(f"Loaded YOLOv8 model: {self.model_path}")

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Detect people in a frame.

        Args:
            frame: BGR image as numpy array

        Returns:
            List of Detection objects for people found in the frame
        """
        if self._model is None:
            self._load_model()

        # Run inference — only detect persons (class 0)
        results = self._model(
            frame,
            conf=self.confidence,
            classes=[0],  # person only
            verbose=False,
            device=self._device if self._device != "auto" else None,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu())
                cls = int(boxes.cls[i].cpu())

                detections.append(Detection(
                    bbox=bbox,
                    confidence=conf,
                    class_id=cls,
                ))

        return detections

    def detect_batch(self, frames: list[np.ndarray]) -> list[list[Detection]]:
        """Detect people in multiple frames (batched inference)."""
        if self._model is None:
            self._load_model()

        results = self._model(
            frames,
            conf=self.confidence,
            classes=[0],
            verbose=False,
            device=self._device if self._device != "auto" else None,
        )

        all_detections = []
        for result in results:
            detections = []
            boxes = result.boxes
            if boxes is not None:
                for i in range(len(boxes)):
                    bbox = boxes.xyxy[i].cpu().numpy()
                    conf = float(boxes.conf[i].cpu())
                    cls = int(boxes.cls[i].cpu())
                    detections.append(Detection(bbox=bbox, confidence=conf, class_id=cls))
            all_detections.append(detections)

        return all_detections
