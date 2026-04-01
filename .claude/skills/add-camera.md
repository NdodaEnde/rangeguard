---
name: add-camera
description: Add a new camera to the system with zone mapping
user_invocable: true
---

# Add Camera

Adds a new camera feed to the system with its zone polygon mapping.

## Instructions

1. **Get camera details** from the user:
   - Camera name and ID
   - RTSP URL (or video file path for testing)
   - Which zone it covers (range, short_game, transition)
   - Resolution
   - Target FPS

2. **Add camera config** to `config/default.yaml`:
   ```yaml
   cameras:
     - id: "cam_new_1"
       name: "New Camera Name"
       source: "rtsp://admin:password@192.168.1.XX:554/stream1"
       zone: "range"  # or short_game, transition
       fps: 15
       resolution: [1920, 1080]
   ```

3. **Add zone polygon** to `zone_maps` in `config/default.yaml`:
   ```yaml
   zone_maps:
     cam_new_1:
       range: [[0.0, 0.3], [1.0, 0.3], [1.0, 1.0], [0.0, 1.0]]
   ```
   - Use normalized 0-1 coordinates
   - The polygon defines which area of the camera view maps to the zone
   - Ask the user to describe what portion of the camera view shows the zone

4. **If the camera covers a new zone**, add the zone definition:
   ```yaml
   zones:
     new_zone:
       name: "Display Name"
       color: [R, G, B]
       cameras: ["cam_new_1"]
   ```

5. **Verify** by running the pipeline with the new config and checking that:
   - The camera connects (or reports a clear connection error)
   - Zone polygons render correctly on the frame
   - Person detections within the zone generate correct zone events

6. **Run `/verify`** to confirm config is valid.
