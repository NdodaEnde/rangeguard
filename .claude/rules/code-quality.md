---
name: code-quality
description: Coding standards for the Golf Range CV Python project
---

# Code Quality Rules

## Python Standards

1. **Read before writing**: Always read existing code before modifying. Understand the module's role in the pipeline before extending it.

2. **No file over 400 lines**: If a file exceeds 400 lines, extract a logical sub-module. Detectors, trackers, and engines should each be focused on one responsibility.

3. **Modules are independent**: Each module in `src/` should be testable in isolation. Modules communicate through dataclasses (Detection, Track, ZoneEvent, Alert), not by importing each other's internals.

4. **Config over hardcoding**: Thresholds, model paths, zone definitions, and timing parameters go in `config/default.yaml`. Never hardcode tunable values in source code.

5. **Type hints on all public functions**: Use Python 3.11+ type hints. Return types and parameter types are required on all public methods.

6. **Dataclasses for data structures**: Use `@dataclass` for Detection, Track, ZoneEvent, Alert, and similar structs. Not plain dicts.

7. **Loguru for logging**: Use `from loguru import logger`. Do not use `print()` for debug output.

## CV-Specific Standards

8. **Numpy arrays for bounding boxes**: Bboxes are always `np.ndarray` in `[x1, y1, x2, y2]` format (pixel coordinates). Never use `[x, y, w, h]` or normalized coords internally.

9. **Zone polygons use normalized coordinates in config**: Config files use 0-1 normalized coords. Convert to pixel coords at load time based on camera resolution.

10. **Embeddings are L2-normalized**: All Re-ID feature vectors must be L2-normalized before storage or comparison. Cosine similarity on normalized vectors = dot product.

11. **Lazy model loading**: ML models (YOLO, OSNet) load on first use, not at import time. This keeps startup fast and tests lightweight.

## Testing Standards

12. **Test each module independently**: Tests for detection don't need real cameras. Tests for the rule engine don't need real detections. Use synthetic data.

13. **Test names describe the scenario**: Format: `test_cross_zone_range_to_shortgame_to_range_triggers_alert`. Not `test_1`.

14. **No skipped tests**: Never skip a test to make CI pass. Fix it or delete it.

## Git Standards

15. **Commit after verification**: Only commit code that passes tests and lint. Never commit broken code.

16. **Commit messages describe the change**: Format: `feat: add cross-camera Re-ID with OSNet` or `fix: zone exit event not firing on track loss`.

17. **One feature per commit**: Don't bundle unrelated changes.
