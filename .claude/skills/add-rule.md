---
name: add-rule
description: Add a new detection rule to the rule engine for a specific suspicious behavior pattern
user_invocable: true
---

# Add Detection Rule

Adds a new behavioral rule to the rule engine that detects a specific suspicious movement pattern.

## Instructions

1. **Read the existing rules** in `golf-range-cv/src/rules/rule_engine.py` to understand the pattern.

2. **Define the rule**:
   - What zone sequence triggers it? (e.g., Range → Short Game → Range)
   - What timing thresholds apply? (min dwell time, time window)
   - What severity level? (low, medium, high)
   - What alert message should be generated?

3. **Implement the rule** as a new `_check_*` method in the `RuleEngine` class:
   - Follow the pattern of `_check_cross_zone_theft` and `_check_reverse_cross_zone`
   - Accept `PersonMovementHistory` and `ZoneEvent` parameters
   - Return `Alert | None`
   - Respect the cooldown period

4. **Wire it up** by adding a call to the new method in `_check_rules()`.

5. **Add config** for the new rule's thresholds in `config/default.yaml` under the `rules:` section.

6. **Write a test** in `tests/` that:
   - Creates synthetic zone events matching the pattern
   - Verifies the alert fires with correct type and severity
   - Verifies the alert does NOT fire for non-matching patterns

7. **Run `/verify`** to confirm everything passes.

## Template for the check method:
```python
def _check_new_rule(self, history: PersonMovementHistory,
                    event: ZoneEvent) -> Alert | None:
    now = time.time()
    if now - history.last_alert_time < self.cooldown:
        return None

    recent = history.get_recent_zones(self.time_window)
    # ... pattern matching logic ...

    self._alert_counter += 1
    alert = Alert(
        id=f"ALT-{self._alert_counter:06d}",
        alert_type=AlertType.NEW_TYPE,  # Add to AlertType enum
        severity=AlertSeverity.MEDIUM,
        person_id=history.global_id,
        message="Description of what was detected",
        camera_id=event.camera_id,
        zone_path=[...],
    )
    self._alerts.append(alert)
    history.last_alert_time = now
    for cb in self._alert_callbacks:
        cb(alert)
    return alert
```
