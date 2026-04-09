# Handoff Document — CYT-NG Stabilization & OPSEC Hardening

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-09 08:00
**Session Duration**: Extended session (~9 hours)

## Goal

Stabilize CYT-NG for field deployment, get it running live on Kali VM, and harden OPSEC by purging all PII from the public GitHub repo.

## Progress Summary

### Phase 1: Stabilization (6 phases completed)
- Git triage of ~30 modified/untracked files — committed 22, deferred WATCHDOG prototypes
- Fixed 5 bare `except:` clauses across api_server.py, investigate_devices.py, wigle_export_filter.py, my_wigle_export.py
- Replaced `os.system()` shell injection in alert_manager.py TTS with `subprocess.Popen()`
- Added `_sql_safe_value()` defense-in-depth for 3 SQL injection points in cyt_proxy_server.py
- Moved hardcoded Kismet API credentials to environment variables in attacker_hunter.py
- Fixed division-by-zero crash in surveillance_detector.py persistence scoring
- Fixed ignore list new_count calculation bug in create_ignore_list.py
- Fixed `getctime` -> `getmtime` in create_ignore_list.py and investigate_devices.py
- Added `get_kismet_logs_path()` for cross-platform DB path resolution (macOS vs Kali)
- Added 34 new tests (30 -> 64 total), all passing
- Created `preflight.sh` pre-flight checklist script
- All work committed with conventional commit messages

### Phase 2: Kali VM Deployment
- Cloned repo to `~/CYT` on Kali
- Debugged Kismet capture issues:
  - Interface is `wlan0` (RTL8814AU), NOT `wlan0mon`
  - Stale Kismet processes holding port 3501 caused silent capture failures
  - Parallels shared folder incompatible with SQLite WAL mode — Kismet must write locally
  - Set `kismet_logs_vm` to `/home/parallels/CYT/logs`
- TUI running live with 227+ devices captured
- `diag.py` diagnostic script created for DB connectivity debugging

### Phase 3: PII Audit & Remediation
- Full security audit found 5 CRITICAL, 6 HIGH, 5 MEDIUM, 3 LOW findings
- Remediated ALL findings:
  - Real name, iCloud email, macOS username purged from all files and git history
  - WiGLE API token revoked and purged from history
  - CYT API key moved to environment variable
  - GPS coordinates replaced with generic NYC/Chicago across all files and history
  - Personal SSIDs (3) redacted from all files and history
  - Neighbor family name and MACs purged from history
  - Kismet password removed from shell scripts
  - Operational data files (device_aliases.json, signal_log.csv, threat_map, ignore lists, wigle tools) removed from tracking
  - `.gitignore` updated to prevent re-tracking
- Git history rewritten with `git filter-repo` (4 passes)
- Force-pushed clean history (159 commits, 0 PII matches)
- Git email set to `SwampPop@users.noreply.github.com`

### Phase 4: AI Toolchain Research
- Deployed 6 research agents covering 78+ AI tools
- Produced 8 reference documents (~25,000 words) at `~/my_projects/2_reference_docs/docs/ai_toolchain/`
- Round-table debrief with project-specific recommendations
- AAR with action items mapped to active projects
- User started Perplexity AI Pro trial

## Current State

**Codebase**: Clean. 64 tests passing. Zero PII in files or git history.

**Kali VM**: CYT cloned at `~/CYT`, Kismet capturing to `/home/parallels/CYT/logs`, TUI operational. Config updated locally for VM paths (not committed — machine-specific).

**GitHub**: Force-pushed clean history. All forks/clones need re-clone.

**Branches**: `main` only. `stabilization` branch was merged and can be deleted.

## What Worked

- **Preflight script** — caught every deployment issue (wrong DB path, missing deps, empty DB)
- **diag.py** — pinpointed the empty DB / Kismet capture failure quickly
- **`get_kismet_logs_path()`** — clean solution for macOS vs Linux path resolution
- **`git filter-repo`** with `--replace-text` and `--replace-message` — thorough PII purge across all history
- **Staged remediation** — fix current files first, then rewrite history, then force-push

## What Didn't Work

- **`git checkout-index -a -f`** during Phase 0 wiped working tree changes (recovered via remote)
- **Parallels shared folder** for Kismet DB writes — SQLite WAL mode incompatible, silent empty DBs
- **`wlan0mon`** interface name — actual monitor mode interface is `wlan0` on this hardware
- **First 3 filter-repo passes** missed PII in commit messages and variant coordinate formats — needed 4 total passes

## Next Steps

1. **Phase 1A: Directory restructuring** — the capture/analysis/reporting/core/ui split is documented in the plan but not executed. This is the key architectural change for cross-platform development.
2. **TUI improvements** — user expressed interest in modifying the terminal interface
3. **MCP server for Kismet DB** — highest-leverage tool integration (from AAR)
4. **Perplexity integration** into research workflow
5. **NotebookLM** for Paramedic_Doctrine content processing
6. **WATCHDOG modules** — camera_detector, ble_tracker, alpr_context, watchdog_reporter are untracked prototypes ready for integration when the time comes

## Blockers

- None currently. All systems operational.

## Key Files Modified

### Stabilization
- `alert_manager.py` — os.system -> subprocess.Popen for TTS
- `api_server.py` — bare except -> specific exceptions
- `cyt_proxy_server.py` — SQL safe value wrapper
- `attacker_hunter.py` — env var for Kismet creds
- `surveillance_detector.py` — division by zero guard
- `create_ignore_list.py` — count bug fix, getmtime fix
- `lib/gui_logic.py` — get_kismet_logs_path() added
- `cyt_tui.py`, `chasing_your_tail.py` — cross-platform path resolution
- `preflight.sh` — NEW, pre-flight checklist
- `diag.py` — NEW, DB diagnostic
- `tests/test_surveillance_detector.py` — NEW, 9 tests
- `tests/test_gps_tracker.py` — NEW, 14 tests
- `tests/test_ignore_loader.py` — NEW, 11 tests

### PII Remediation
- `config.json` — paths genericized
- `HANDOFF.md` — paths replaced with variables
- `watchdog_reporter.py` — real name removed, GPS defaults zeroed
- `generate_test_data.py` — real coords -> NYC
- `cyt_api_cors.py`, `dashboard.html`, `dashboard_local.html` — API key -> env var
- `start_wardrive.sh`, `stop_wardrive.sh` — Kismet password -> env var
- `.gitignore` — comprehensive operational data exclusions

### Research (in ~/my_projects/2_reference_docs/docs/ai_toolchain/)
- `00_AI_TOOLCHAIN_OVERVIEW.md` through `08_after_action_report.md`

## Commands to Resume

```bash
# On macOS — run tests
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
python3 -m pytest tests/ -v

# On Kali — start monitoring
cd ~/CYT
sudo killall -9 kismet 2>/dev/null
sudo kismet -c wlan0 --daemonize --log-prefix /home/parallels/CYT/logs
./preflight.sh
python3 cyt_tui.py

# On Kali — diagnostic
python3 diag.py
```
