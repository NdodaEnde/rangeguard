"""
Main processing pipeline — ties together all modules.

Stream → Detect → Track → Re-ID → Zone Check → Rule Engine → Alerts
"""

import threading
import time

import cv2
import numpy as np
import yaml
from loguru import logger

from src.alerts.alert_manager import AlertManager
from src.detection.detector import PersonDetector
from src.reid.person_reid import PersonReID
from src.rules.rule_engine import RuleEngine
from src.tracking.tracker import PersonTracker
from src.video.stream import CameraConfig, StreamManager
from src.zones.zone_engine import ZoneEngine


class Pipeline:
    """
    Main CV pipeline orchestrating all components.

    Flow per frame:
    1. Grab frames from all cameras
    2. Detect people in each frame (YOLOv8)
    3. Track people within each camera (ByteTrack)
    4. Re-identify people across cameras (OSNet)
    5. Check zone transitions
    6. Evaluate rules for suspicious behavior
    7. Dispatch alerts
    """

    def __init__(self, config_path: str = "config/default.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Initialize components
        self.stream_manager = StreamManager()
        self.detector = PersonDetector(
            model_path=self.config["detection"]["model"],
            confidence=self.config["detection"]["confidence"],
            device=self.config["detection"]["device"],
        )
        self.zone_engine = ZoneEngine()
        self.reid = PersonReID(
            model_name=self.config["reid"]["model"],
            match_threshold=self.config["reid"]["match_threshold"],
            gallery_ttl=self.config["reid"]["gallery_ttl"],
        )
        self.rule_engine = RuleEngine(
            time_window=self.config["rules"]["cross_zone_alert"]["time_window"],
            min_dwell_time=self.config["rules"]["cross_zone_alert"]["min_dwell_time"],
            cooldown=self.config["rules"]["cross_zone_alert"]["cooldown"],
        )
        self.alert_manager = AlertManager(
            log_file=self.config["alerts"].get("log_file", "alerts.log"),
        )

        # Per-camera trackers
        self._trackers: dict[str, PersonTracker] = {}
        self._running = False
        self._process_thread: threading.Thread | None = None

        # Wire up alert callback
        self.rule_engine.on_alert(self.alert_manager.handle_alert)

    def setup_cameras(self):
        """Configure cameras from config file."""
        for cam_cfg in self.config["cameras"]:
            config = CameraConfig(
                id=cam_cfg["id"],
                name=cam_cfg["name"],
                source=cam_cfg["source"],
                zone=cam_cfg["zone"],
                fps=cam_cfg.get("fps", 15),
                resolution=tuple(cam_cfg.get("resolution", [1920, 1080])),
            )
            self.stream_manager.add_camera(config)

            # Create tracker for this camera
            self._trackers[config.id] = PersonTracker(
                camera_id=config.id,
                max_age=self.config["tracking"]["max_age"],
                min_hits=self.config["tracking"]["min_hits"],
                iou_threshold=self.config["tracking"]["iou_threshold"],
            )

            logger.info(f"Camera configured: {config.name} ({config.id})")

    def setup_zones(self):
        """Configure zones from config file."""
        zone_maps = self.config.get("zone_maps", {})

        for cam_id, zones in zone_maps.items():
            cam_cfg = next(
                (c for c in self.config["cameras"] if c["id"] == cam_id),
                None,
            )
            if cam_cfg is None:
                continue

            frame_size = tuple(cam_cfg.get("resolution", [1920, 1080]))

            for zone_name, polygon in zones.items():
                zone_config = self.config["zones"].get(zone_name, {})
                color = tuple(zone_config.get("color", [0, 255, 0]))
                display_name = zone_config.get("name", zone_name)

                self.zone_engine.add_zone_from_normalized(
                    name=display_name,
                    zone_type=zone_name,
                    camera_id=cam_id,
                    normalized_polygon=polygon,
                    frame_size=frame_size,
                    color=color,
                )

    def start(self):
        """Start the pipeline."""
        self.setup_cameras()
        self.setup_zones()
        self.stream_manager.start_all()

        self._running = True
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

        logger.info("Pipeline started")

    def stop(self):
        """Stop the pipeline."""
        self._running = False
        if self._process_thread:
            self._process_thread.join(timeout=10)
        self.stream_manager.stop_all()
        logger.info("Pipeline stopped")

    def _process_loop(self):
        """Main processing loop — runs in a background thread."""
        cleanup_interval = 60  # seconds
        last_cleanup = time.time()

        while self._running:
            try:
                self._process_frame()

                # Periodic cleanup
                now = time.time()
                if now - last_cleanup > cleanup_interval:
                    self.reid.cleanup_stale()
                    last_cleanup = now

            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                time.sleep(0.1)

    def _process_frame(self):
        """Process one frame from each camera."""
        frames = self.stream_manager.get_frames()

        for cam_id, frame in frames.items():
            if frame is None:
                continue

            image = frame.image

            # 1. Detect people
            detections = self.detector.detect(image)

            # 2. Track within this camera
            tracker = self._trackers.get(cam_id)
            if tracker is None:
                continue
            tracks = tracker.update(detections)

            if not tracks:
                continue

            # 3. Re-ID across cameras
            id_map = self.reid.process_tracks(cam_id, tracks, image)

            # 4. Update zones
            zone_events = self.zone_engine.update(cam_id, tracks, id_map)

            # 5. Run rules on zone events
            if zone_events:
                self.rule_engine.process_zone_events(zone_events)

    def get_annotated_frame(self, camera_id: str) -> np.ndarray | None:
        """
        Get a frame with detection overlays drawn on it.
        Useful for the dashboard live view.
        """
        stream = self.stream_manager.get_stream(camera_id)
        if stream is None:
            return None

        frame = stream.read()
        if frame is None:
            return None

        image = frame.image.copy()

        # Draw zones
        image = self.zone_engine.draw_zones(image, camera_id)

        # Draw tracked persons
        tracker = self._trackers.get(camera_id)
        if tracker:
            for track in tracker.tracks:
                x1, y1, x2, y2 = track.bbox.astype(int)
                color = (0, 255, 0) if track.state == "confirmed" else (0, 255, 255)
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

                label = f"ID:{track.track_id}"
                cv2.putText(
                    image, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                )

        return image


def create_pipeline(config_path: str = "config/default.yaml") -> Pipeline:
    """Factory function to create and configure a pipeline."""
    pipeline = Pipeline(config_path)
    return pipeline
