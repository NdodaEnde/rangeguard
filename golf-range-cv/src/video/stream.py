"""
RTSP/video stream handler with automatic reconnection and frame buffering.
Supports RTSP cameras, video files, and webcams for development.
"""

import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from loguru import logger


@dataclass
class CameraConfig:
    id: str
    name: str
    source: str  # RTSP URL, file path, or device index
    zone: str
    fps: int = 15
    resolution: tuple[int, int] = (1920, 1080)


@dataclass
class Frame:
    image: np.ndarray
    camera_id: str
    timestamp: float
    frame_number: int


class VideoStream:
    """Handles a single camera stream with reconnection logic."""

    def __init__(self, config: CameraConfig):
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[Frame] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._reconnect_delay = 2  # seconds
        self._max_reconnect_delay = 30

    def start(self) -> "VideoStream":
        """Start the stream reader thread."""
        if self._running:
            return self
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info(f"[{self.config.id}] Stream started: {self.config.name}")
        return self

    def stop(self):
        """Stop the stream reader thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()
        logger.info(f"[{self.config.id}] Stream stopped")

    def read(self) -> Optional[Frame]:
        """Get the latest frame (non-blocking)."""
        with self._lock:
            return self._frame

    @property
    def is_running(self) -> bool:
        return self._running

    def _connect(self) -> bool:
        """Attempt to connect to the video source."""
        try:
            # Handle different source types
            source = self.config.source
            if source.isdigit():
                source = int(source)  # Webcam index

            self._cap = cv2.VideoCapture(source)

            if isinstance(source, str) and source.startswith("rtsp"):
                # Optimize for RTSP: use TCP, reduce buffer
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self._cap.isOpened():
                logger.warning(f"[{self.config.id}] Failed to open: {self.config.source}")
                return False

            logger.info(f"[{self.config.id}] Connected to: {self.config.source}")
            return True

        except Exception as e:
            logger.error(f"[{self.config.id}] Connection error: {e}")
            return False

    def _read_loop(self):
        """Main loop: read frames, handle reconnection."""
        delay = self._reconnect_delay

        while self._running:
            # Connect if needed
            if self._cap is None or not self._cap.isOpened():
                if not self._connect():
                    time.sleep(delay)
                    delay = min(delay * 2, self._max_reconnect_delay)
                    continue
                delay = self._reconnect_delay  # Reset on success

            ret, image = self._cap.read()

            if not ret:
                logger.warning(f"[{self.config.id}] Frame read failed, reconnecting...")
                self._cap.release()
                self._cap = None
                continue

            self._frame_count += 1

            # Build frame object
            frame = Frame(
                image=image,
                camera_id=self.config.id,
                timestamp=time.time(),
                frame_number=self._frame_count,
            )

            with self._lock:
                self._frame = frame

            # Throttle to target FPS
            time.sleep(1.0 / self.config.fps)


class StreamManager:
    """Manages multiple camera streams."""

    def __init__(self):
        self._streams: dict[str, VideoStream] = {}

    def add_camera(self, config: CameraConfig) -> VideoStream:
        """Add and start a camera stream."""
        stream = VideoStream(config)
        self._streams[config.id] = stream
        return stream

    def start_all(self):
        """Start all registered streams."""
        for stream in self._streams.values():
            stream.start()
        logger.info(f"Started {len(self._streams)} camera streams")

    def stop_all(self):
        """Stop all streams."""
        for stream in self._streams.values():
            stream.stop()

    def get_frames(self) -> dict[str, Optional[Frame]]:
        """Get latest frame from each camera."""
        return {cam_id: stream.read() for cam_id, stream in self._streams.items()}

    def get_stream(self, camera_id: str) -> Optional[VideoStream]:
        return self._streams.get(camera_id)

    @property
    def camera_ids(self) -> list[str]:
        return list(self._streams.keys())
