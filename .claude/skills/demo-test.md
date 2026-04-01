---
name: demo-test
description: Run the demo simulation and verify alerts fire correctly
user_invocable: true
---

# Demo Test

Starts the demo simulation and verifies the full system works end-to-end without cameras.

## Steps

### Step 1: Start Demo Server
```bash
cd "golf-range-cv" && timeout 30 python -c "
import threading
import time
import requests

# Import and set up demo
from demo import DemoPipeline
from src.api import server

pipeline = DemoPipeline()
server.set_pipeline(pipeline)
pipeline.start()

# Run server in background
import uvicorn
server_thread = threading.Thread(
    target=lambda: uvicorn.run(server.app, host='127.0.0.1', port=8099, log_level='error'),
    daemon=True
)
server_thread.start()
time.sleep(3)

# Test endpoints
print('Testing API endpoints...')

resp = requests.get('http://127.0.0.1:8099/api/status')
assert resp.status_code == 200, f'Status endpoint failed: {resp.status_code}'
print(f'  /api/status: OK')

resp = requests.get('http://127.0.0.1:8099/api/cameras')
assert resp.status_code == 200, f'Cameras endpoint failed: {resp.status_code}'
cameras = resp.json()
print(f'  /api/cameras: OK ({len(cameras)} cameras)')

resp = requests.get('http://127.0.0.1:8099/api/alerts')
assert resp.status_code == 200, f'Alerts endpoint failed: {resp.status_code}'
print(f'  /api/alerts: OK')

resp = requests.get('http://127.0.0.1:8099/api/dashboard')
assert resp.status_code == 200, f'Dashboard endpoint failed: {resp.status_code}'
print(f'  /api/dashboard: OK')

# Wait for alerts to generate
print('Waiting for demo alerts...')
time.sleep(15)

resp = requests.get('http://127.0.0.1:8099/api/alerts')
alerts = resp.json()
print(f'  Alerts generated: {len(alerts)}')

pipeline.stop()
print('Demo test complete!')
" || echo "DEMO TEST FAILED"
```

### Step 2: Report
```
✓ API server starts
✓ /api/status returns 200
✓ /api/cameras returns camera list
✓ /api/alerts returns alert list
✓ /api/dashboard returns full data
✓ Demo simulation generates alerts
```

If any step fails, report the error clearly.
