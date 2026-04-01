"""Tests for the alert manager."""

import pytest

from src.alerts.alert_manager import AlertManager
from src.rules.rule_engine import Alert, AlertSeverity, AlertType


def _make_alert(alert_id="ALT-000001", person_id=1):
    return Alert(
        id=alert_id,
        alert_type=AlertType.CROSS_ZONE_THEFT,
        severity=AlertSeverity.HIGH,
        person_id=person_id,
        message="Test alert",
        camera_id="cam1",
        zone_path=["Driving Range", "Short Game Area", "Driving Range"],
    )


class TestAlertManager:
    """Test alert storage and distribution."""

    def test_handle_alert_stores_in_recent(self):
        manager = AlertManager(log_file="/dev/null")
        alert = _make_alert()
        manager.handle_alert(alert)

        recent = manager.get_recent_alerts()
        assert len(recent) == 1
        assert recent[0]["id"] == "ALT-000001"

    def test_recent_alerts_limited_to_max(self):
        manager = AlertManager(log_file="/dev/null")
        manager._max_recent = 5

        for i in range(10):
            manager.handle_alert(_make_alert(f"ALT-{i:06d}", person_id=i))

        recent = manager.get_recent_alerts()
        assert len(recent) == 5
        # Should keep the latest 5
        assert recent[0]["id"] == "ALT-000005"

    def test_get_recent_alerts_with_limit(self):
        manager = AlertManager(log_file="/dev/null")
        for i in range(10):
            manager.handle_alert(_make_alert(f"ALT-{i:06d}"))

        recent = manager.get_recent_alerts(limit=3)
        assert len(recent) == 3

    def test_no_websocket_clients_initially(self):
        manager = AlertManager(log_file="/dev/null")
        assert manager.connected_clients == 0

    def test_alert_dict_format(self):
        alert = _make_alert()
        d = alert.to_dict()

        assert d["id"] == "ALT-000001"
        assert d["alert_type"] == "cross_zone_theft"
        assert d["severity"] == "high"
        assert d["person_id"] == 1
        assert d["zone_path"] == [
            "Driving Range", "Short Game Area", "Driving Range"
        ]
        assert d["acknowledged"] is False
