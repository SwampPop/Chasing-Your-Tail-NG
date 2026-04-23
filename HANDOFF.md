# Handoff Document — CYT-NG

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-22 18:00 CDT
**Latest Session Duration**: ~12 h (UI unification + AttackerHunter integration + eventbus client + reports bundle)

## Goal

Evolve CYT-NG from a passive-monitoring platform into a unified "mission control" real-time counter-surveillance dashboard with:
- Real-time delivery (SocketIO push, not page refresh)
- Full active-attack detection surface (DEAUTH / DISASSOC / KARMA / APSPOOF)
- Editable UI (templates + CSS + JS, not embedded Python strings)
- Sub-second alert latency via Kismet eventbus subscription
- Longitudinal device profiling (follower-candidate classifier) — design complete, implementation pending
- Platform portability toward a dedicated sensor (Jetson/Pi) — design complete, build pending

## Progress Summary — 2026-04-22

### Mission-control UI unification

- ✅ Extracted embedded `DASHBOARD_HTML` string (was 120 lines in `watchdog_dashboard.py`) into Jinja templates + static CSS/JS
- ✅ `templates/_base.html`, `dashboard.html`, `_panel_detections.html`, `_panel_devices.html`, `_panel_alerts.html`
- ✅ `static/css/mission_control.css` (CSS variables, attack-flash animation)
- ✅ `static/js/socket_client.js` (SocketIO client, DOM updates, HTML-escape)
- ✅ Browser reload is sufficient for visual changes — no Python restart needed

### Real-time push (replaces meta-refresh)

- ✅ SocketIO emits wired: `system_status`, `device_update`, `detection`, `attack_alert`
- ✅ Threading-mode SocketIO (no eventlet conflict with asyncio/bleak)
- ✅ Attack alerts rate-limited 1/sec/MAC; persistence unaffected
- ✅ UI gate `UI_SURFACE_ATTACK_TYPES = {DEAUTH, DISASSOC, TARGETING}` — soft heuristics persist to DB but don't flash banner

### AttackerHunter integration (formerly orphaned)

- ✅ Added `alert_callback=None` kwarg to `AttackerHunter.__init__`; invoked from `alert()`
- ✅ `on_attack_alert()` in dashboard normalizes AttackerHunter output → classifier → DB + SocketIO
- ✅ `_classify_attack()` derives (attack_type, severity, count) from flag set
- ✅ `attacks` table added to `watchdog_live.db` via `DetectionLogger.log_attack()`
- ✅ REST-polling path auto-skips Kismet alert fetch when eventbus is connected (no double-fire)

### Kismet eventbus WebSocket client

- ✅ New module `kismet_eventbus.py` — `KismetEventbusClient` class, threaded, exponential-backoff reconnect
- ✅ Subscribes to `ALERT` + `TIMESTAMP` topics by default
- ✅ `--eventbus` CLI flag on dashboard (off by default — safe fallback to REST polling)
- ✅ `_handle_eventbus_message()` translates Kismet ALERT shape → AttackerHunter alert shape → `on_attack_alert`
- ✅ Verified end-to-end on live Kismet: sub-second latency (log line `kismet eventbus connected: topics=ALERT,TIMESTAMP`)

### Test coverage

- ✅ 64 → 94 passing (+30 net, includes previously-skipped BLE tests now running with `bleak` installed)
- ✅ 7 new tests: `test_socketio_emit.py`
- ✅ 2 new tests: `test_attacker_integration.py`
- ✅ 6 new tests: `test_kismet_eventbus.py`
- ✅ Zero regressions in pre-existing suite

### Documentation

- ✅ `docs/GREENFIELD_MOBILE_SENSOR_DESIGN.md` — comprehensive design for a mobile counter-surveillance sensor (~800 lines). Covers hardware tiers, software stack, follower-candidate classifier algorithm, LLM integration, operator UX, security/OPSEC, deployment scenarios.
- ✅ `~/Desktop/CYT-NG-Reports-2026-04-22/` — 5-file reports bundle (~3,100 lines total):
  - `00_README.md` (navigation + cross-document narrative)
  - `01_CYT-NG_Current_State_Report.md` (architecture, shortcomings, friction, technical debt)
  - `02_Tier_II_Professional_Build_with_HackRF.md` (~$2,500 Jetson Orin Nano Super build)
  - `03_Tier_III_Individual_Operator_Build.md` (~$5,200 AGX Orin + DF + hardened OPSEC)
  - `04_TSCM_Industry_Teams_Training_Gear.md` (industry overview, methodology, gear catalog)

### Session hygiene fixes (unrelated but urgent)

- ✅ Diagnosed + resolved 278 GiB disk exhaustion (runaway `/tmp/security-audit-2026-04.log` from misconfigured launchd `com.security.monthly-compliance-audit.plist` with `RunAtLoad=true`)
- ✅ launchd plist unloaded; underlying audit-script bug (unbounded output) left for operator review

## Current State

- **Git**: `7b70d8a` + uncommitted session work (ready to commit at session close)
- **Kali VM**: running; Kismet PID varies, wlan0 in monitor mode (fragile — lost twice during VM restarts today)
- **Mac dashboard**: running on port 5002 with `--eventbus` active at last check; PID 81256
- **Hardware**: Alfa AWUS1900 (RTL8814AU) + u-blox 8 GNSS both connected to VM; operator re-toggled after VM restart flapped them
- **Database**: `watchdog_live.db` retained with latest session's detections + false-positive `BRIEF` attack rows (can be cleared via `DELETE FROM attacks WHERE attack_type='BRIEF'`)
- **ProtonVPN**: off at session close — would re-hijack `10.211.55.12` via utun8 if reconnected
- **Disk**: 287 GiB free (was 102 MiB before session cleanup)

## What Worked

- **Extract HTML first, then add SocketIO second** — staging the template extraction as a separate, byte-identical refactor before adding real-time features kept regressions to zero
- **UI gating for attack types** — adding `UI_SURFACE_ATTACK_TYPES` allowlist at the emit step (not the classifier) preserved AttackerHunter's full audit trail while killing the false-positive banner storm on every passing randomized-MAC phone
- **Rate-limit at the fan-out, persist without rate limit** — correct design for deauth floods: every alert is logged, UI gets a max of 1/sec/MAC with accumulated count
- **Eventbus client designed with tests BEFORE integration** — WS + reconnect + shutdown tested via mock socket first, live integration was trivial after
- **Reports bundle approach for off-session reference** — when user signaled session end + cross-project reference, 5-file markdown bundle on Desktop is easier to consume than chat history
- **Greenfield design doc as a lens, not a prescription** — framing it as "if starting from scratch" surfaces architectural choices without requiring immediate action

## What Didn't Work

- **Proton VPN kill-switch + split-tunnel mutual exclusion** — per operator, Proton on macOS cannot have split-tunnel exclusions while kill-switch is on. This means eventbus (direct WS to VM) and Proton are mutually exclusive until a different workaround ships (prlctl-exec WS bridge, Parallels Bridged networking, or VM at a different subnet).
- **RTL8814AU driver** stubbornly reverts to `type managed` via Kismet's cap helper in daemonize mode. Manual `iw` command works reliably but has to be issued after each VM restart.
- **Parallels USB auto-connect** appears checkmarked in the menu but doesn't re-establish pass-through on VM resume. Requires manual uncheck+recheck. Parallels config-level auto-connect exists but isn't set.
- **My initial Pi cost estimate was too low** ($100) — operator correctly noted retail reality is $175+ for the Pi 5 8GB alone; realistic kit is $270 minimum. Corrected in reports.
- **Homebrew vs .venv Python confusion** bit the operator once — dashboard started with system Python and bleak absent; recovered by explicit `.venv/bin/python` invocation. Preflight check recommended.

## Next Steps

Operator is switching context to the `pentest/` directory. CYT-NG work pauses. Before resuming:

### Priority 1 (platform stability — ~4 hours total)

1. Install `realtek-rtl88xxau-dkms` in Kali VM (aircrack-ng fork, permanent monitor-mode fix)
2. Add `unmanaged-devices=interface-name:wlan0` to VM's NetworkManager config
3. Create `/etc/systemd/system/kismet.service` for auto-start on VM boot
4. Parallels: Configure → Hardware → USB & Bluetooth → "Connect automatically" for 802.11ac NIC + u-blox GNSS
5. Dashboard Python-env preflight (shebang + `bleak`/`flask_socketio` import check)

### Priority 2 (capability expansion)

6. **HackRF** — operator confirmed purchase planned regardless of project. When it arrives:
   - Wire `imsi_detector.py` (stub exists, unwired) to HackRF + gr-gsm
   - Add sub-GHz ISM scanner (433/868/915) for covert-tracker detection
   - Add broadband spectrum panel to dashboard
7. Wire `flock_detector.py` (stub exists, unwired) to dashboard
8. Implement follower-candidate classifier per greenfield doc §6 (location clustering + temporal + co-occurrence rules)

### Priority 3 (platform migration decision — 3 months out)

9. **Decide**: stay Mac+VM vs migrate to dedicated Pi/Jetson sensor
10. If migrating: execute Tier II build per `~/Desktop/CYT-NG-Reports-2026-04-22/02_Tier_II_Professional_Build_with_HackRF.md`

### Priority 4 (long-term)

11. LLM integration (Ollama-based natural-language alerts, profile reasoning)
12. Watchlist UI port from Kivy GUI to web dashboard (Alpine.js modal)
13. Mobile-first PWA rework of dashboard
14. Consider annual professional TSCM sweep for dormant-device / wireline coverage that SDR cannot reach

## Blockers

- **None blocking immediate work**. Operator switched context voluntarily, not due to blockers.
- **Pending (external)**: HN-012 Cox Tier 2 phone call still open from previous sessions (unchanged)
- **Pending (VM config)**: all Priority 1 items are one-time setup, no dependencies beyond operator time

## Key Files

### New this session
- `kismet_eventbus.py` — Kismet eventbus WS client
- `templates/_base.html`, `templates/dashboard.html`, `templates/_panel_{detections,devices,alerts}.html` — mission-control UI
- `static/css/mission_control.css` — NASA-grade dark theme with attack-banner flash
- `static/js/socket_client.js` — SocketIO client, DOM updates, HTML-escape
- `tests/test_socketio_emit.py` (7 tests)
- `tests/test_attacker_integration.py` (2 tests)
- `tests/test_kismet_eventbus.py` (6 tests)
- `docs/GREENFIELD_MOBILE_SENSOR_DESIGN.md` — not committed (docs/ is gitignored)

### Modified
- `watchdog_dashboard.py` — removed embedded HTML, added emit helpers + AttackerHunter wiring + eventbus client integration + UI-gating logic
- `watchdog_reporter.py` — added `attacks` table + `log_attack()` + `get_recent_attacks()`
- `attacker_hunter.py` — added `alert_callback` kwarg and invocation from `alert()`
- `.gitignore` — added `attacker_detections.json`, `attacker_hunt.log` (runtime operational data)

### Off-project (on Desktop)
- `~/Desktop/CYT-NG-Reports-2026-04-22/` — 5-file professional report bundle

## Commands to Resume

```bash
# Return to project
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG

# Check VM + Kismet state
prlctl list --all
prlctl exec "Kali Linux 2025.2 ARM64" "pgrep -a kismet; iw dev wlan0 info | grep type"

# Restart Kismet if wlan0 lost monitor mode (almost guaranteed after VM restart)
prlctl exec "Kali Linux 2025.2 ARM64" "sudo pkill -9 kismet; sleep 2; sudo ip link set wlan0 down; sudo iw dev wlan0 set type monitor; sudo ip link set wlan0 up; sudo /usr/bin/kismet -c wlan0 --daemonize --log-prefix /home/parallels/CYT/logs"

# Start dashboard (remember .venv!)
.venv/bin/python watchdog_dashboard.py --kismet-url http://10.211.55.12:2501 --kismet-pass watchdog2026 --eventbus

# Full test suite
.venv/bin/python -m pytest tests/

# Open reports bundle for reference
open ~/Desktop/CYT-NG-Reports-2026-04-22/
```

## Session Stats

- **Tests**: 94 passing (was 64) — +30 net
- **New lines of production code**: ~550
- **New test lines**: ~400
- **Files created**: 13 (not counting reports bundle)
- **Lines of documentation shipped**: ~3,900 (greenfield + reports bundle + this handoff)
- **Disk freed**: 278 GiB
- **Uncommitted work size**: ~1,500 diff lines ready for session-close commit
