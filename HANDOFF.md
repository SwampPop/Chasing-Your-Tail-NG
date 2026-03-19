# Handoff Document - CYT Live Capture Routing

**Created**: 2026-01-25 13:10
**Last Updated**: 2026-03-18 20:22
**Session Duration**: Evening session

## Goal

Get CYT fully operational with live Kismet capture feeding from the Kali VM through the Parallels shared folder to the macOS GUI — so the "TELEMETRY STALE" banner clears on a real wardrive.

---

## Progress Summary

- Reviewed and committed CODEX's four-file patch set (`f14e338`)
- Pushed all pending commits to origin/main — repo fully synced
- Confirmed Mac-side `.kismet` directory exists with 7 historical files
- Verified `getmtime` fix correctly selects `Kismet-20251213-06-40-32-1.kismet` as newest
- Operational end-to-end test staged and ready — pending VM execution

---

## Current State

**Codebase**: Clean. All tests passing (30 Python, shell syntax clean). Two commits ahead from this work cycle.

**Live capture routing** (new — not yet tested end-to-end):
```
VM Kismet writes to:  /media/psf/Home/Library/Mobile Documents/.../Documents_Local_Clean/IT/Chasing-Your-Tail-NG
Mac CYT reads from:   /Users/REDACTED/Library/Mobile Documents/.../Documents_Local_Clean/IT/Chasing-Your-Tail-NG
```
Both resolve to the same physical directory via Parallels shared folder. The `.kismet` files in that directory are Sep–Dec 2025 historical captures. Next live wardrive will write a fresh file there.

**Python environment**: `.venv` (Python 3.12) — use this, not system Python 3.14.

---

## What Worked

- `getmtime` fix — correct key for newest capture; `getctime` was wrong on macOS (metadata change time, not data write time)
- Config-driven log path — `kismet_logs_vm` in config.json; scripts read it via inline Python at runtime
- `--log-prefix` flag — correct Kismet CLI flag for controlling output directory; replaces fragile `cd` workaround

## What Didn't Work / Residuals

- Operational test not yet run — VM must be running to verify the full chain
- `wardrive.sh:184` — stop summary still echoes hardcoded `/home/parallels/CYT/my_wigle_export.py` (cosmetic only)
- Other VM helpers (attacker_hunter.py etc.) may still reference old `/home/parallels/CYT/logs/kismet` path

---

## Next Steps

1. **Run operational end-to-end test** (requires VM):

   In VM terminal:
   ```bash
   # Confirm shared folder accessible
   ls -la "/media/psf/Home/Library/Mobile Documents/com~apple~CloudDocs/Documents_Local_Clean/IT/Chasing-Your-Tail-NG/" | grep kismet

   # Start Kismet via patched script
   cd /home/parallels/Chasing-Your-Tail-NG
   sudo ./start_kismet_clean.sh wlan0
   # Should print: Using log prefix: /media/psf/Home/Library/...

   # Confirm new .kismet file being written
   ls -lt "/media/psf/Home/Library/Mobile Documents/com~apple~CloudDocs/Documents_Local_Clean/IT/Chasing-Your-Tail-NG/"*.kismet | head -3
   ```

   On Mac:
   ```bash
   # Confirm same file visible
   stat -f "%Sm %N" -t "%Y-%m-%d %H:%M:%S" "/Users/REDACTED/Library/Mobile Documents/com~apple~CloudDocs/Documents_Local_Clean/IT/Chasing-Your-Tail-NG/Kismet"*.kismet | sort | tail -3

   # Launch CYT
   cd "/Users/REDACTED/Library/Mobile Documents/com~apple~CloudDocs/my_projects/0_active_projects/Chasing-Your-Tail-NG"
   source .venv/bin/activate
   python cyt_gui.py
   ```

   **Success indicator**: TELEMETRY STALE banner clears; live feed shows active devices.

2. **If test passes**: snapshot the VM (`prlctl snapshot CYT-Kali --name "Shared-Folder-Live-Capture-Working"`)

3. **Clean up**: fix `wardrive.sh:184` hardcoded wigle path

---

## Blockers

None — code is committed and correct. Operational test is the only remaining gate.

---

## Key Files

| File | Changes |
|------|---------|
| `config.json` | Added `kismet_logs_vm` key |
| `start_kismet_clean.sh` | `get_log_prefix()` + `--log-prefix` flag |
| `wardrive.sh` | `get_vm_kismet_logs_dir()`, all hardcoded paths replaced |
| `start_wardrive.sh` | Same pattern as wardrive.sh |
| `lib/gui_logic.py:35` | `getctime` → `getmtime` |
| `chasing_your_tail.py:120` | `getctime` → `getmtime` |
| `.venv/` | Python 3.12 venv, all deps including Kivy SDL2 |

---

## Git Status

**Latest commits**:
- `f14e338` — fix: route Kismet log output through Parallels shared folder
- `18efccb` — fix: stabilize CYT UI and Kismet DB selection

**Remote**: https://github.com/SwampPop/Chasing-Your-Tail-NG.git — fully synced

---

**Session Status**: Paused — awaiting operational VM-side test
**Confidence**: High — code is correct; test is execution-only
