# Site Visit Checklist — Camera Integration

Use this checklist when visiting the golf range to collect everything needed for real camera integration.

---

## 1. Camera Access (Critical)

- [ ] Get RTSP URL for each camera
  - Format: `rtsp://username:password@192.168.1.X:554/stream1`
  - Found in the camera's web admin interface (browse to the camera's IP)
  - If there's an NVR/DVR, get the NVR's IP and channel URLs instead
- [ ] Get camera admin credentials (username + password)
- [ ] Get WiFi password or ethernet access to the camera network
- [ ] Confirm your laptop can reach the cameras (same subnet/VLAN)

### How to find RTSP URLs by brand

| Brand | Typical RTSP URL format |
|-------|------------------------|
| Hikvision | `rtsp://admin:password@IP:554/Streaming/Channels/101` |
| Dahua | `rtsp://admin:password@IP:554/cam/realmonitor?channel=1&subtype=0` |
| Reolink | `rtsp://admin:password@IP:554/h264Preview_01_main` |
| Axis | `rtsp://admin:password@IP/axis-media/media.amp` |
| Generic ONVIF | Check camera web UI under "Network" or "Stream" settings |

If the owner doesn't know, ask: *"Can I access the camera's web interface? I'll find it from there."*

---

## 2. Camera Inventory

Fill in for each camera:

| # | Camera Name/Location | Make & Model | IP Address | RTSP URL | Resolution | Zone it covers |
|---|---------------------|-------------|-----------|----------|-----------|---------------|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |

---

## 3. Site Layout

Walk the site with the owner and note:

- [ ] Where are the driving range hitting bays?
- [ ] Where is the short game area (chipping green, bunkers)?
- [ ] What paths can people walk between the range and short game area?
  - Note: owner confirmed there are MULTIPLE paths (no single chokepoint)
- [ ] Where is the point of sale / payment counter?
- [ ] Where could a processing unit (small box) be mounted? (needs power + ethernet)

### Draw a rough map

```
Sketch the layout here or on paper. Mark:
- Camera positions (number them to match the table above)
- Camera viewing direction (arrow showing where it points)
- Zone boundaries (range, short game, transition paths)
- Payment/POS location


    [POS]
      |
      |  path
      |
[RANGE BAYS]----[path]----[SHORT GAME]
      |                        |
      |-----[path 2]-----------+

Camera 1: ___
Camera 2: ___
(etc.)
```

---

## 4. Camera Screenshots / Test Footage

- [ ] Take a screenshot from each camera's live view
  - Use the camera's web interface or phone app
  - Save as: `cam1_range.jpg`, `cam2_shortgame.jpg`, etc.
- [ ] Ask the owner: *"Can I get 10-15 minutes of recorded footage from each camera?"*
  - Most NVRs can export clips to USB stick
  - Request footage during a busy period (weekday afternoon, weekend morning)
  - This lets you develop and test at home without being on-site

---

## 5. Network Details

- [ ] Camera network IP range (e.g., 192.168.1.X)
- [ ] Is there a separate VLAN for cameras?
- [ ] NVR/DVR details (if used):
  - Make/model: ___
  - IP address: ___
  - Number of channels: ___
- [ ] Is there a wired ethernet port available near a potential mounting location?
- [ ] Internet connection available? (for remote access later — not required for MVP)

---

## 6. Operations Info

- [ ] Business hours (range open from ___ to ___)
- [ ] Peak hours (busiest times for theft)
- [ ] How many customers per day on average?
- [ ] Current bucket ball price: R75 (confirmed)
- [ ] Current short game price: R20 (confirm)
- [ ] How does the sticker system work today? (colour, placement, who checks)
- [ ] Approximate number of balls in the short game area at any time?
- [ ] How often does the ball picker run?

---

## 7. Questions for the Owner

Ask these during the visit:

1. *"Which cameras have the best view of people moving between the range and short game area?"*
2. *"Where do you think most of the ball theft happens — which path do people use?"*
3. *"Do you have an IT person who manages the cameras, or do you handle it yourself?"*
4. *"Would it be okay if I connect my laptop to your camera network for testing?"*
5. *"Can I come back during a busy period to test with real activity?"*
6. *"Where would you want to see the alert dashboard — office PC, your phone, or both?"*

---

## 8. What to Bring

- [ ] Laptop with the project installed and demo ready
- [ ] Ethernet cable (Cat5e/Cat6)
- [ ] USB stick (for receiving recorded footage)
- [ ] Phone for taking site photos
- [ ] Notebook / this printed checklist
- [ ] Power adapter / extension cord

---

## 9. Quick Demo at the Site

Before you leave, if possible:

1. Connect laptop to the camera network
2. Test one RTSP stream: `ffplay rtsp://admin:password@IP:554/stream1`
   - If ffplay isn't installed: `brew install ffmpeg`
   - Or use VLC: Open Network Stream > paste RTSP URL
3. Show the owner the dashboard with the demo simulation
4. Explain: *"This is simulated. Once I connect your cameras, it will track real people and real movement patterns."*

---

## After the Visit

- [ ] Update `config/default.yaml` with real camera RTSP URLs and zone assignments
- [ ] Draw zone polygons on each camera's screenshot (mark range, short game, transition areas)
- [ ] Convert polygon coordinates to normalized 0-1 values and add to `zone_maps` in config
- [ ] Test with recorded footage before going back for live testing
