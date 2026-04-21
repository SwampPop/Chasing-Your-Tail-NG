# Handoff Document — CYT-NG

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-21 11:11 CDT
**Latest Session Duration**: ~10 h (integration + 7 h overnight capture + review exports)

## Goal

Maintain CYT-NG as a passive-monitoring platform for operator's residential and mobile RF environment. Expand coverage to Bluetooth Low Energy without introducing new hardware. Close out HN-012 (Cox public-hotspot opt-out, pending Cox Tier 2 call).

## Progress Summary — 2026-04-21

### Mac-native Bluetooth integration (new)
- ✅ Completed the unfinished `bleak` path in `ble_tracker_detector.py` (docstring advertised both Kismet and bleak sources — only the Kismet half was wired)
- ✅ New module `macos_ble_scanner.py` — `bleak.BleakScanner` in a dedicated asyncio thread, lock-protected writes to shared `BLETrackerDetector`, Kismet GPS fetcher with cache
- ✅ New test file `tests/test_macos_ble_scanner.py` — 13 tests (classifier, GPS cache, lock contention, dashboard drain, Kismet dedup, DB persistence)
- ✅ Wired into `watchdog_dashboard.py`: shared `ble_detector_lock`, scanner lifecycle, `atexit` cleanup, drain pattern in `process_devices()`, Kismet-down fallback, `db_logger.log_detection()` for durability
- ✅ Added `bleak>=0.22` + `bluetooth_settings` config block
- ✅ Full test suite 74/74 green, live scanner verified (158 callbacks / 6 s), dashboard HTML renders BLE rows

### Overnight + morning capture
- ✅ 7 h continuous run (02:45 → 09:44) wrapping `python3 watchdog_dashboard.py` in `caffeinate -dims`
- ✅ **12 WiFi cameras** (8 new tonight): most persistent is Nest `18:B4:30:93:F7:20` with 340 sightings over 284 min at RSSI -78 (likely neighbor's camera)
- ✅ **2,921 BLE tracker identifiers** / **63,989 total sightings** — 2,686 Apple Find My, 224 Samsung SmartTag, 11 Tile
- ✅ 4 "lives-here" candidates (5+ h persistence, thousands of sightings each, RSSI -54 to -89) — operator's own devices
- ✅ Review CSVs produced: `review_20260421/all_detections.csv`, `tracker_details.csv`
- ⚠️ Zero `FOLLOWING` alerts — u-blox never locked satellites indoors, so the "2+ locations" criterion never fired

## Current State

- **Git**: `5cd5394` HEAD + uncommitted work (4 modified, 2 new files + `review_20260421/`)
- **Kali VM**: running; Kismet stopped at session close
- **Mac dashboard**: stopped; all processes clean
- **Hardware**: Alfa WiFi adapter + u-blox GNSS puck removed (user unplugged for mobility)
- **Database**: `watchdog_live.db` preserved, 204 KB, 2,935 detection rows

## What Worked

- **Framing as "complete an unfinished feature"** — `process_ble_advertisement()`'s signature was already perfect for `bleak.AdvertisementData`. Tighter scope than "add Bluetooth" would have been.
- **Advisor call mid-plan caught the UI gap** — scanner was incrementing `ble_detector.trackers` but never pushing into `recent_detections`. Drain pattern on each scan cycle fixed it cleanly.
- **Advisor also flagged asyncio + eventlet conflicts early** — baked into design from the start: dedicated thread, fresh event loop, `threading.Lock()`, not dual rebinding.
- **Pre-existing `prlctl exec` fallback in `fetch_kismet_devices()`** — direct HTTP from Mac to VM stopped working mid-capture; fallback kept the scan loop alive.

## What Didn't Work

- **Direct curl to `10.211.55.12:2501`** returned HTTP 000 with time=15s after user restarted Kismet, despite dashboard scans continuing to succeed. Never root-caused (prlctl path worked and ran out the clock). Possible bridge-mode networking hiccup.
- **My "kill" on session-stop** hit the `nohup caffeinate` wrapper (PID 2203) but not the actual Python child — dashboard kept running ~45 min until hardware removal broke it. No harm, just a reminder to kill by process tree next time.
- **User's paste broke `sudo systemctl enable --now ssh`** across a newline; still unresolved (TUI option requires sshd in VM).

## Next Steps

1. **Decide commit scope** — all 4 modified + 2 new + `review_20260421/` are uncommitted. Suggest a single commit: `feat(ble): complete mac-native scanner path (bleak) + overnight validation`. User hasn't given the go-ahead yet.
2. **Real wardrive with GPS lock** — 7 h indoor capture never populated `latitude`/`longitude` on any tracker row. An outdoor run with sky view will let `FOLLOWING` (30 min / 2+ locations) actually fire.
3. **Reassess HN-009** ("Purchase BT adapter for BLE coverage") in `todo.md` — Mac-native scanning now covers passive advertisement capture (Find My / Tile / SmartTag). External adapter still valuable for active GATT probing or raw packet-level analysis, but no longer blocking for tracker detection.
4. **HN-012 Cox Tier 2 call** — unchanged from last handoff, still pending human action.

## Blockers

- None for CYT code. Still the longstanding HN-012 (external — requires phone call to Cox).
- SSH into Kali VM for TUI requires `sudo systemctl start ssh` (one-line, inside VM console).

## Key Files

### New
- `macos_ble_scanner.py` — scanner module (`MacOSBLEScanner` class, `build_kismet_gps_fetcher()` helper)
- `tests/test_macos_ble_scanner.py` — 13 unit tests
- `review_20260421/all_detections.csv` — full DB export, 2,935 rows
- `review_20260421/tracker_details.csv` — trackers with parsed `match_details`, 2,921 rows
- `review_20260421/extract_tracker_details.py` — regeneration script
- `logs/watchdog_overnight_20260421_024532.log` — 184 KB overnight capture log
- `logs/wardrive_20260421_085846.log` — 359 KB morning extension log

### Modified
- `requirements.txt` — added `bleak>=0.22` (pulls pyobjc-core + pyobjc-framework-CoreBluetooth)
- `config.json` — `bluetooth_settings` block (enabled/gps_source/cache/thresholds/log_level)
- `watchdog_dashboard.py` — shared `ble_detector_lock`, scanner lifecycle in `main()`, `_make_tracker_detection()` + drain pattern in `process_devices()`, `_drain_host_ble_only()` fallback
- `watchdog_live.db` — +8 cameras, +2,921 trackers, +1 unknown from tonight

### Still load-bearing (unchanged)
- `ble_tracker_detector.py` — `BLETrackerDetector` consumes the new scanner's output unmodified
- `start_kismet_clean.sh` (on VM) — launcher for Kismet

## Commands to Resume

```bash
# Full test suite (run before any further changes)
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
source venv_new/bin/activate
python3 -m unittest discover -s tests

# Re-launch overnight-style capture (after plugging Alfa + u-blox back in, start Kismet in VM)
LOGFILE="logs/watchdog_$(date +%Y%m%d_%H%M%S).log"
nohup caffeinate -dims python3 -u watchdog_dashboard.py \
    --kismet-url http://10.211.55.12:2501 \
    --kismet-user kismet --kismet-pass watchdog2026 \
    --port 5002 --interval 10 > "$LOGFILE" 2>&1 &
echo $! > logs/watchdog.pid

# Dashboard view
open http://127.0.0.1:5002

# Review last capture
sqlite3 watchdog_live.db "SELECT device_type, COUNT(*), SUM(seen_count) FROM detections GROUP BY device_type"
sqlite3 watchdog_live.db "SELECT mac, manufacturer, seen_count FROM detections WHERE detection_method='ble_persistence'"  # FOLLOWING alerts

# Regenerate tracker CSV
python3 review_20260421/extract_tracker_details.py

# Clean shutdown
kill $(cat logs/watchdog.pid) && sleep 2 && pgrep -f watchdog_dashboard  # should be empty
prlctl exec "Kali Linux 2025.2 ARM64" sudo killall -9 kismet
```

## Session Stats

- Tests: **74 passing** (61 pre-existing + 13 new)
- New code: `macos_ble_scanner.py` 222 lines, test file 250 lines
- Overnight runtime: **7 h 0 m** end-to-end
- Captured: 12 cameras, 2,921 BLE tracker IDs, 63,989 sightings
- Zero crashes, zero test regressions, zero errors in the 7 h log
