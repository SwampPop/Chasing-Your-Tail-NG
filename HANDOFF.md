# Handoff Document — CYT-NG

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-18 15:30 CDT
**Latest Session Duration**: ~6 h (deploy + wire orphans + full passive recon engagement)

## Goal

Get CYT-NG fully operational (Kali VM, watchdog dashboard, all detection modules wired), and use it to conduct a real passive-RF reconnaissance against the operator's own residential environment — delivering professional threat-surface analysis and a prioritized mitigation plan.

## Progress Summary — 2026-04-18 Session

- ✅ 5 untracked Python modules + config/ + templates/ committed in 5 logical commits + docs commit + 1 follow-up fix
- ✅ BLE tracker + ALPR context wired into watchdog_dashboard.py (phy-branching in `process_devices()`, `fetch_kismet_gps()` helper with shape-tolerant `_parse_kismet_gps_payload()`)
- ✅ All 64 pytest tests still passing
- ✅ Deployed to Kali VM (Technicolor/Cox XB6 gateway at 192.168.0.1), pulled + installed + preflight 14/0/4, Kismet running on `wlan0`
- ✅ WPS vulnerability test: NEGATIVE on all 10 operator VAPs (HN-006 CLOSED)
- ✅ 66-min extended passive capture: 675 devices, 21 transient probers, 26 probes captured
- ✅ 3 field reports filed to `2_reference_docs/docs/network/` + Desktop:
  - HOME_NETWORK_FIELD_REPORT_2026-04-18.md (31.9 KB)
  - WPS_VULNERABILITY_TEST_REPORT_2026-04-18.md (14.9 KB)
  - HOUSEHOLD_DEVICE_PROFILES_2026-04-18.md (39.1 KB)
- ✅ All 3 "uncatalogued" internal devices identified as household: Litter-Robot 4, iPad, iPhone
- ✅ Discovered 10th virtual AP / 2nd visible SSID "SCIF Access Node" (2.4 GHz ch 1)
- ✅ ProtonVPN kill-switch LAN-blocking diagnosed + fixed (user enabled "Allow LAN connections")
- ✅ Cox public-hotspot opt-out executed by user (verification pending)
- 🔄 Scheduled wakeup 15:58 to verify Cox hotspot VAPs `:78` and `:80` went silent via live Kismet check

## Current State

- **Git**: clean, all pushed to origin/main, HEAD `c22e792`
- **Kali VM**: Kismet running (PID 689387), capturing continuously since ~12:25
- **Dashboard**: stopped (can be restarted; command below)
- **Scheduled wakeup**: fires 15:58 CDT (will run Cox hotspot verification automatically)
- **Reports**: all three field reports filed in 2 locations each; sensitive (don't commit)

## What Worked

- **Logical commit-splitting strategy**: 6 small commits beats 1 giant one. Each can be reverted independently. Clean history.
- **Advisor calls at the right gates**: caught the GPS geopoint-vs-scalar bug that would have been a silent field-deployment defect; caught the "push first, check Kali divergence after" near-miss.
- **Cross-verification of negative findings**: `wash` alone couldn't prove WPS disabled (might have missed beacons). Airodump-ng on each target channel confirmed we were receiving beacons AND the WPS column was empty. Converted a null result into a positive conclusion.
- **Advisor-suggested shape tolerance**: `_extract_device_location()` pattern (dict OR list, with fallback to geopoint array) turned out to be the right abstraction; same treatment applied to `fetch_kismet_gps` during the follow-up fix.
- **Using Kismet REST API + prlctl exec** (not SSH / passthrough over network) — Parallels exec is surprisingly reliable as a control channel.
- **Categorizing analysis (household / neighbor / transient probers)**: clear separation made the profile report immediately useful for operator decisions rather than a wall of devices.

## What Didn't Work

- **Initial profile_builder.py assumed Kismet's `probed_ssid_map` is a dict.** In this Kismet version it's a LIST. Zero probes captured on first run despite 61 devices actually having probes. Patched in-session. **Lesson: always inspect real data shape before trusting assumptions.**
- **Kismet + active WPS test simultaneously: not possible** (both need exclusive monitor-mode access). Sequential only.
- **Ping / curl / nc from Mac to LAN gateway: mysteriously failed** for ~15 minutes of debugging. Not pf, not route table, not LuLu. Was ProtonVPN kill-switch's NetworkExtension-layer rules, invisible to `pfctl`. Lesson: always add "any active VPN?" to the diagnostic checklist.
- **WebFetch on Cox JS-heavy support pages**: returned empty content. Had to pivot to Cox community forums + 3rd-party tutorials to extract the actual opt-out path.

## Next Steps

1. **Handle 15:58 scheduled wakeup** — Cox hotspot verification. If negative (VAPs silent): update HN-012 across all 3 reports to CLOSED. If still beaconing: provide Cox call script.
2. **Decide Kismet fate**: stop or let run overnight for richer probe corpus. Operator's call.
3. **Optional: port the SSID-map list-tolerance patch upstream** into `watchdog_dashboard.py` so future runs don't hit the same bug on this Kismet version. (Patch lives on `/tmp/profile_builder.py` on Kali — ephemeral.)
4. **BT adapter**: user is considering nRF52840 Dongle + Sniffle (primary) or TP-Link UB500 (fallback). When hardware arrives, write the Sniffle-to-CYT-NG bridge script.
5. **Strategic next project (deferred)**: bridge-mode + own router to regain user control over WPA3, PMF, TX power, UPnP — all things Cox XB6 firmware locks out.

## Blockers

- **None active.** Two conditional items pending:
  - Cox hotspot verification (automatic at 15:58)
  - If opt-out failed: user must call Cox (offered support phrasing in Cox research block)

## Key Files

**Code (committed, in this repo)**:
- `watchdog_dashboard.py` — main integration point; do not regress the phy-branching in `process_devices()`
- `ble_tracker_detector.py`, `alpr_context.py` — new modules wired to dashboard
- `camera_detector.py`, `drone_signature_matcher.py`, `watchdog_reporter.py` — committed in preceding commit
- `config/camera_signatures.yaml`, `config/drone_signatures.yaml`, `config/alpr_locations_nola.json`, `templates/cvd_memo.md`

**Reports (NOT committed; sensitive)**:
- `~/my_projects/2_reference_docs/docs/network/HOME_NETWORK_FIELD_REPORT_2026-04-18.md`
- `~/my_projects/2_reference_docs/docs/network/WPS_VULNERABILITY_TEST_REPORT_2026-04-18.md`
- `~/my_projects/2_reference_docs/docs/network/HOUSEHOLD_DEVICE_PROFILES_2026-04-18.md`
- All three also at `~/Desktop/…`

**Session log**:
- `~/AI-Sessions/logs/session-2026-04-18-cyt-ng-deployment.md`

## Commands to Resume

```bash
# Verify Kismet still running on Kali:
prlctl exec "Kali Linux 2025.2 ARM64" "pgrep -af 'kismet -c'"

# Pull a fresh snapshot + view summary:
prlctl exec "Kali Linux 2025.2 ARM64" \
  "curl -s -u kismet:watchdog2026 http://localhost:2501/devices/last-time/-3600/devices.json \
   | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f\"devices: {len(d)}\")'"

# Re-launch watchdog dashboard on Kali (exposed on LAN):
prlctl exec "Kali Linux 2025.2 ARM64" \
  "cd /home/parallels/CYT && nohup bash -c 'BIND_HOST=0.0.0.0 python3 watchdog_dashboard.py --kismet-url http://localhost:2501 --port 5002' > /tmp/watchdog.log 2>&1 &"
# Then browse http://10.211.55.12:5002 from Mac (requires ProtonVPN "Allow LAN" enabled)

# Cox hotspot verification (automatic at 15:58 scheduled wakeup; manual form):
prlctl exec "Kali Linux 2025.2 ARM64" \
  "curl -s -u kismet:watchdog2026 http://localhost:2501/devices/last-time/-1800/devices.json \
   | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(x[\"kismet.device.base.macaddr\"], x.get(\"kismet.device.base.last_time\")) for x in d if x.get(\"kismet.device.base.macaddr\") in (\"6C:55:E8:7A:29:78\", \"6C:55:E8:7A:29:80\")]'"

# Stop Kismet when done:
prlctl exec "Kali Linux 2025.2 ARM64" "pkill -9 kismet"
```

## Session Stats

- **Devices observed (66-min capture)**: 675
- **Operator household clients identified**: 5 online + 1 offline Litter-Robot = 6 total, all identified
- **Commits pushed**: 7
- **Field reports written**: 3 (totaling ~86 KB)
- **pytest baseline held**: 64/64 passing throughout

---

**Status**: Complete (scheduled wakeup at 15:58 pending) | **Confidence**: High
