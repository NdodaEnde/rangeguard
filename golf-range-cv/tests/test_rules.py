"""Tests for the rule engine — the core business logic."""

import time

import pytest

from src.rules.rule_engine import (
    Alert, AlertSeverity, AlertType, RuleEngine,
)
from src.zones.zone_engine import ZoneEvent


def _make_event(person_id, zone, camera_id="cam1", timestamp=None):
    return ZoneEvent(
        person_id=person_id,
        local_track_id=person_id,
        camera_id=camera_id,
        zone=zone,
        event_type="enter",
        timestamp=timestamp or time.time(),
        position=(100, 100),
    )


class TestCrossZoneTheft:
    """Test the primary theft pattern: Range → Short Game → Range."""

    def test_range_shortgame_range_triggers_alert(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        events = [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 2),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]
        for e in events:
            engine.process_zone_events([e])

        # Fires both cross-zone theft AND reverse cross-zone (ShortGame→Range)
        theft_alerts = [a for a in alerts
                        if a.alert_type == AlertType.CROSS_ZONE_THEFT]
        assert len(theft_alerts) == 1
        assert theft_alerts[0].severity == AlertSeverity.HIGH
        assert theft_alerts[0].person_id == 1

    def test_no_alert_if_dwell_too_short(self):
        engine = RuleEngine(min_dwell_time=100, cooldown=0)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        events = [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 1),
            _make_event(1, "Driving Range", timestamp=now + 2),
        ]
        for e in events:
            engine.process_zone_events([e])

        assert len(alerts) == 0

    def test_cooldown_prevents_duplicate_alert(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=300)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        # First theft
        for e in [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 2),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]:
            engine.process_zone_events([e])

        # Second theft (within cooldown)
        for e in [
            _make_event(1, "Short Game Area", timestamp=now + 10),
            _make_event(1, "Driving Range", timestamp=now + 15),
        ]:
            engine.process_zone_events([e])

        assert len(alerts) == 1  # Only first one fires

    def test_different_people_get_separate_alerts(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        for pid in [1, 2]:
            for e in [
                _make_event(pid, "Driving Range", timestamp=now),
                _make_event(pid, "Short Game Area", timestamp=now + 2),
                _make_event(pid, "Driving Range", timestamp=now + 5),
            ]:
                engine.process_zone_events([e])

        theft_alerts = [a for a in alerts
                        if a.alert_type == AlertType.CROSS_ZONE_THEFT]
        assert len(theft_alerts) == 2
        assert theft_alerts[0].person_id == 1
        assert theft_alerts[1].person_id == 2

    def test_normal_customer_no_alert(self):
        """Customer stays in one zone — no alert."""
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        events = [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Driving Range", timestamp=now + 60),
        ]
        for e in events:
            engine.process_zone_events([e])

        assert len(alerts) == 0


class TestReverseCrossZone:
    """Test: Short Game → Range (unpaid range use)."""

    def test_shortgame_to_range_triggers_medium_alert(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        events = [
            _make_event(1, "Short Game Area", timestamp=now),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]
        for e in events:
            engine.process_zone_events([e])

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.UNPAID_RANGE_USE
        assert alerts[0].severity == AlertSeverity.MEDIUM


class TestAlertManagement:
    """Test alert querying and acknowledgement."""

    def test_acknowledge_alert(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        now = time.time()
        for e in [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 2),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]:
            engine.process_zone_events([e])

        alerts = engine.get_alerts()
        assert len(alerts) > 0

        alert_id = alerts[0].id
        assert engine.acknowledge_alert(alert_id) is True
        assert alerts[0].acknowledged is True

    def test_acknowledge_nonexistent_returns_false(self):
        engine = RuleEngine()
        assert engine.acknowledge_alert("FAKE-000") is False

    def test_query_unacknowledged_only(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        now = time.time()
        for e in [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 2),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]:
            engine.process_zone_events([e])

        engine.acknowledge_alert(engine.get_alerts()[0].id)

        unacked = engine.get_alerts(unacknowledged_only=True)
        # The cross-zone theft alert was acked, but reverse cross-zone might also fire
        for a in unacked:
            assert a.acknowledged is False

    def test_active_alerts_count(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        assert engine.active_alerts == 0

        now = time.time()
        for e in [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 2),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]:
            engine.process_zone_events([e])

        assert engine.active_alerts > 0
        assert engine.total_alerts > 0

    def test_person_history_tracking(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        now = time.time()
        engine.process_zone_events([
            _make_event(1, "Driving Range", timestamp=now),
        ])

        history = engine.get_person_history(1)
        assert history is not None
        assert history.current_zone == "Driving Range"
        assert len(history.zone_sequence) == 1

    def test_person_history_nonexistent(self):
        engine = RuleEngine()
        assert engine.get_person_history(999) is None

    def test_alert_zone_path_recorded(self):
        engine = RuleEngine(min_dwell_time=1, cooldown=0)
        alerts = []
        engine.on_alert(lambda a: alerts.append(a))

        now = time.time()
        for e in [
            _make_event(1, "Driving Range", timestamp=now),
            _make_event(1, "Short Game Area", timestamp=now + 2),
            _make_event(1, "Driving Range", timestamp=now + 5),
        ]:
            engine.process_zone_events([e])

        theft_alert = [a for a in alerts
                       if a.alert_type == AlertType.CROSS_ZONE_THEFT][0]
        assert theft_alert.zone_path == [
            "Driving Range", "Short Game Area", "Driving Range"
        ]
