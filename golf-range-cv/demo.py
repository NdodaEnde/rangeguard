"""
Demo script — simulates the full pipeline without real cameras.

Creates fake zone events to demonstrate the alert system and dashboard.
Run this to show the owner how the system works before installing cameras.

Usage:
    python demo.py
    Then open http://localhost:8000/dashboard
"""

import asyncio
import random
import sys
import threading
import time

import uvicorn
from loguru import logger

from src.alerts.alert_manager import AlertManager
from src.api import server
from src.api.models import SystemStatus, ZoneOccupancy
from src.rules.rule_engine import Alert, AlertSeverity, AlertType, RuleEngine
from src.zones.zone_engine import ZoneEvent


class DemoPipeline:
    """Simulated pipeline that generates realistic zone events."""

    def __init__(self):
        self.rule_engine = RuleEngine(
            time_window=1800,
            min_dwell_time=5,  # Short dwell for demo purposes
            cooldown=30,
        )
        self.alert_manager = AlertManager(log_file="demo_alerts.log")
        self.rule_engine.on_alert(self.alert_manager.handle_alert)

        # Simulated state
        self._persons: dict[int, dict] = {}
        self._running = False
        self._zone_occupancy = {"Driving Range": 0, "Short Game Area": 0, "Transition Path": 0}

        # Fake stream/reid for API compatibility
        self.stream_manager = type('obj', (object,), {
            'camera_ids': ['cam_range_1', 'cam_shortgame_1', 'cam_transition_1'],
            'get_stream': lambda self, x: type('obj', (object,), {
                'config': type('obj', (object,), {
                    'name': {'cam_range_1': 'Range Camera 1',
                             'cam_shortgame_1': 'Short Game Camera 1',
                             'cam_transition_1': 'Transition Camera 1'}[x],
                    'zone': {'cam_range_1': 'range',
                             'cam_shortgame_1': 'short_game',
                             'cam_transition_1': 'transition'}[x],
                })(),
                'is_running': True,
            })(),
        })()

        self.reid = type('obj', (object,), {
            'gallery_size': 0,
            'get_all_persons': lambda self: [],
        })()

        self._zone_counts = {"Driving Range": 0, "Short Game Area": 0}
        self.zone_engine = type('obj', (object,), {
            '_parent': self,
            'get_zone_occupancy': lambda self: self._parent._zone_counts,
        })()

    def start(self):
        self._running = True
        threading.Thread(target=self._simulate, daemon=True).start()
        logger.info("Demo simulation started")

    def stop(self):
        self._running = False

    def _simulate(self):
        """Generate realistic customer behavior patterns."""
        person_id = 0
        zones = ["Driving Range", "Short Game Area"]
        cameras = {"Driving Range": "cam_range_1", "Short Game Area": "cam_shortgame_1"}

        while self._running:
            # Every 10-20 seconds, simulate a new customer event
            time.sleep(random.uniform(8, 15))

            person_id += 1
            self.reid.gallery_size = person_id

            # 70% legitimate customers, 30% suspicious
            is_suspicious = random.random() < 0.3

            if is_suspicious:
                self._simulate_theft(person_id, cameras)
            else:
                self._simulate_normal(person_id, cameras)

    def _simulate_normal(self, person_id: int, cameras: dict):
        """Simulate a normal customer — stays in their paid zone."""
        zone = random.choice(["Driving Range", "Short Game Area"])
        camera = cameras[zone]

        logger.info(f"[DEMO] Person #{person_id}: Normal customer at {zone}")

        self._zone_counts[zone] = self._zone_counts.get(zone, 0) + 1

        event = ZoneEvent(
            person_id=person_id,
            local_track_id=person_id,
            camera_id=camera,
            zone=zone,
            event_type="enter",
            timestamp=time.time(),
            position=(random.uniform(100, 1800), random.uniform(300, 900)),
        )
        self.rule_engine.process_zone_events([event])

        # Customer leaves after a while (background)
        def leave_later(z, delay):
            time.sleep(delay)
            self._zone_counts[z] = max(0, self._zone_counts.get(z, 0) - 1)

        threading.Thread(
            target=leave_later,
            args=(zone, random.uniform(30, 90)),
            daemon=True,
        ).start()

    def _simulate_theft(self, person_id: int, cameras: dict):
        """Simulate the theft pattern: Range → Short Game → Range."""
        logger.info(f"[DEMO] Person #{person_id}: Simulating suspicious cross-zone movement")

        # Step 1: Enter range
        self._zone_counts["Driving Range"] = self._zone_counts.get("Driving Range", 0) + 1

        event1 = ZoneEvent(
            person_id=person_id,
            local_track_id=person_id,
            camera_id="cam_range_1",
            zone="Driving Range",
            event_type="enter",
            timestamp=time.time(),
            position=(500, 600),
        )
        self.rule_engine.process_zone_events([event1])

        # Step 2: Move to short game area (after a delay)
        time.sleep(random.uniform(3, 6))

        self._zone_counts["Driving Range"] = max(0, self._zone_counts.get("Driving Range", 0) - 1)
        self._zone_counts["Short Game Area"] = self._zone_counts.get("Short Game Area", 0) + 1

        event2 = ZoneEvent(
            person_id=person_id,
            local_track_id=person_id,
            camera_id="cam_shortgame_1",
            zone="Short Game Area",
            event_type="enter",
            timestamp=time.time(),
            position=(800, 500),
        )
        self.rule_engine.process_zone_events([event2])

        # Step 3: Return to range (theft pattern complete!)
        time.sleep(random.uniform(5, 10))

        self._zone_counts["Short Game Area"] = max(0, self._zone_counts.get("Short Game Area", 0) - 1)
        self._zone_counts["Driving Range"] = self._zone_counts.get("Driving Range", 0) + 1

        event3 = ZoneEvent(
            person_id=person_id,
            local_track_id=person_id,
            camera_id="cam_range_1",
            zone="Driving Range",
            event_type="enter",
            timestamp=time.time(),
            position=(600, 700),
        )
        self.rule_engine.process_zone_events([event3])

        # Thief eventually leaves
        def leave_later():
            time.sleep(random.uniform(20, 60))
            self._zone_counts["Driving Range"] = max(0, self._zone_counts.get("Driving Range", 0) - 1)

        threading.Thread(target=leave_later, daemon=True).start()


def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}")

    logger.info("=" * 60)
    logger.info("  Golf Range CV — DEMO MODE")
    logger.info("  Simulating customer activity and theft detection")
    logger.info("=" * 60)

    # Create demo pipeline
    pipeline = DemoPipeline()
    server.set_pipeline(pipeline)

    # Serve the dashboard HTML
    from fastapi.staticfiles import StaticFiles
    server.app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

    # Start simulation
    pipeline.start()

    logger.info("")
    logger.info("  Dashboard: http://localhost:8000/dashboard")
    logger.info("  API Docs:  http://localhost:8000/docs")
    logger.info("  WebSocket: ws://localhost:8000/ws")
    logger.info("")
    logger.info("  Watch the dashboard for live alerts!")
    logger.info("=" * 60)

    try:
        uvicorn.run(server.app, host="0.0.0.0", port=8000, log_level="warning")
    except KeyboardInterrupt:
        logger.info("Demo shutting down")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
