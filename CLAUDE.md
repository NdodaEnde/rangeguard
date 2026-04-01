# Golf Range CV — Revenue Protection System

## Project Overview
Computer vision system that detects and deters revenue leakage at golf driving ranges. Tracks people across cameras using YOLOv8 detection, ByteTrack tracking, and OSNet re-identification. Alerts staff when customers move between zones (range ↔ short game) without paying.

## Tech Stack
- **CV Pipeline**: Python 3.11+, YOLOv8 (ultralytics), ByteTrack, OSNet (torchreid), OpenCV
- **Backend**: FastAPI, WebSockets, SQLite (MVP) → PostgreSQL (scale)
- **Frontend**: Single-page HTML dashboard with TailwindCSS
- **Deployment**: Docker, NVIDIA Jetson Orin Nano (edge)

## Project Structure
```
golf-range-cv/
├── src/
│   ├── detection/     # YOLOv8 person detection
│   ├── tracking/      # ByteTrack multi-object tracking
│   ├── reid/          # Cross-camera person re-identification (OSNet)
│   ├── zones/         # Polygon zone definitions, entry/exit events
│   ├── rules/         # Rule engine for suspicious behavior detection
│   ├── alerts/        # Alert distribution (WebSocket, log, WhatsApp)
│   ├── video/         # RTSP stream handling, frame capture
│   ├── api/           # FastAPI REST + WebSocket server
│   └── pipeline.py    # Main orchestrator tying all modules together
├── dashboard/         # Frontend (HTML + TailwindCSS + vanilla JS)
├── config/            # YAML configuration files
├── tests/             # Test suite
├── main.py            # Production entry point
└── demo.py            # Demo mode — simulates activity without cameras
```

## Key Commands
```bash
# Run demo (no cameras needed)
cd golf-range-cv && python demo.py

# Run production
cd golf-range-cv && python main.py

# Run production with custom config
cd golf-range-cv && python main.py config/custom.yaml

# Run tests
cd golf-range-cv && python -m pytest tests/ -v

# Docker
cd golf-range-cv && docker-compose up --build

# Lint
cd golf-range-cv && python -m flake8 src/ --max-line-length 100
```

## Workflow
**Every task follows: Do → Verify → Move**

1. Pick one task, mark it `in_progress`
2. Implement it
3. Run `/verify` to confirm it works
4. Only then mark `completed` and move to the next task

Never skip verification. Never batch-complete tasks.

## Architecture Principles
- Each module in `src/` is independent and testable in isolation
- The pipeline orchestrates modules — modules don't import each other except through defined interfaces (dataclasses)
- Config is in YAML, not hardcoded
- Zone polygons use normalized (0-1) coordinates for camera-independence
- Re-ID uses appearance embeddings, not facial recognition (POPIA compliance)
- Fallback to color histogram Re-ID when OSNet is not available
