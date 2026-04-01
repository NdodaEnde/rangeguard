---
name: verify
description: Run the full verification suite — lint, tests, imports, demo smoke test
user_invocable: true
---

# Verify

Runs the complete verification suite for the Golf Range CV project. Use this after completing any task before marking it done.

## Steps

### Step 1: Syntax & Import Check
```bash
cd "golf-range-cv" && python -c "
import src.video.stream
import src.detection.detector
import src.tracking.tracker
import src.zones.zone_engine
import src.reid.person_reid
import src.rules.rule_engine
import src.alerts.alert_manager
import src.api.models
import src.api.server
import src.pipeline
print('All modules import successfully')
"
```
- Must produce no ImportError or SyntaxError.
- If a module fails to import, report the exact error.

### Step 2: Lint
```bash
cd "golf-range-cv" && python -m flake8 src/ --max-line-length 100 --count
```
- Must produce zero errors.
- If flake8 is not installed, install it: `pip install flake8`

### Step 3: Unit Tests
```bash
cd "golf-range-cv" && python -m pytest tests/ -v --tb=short
```
- All tests must pass.
- Report any failures with file path and error message.
- If pytest is not installed, install it: `pip install pytest`

### Step 4: Config Validation
```bash
cd "golf-range-cv" && python -c "
import yaml
with open('config/default.yaml') as f:
    cfg = yaml.safe_load(f)
assert 'cameras' in cfg, 'Missing cameras config'
assert 'zones' in cfg, 'Missing zones config'
assert 'detection' in cfg, 'Missing detection config'
assert 'tracking' in cfg, 'Missing tracking config'
assert 'reid' in cfg, 'Missing reid config'
assert 'rules' in cfg, 'Missing rules config'
print(f'Config valid: {len(cfg[\"cameras\"])} cameras, {len(cfg[\"zones\"])} zones')
"
```

### Step 5: Demo Smoke Test
```bash
cd "golf-range-cv" && timeout 10 python -c "
from src.rules.rule_engine import RuleEngine
from src.zones.zone_engine import ZoneEvent
import time

engine = RuleEngine(time_window=1800, min_dwell_time=1, cooldown=5)
alerts_fired = []
engine.on_alert(lambda a: alerts_fired.append(a))

pid = 1
events = [
    ZoneEvent(person_id=pid, local_track_id=pid, camera_id='cam1', zone='Driving Range', event_type='enter', timestamp=time.time(), position=(100,100)),
    ZoneEvent(person_id=pid, local_track_id=pid, camera_id='cam2', zone='Short Game Area', event_type='enter', timestamp=time.time()+2, position=(200,200)),
    ZoneEvent(person_id=pid, local_track_id=pid, camera_id='cam1', zone='Driving Range', event_type='enter', timestamp=time.time()+5, position=(100,100)),
]
for e in events:
    engine.process_zone_events([e])

assert len(alerts_fired) > 0, 'Rule engine did not fire alert for cross-zone pattern'
print(f'Rule engine smoke test passed: {len(alerts_fired)} alert(s) fired')
" || echo "SMOKE TEST FAILED"
```

### Step 6: Report
Produce a summary:
```
✓ Module imports: all clean
✓ Lint: zero errors
✓ Unit tests: X/X passed
✓ Config: valid
✓ Rule engine smoke test: passed
```

If any step fails, do NOT report success. List the failures clearly and stop.

## Rules
- Never skip a verification step.
- Never mark a task as complete if verification fails.
- If a dependency is missing, install it and re-run.
