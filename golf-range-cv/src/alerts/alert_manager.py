"""
Alert manager — distributes alerts to WebSocket clients, logs, and external services.
"""

import asyncio
import json
import time

from loguru import logger

from src.rules.rule_engine import Alert


class AlertManager:
    """
    Manages alert distribution to multiple channels:
    - WebSocket (real-time dashboard)
    - Log file
    - WhatsApp (future)
    """

    def __init__(self, log_file: str = "alerts.log"):
        self.log_file = log_file
        self._websocket_clients: set = set()
        self._recent_alerts: list[dict] = []
        self._max_recent = 100

    def register_ws_client(self, websocket):
        """Register a WebSocket client for real-time alerts."""
        self._websocket_clients.add(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self._websocket_clients)}")

    def unregister_ws_client(self, websocket):
        """Remove a disconnected WebSocket client."""
        self._websocket_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self._websocket_clients)}")

    def handle_alert(self, alert: Alert):
        """
        Process an alert — called by the rule engine callback.
        Dispatches to all configured channels.
        """
        alert_dict = alert.to_dict()

        # Store in recent alerts
        self._recent_alerts.append(alert_dict)
        if len(self._recent_alerts) > self._max_recent:
            self._recent_alerts = self._recent_alerts[-self._max_recent:]

        # Log to file
        self._log_alert(alert)

        # Direct broadcast to WebSocket clients (thread-safe)
        self._broadcast_sync(alert_dict)

    def _broadcast_sync(self, alert_dict: dict):
        """Broadcast alert to all WebSocket clients from any thread."""
        if not self._websocket_clients:
            return

        message = json.dumps({
            "type": "alert",
            "data": alert_dict,
        })

        disconnected = set()
        for ws in self._websocket_clients:
            try:
                # Get the running event loop and schedule the send
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        ws.send_text(message), loop
                    )
                else:
                    asyncio.run(ws.send_text(message))
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.unregister_ws_client(ws)

    async def send_status_update(self, status: dict):
        """Broadcast a status update (zone occupancy, etc.) to all clients."""
        message = json.dumps({
            "type": "status",
            "data": status,
        })

        disconnected = set()
        for ws in self._websocket_clients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.unregister_ws_client(ws)

    def _log_alert(self, alert: Alert):
        """Append alert to log file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{alert.severity.value.upper()} | {alert.alert_type.value} | "
                    f"Person #{alert.person_id} | {alert.message}\n"
                )
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")

    def get_recent_alerts(self, limit: int = 50) -> list[dict]:
        """Get recent alerts for dashboard initial load."""
        return self._recent_alerts[-limit:]

    @property
    def connected_clients(self) -> int:
        return len(self._websocket_clients)
