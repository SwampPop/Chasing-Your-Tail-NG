# Handoff Document — CYT-NG Stabilization, OPSEC, & Security Audit

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-09 12:00
**Session Duration**: Extended (~13 hours across 2 sessions)

## Goal

Stabilize CYT-NG for field deployment, harden OPSEC, and achieve GREEN security posture.

## Progress Summary

### Stabilization (Complete)
- 6-phase stabilization executed (code quality, security, tests, ops)
- 34 new tests (64 total, all passing)
- `preflight.sh` and `diag.py` created
- Cross-platform `get_kismet_logs_path()` for macOS/Kali

### Kali VM Deployment (Complete)
- TUI running live with 227+ devices
- Kismet capturing to `/home/parallels/CYT/logs`
- Interface is `wlan0`, NetworkManager handoff handled by `start_kismet_clean.sh`
- Python venv at `~/.venv/cyt/` on Kali

### PII Remediation (Complete)
- Full audit: 19 findings, all resolved
- Git history rewritten (4 filter-repo passes), zero PII in 159 commits
- Git email: `SwampPop@users.noreply.github.com`
- WiGLE API token revoked

### Dependency Patching (Complete)
- Perplexity vulnerability scan: 11 CVEs across 6 packages
- All patched: urllib3 2.6.3, cryptography 46.0.7, Pillow 12.1.1, requests 2.33.0, Flask 3.1.3, Pygments 2.20.0

### Security Audit (Complete — GREEN)
- Full ARES-1 audit: 37 findings (6C, 9H, 10M, 4L, 8I)
- Perplexity PR #2 fixed 8 findings, merged
- 2 remaining items fixed (watchdog_dashboard bind, tracked pyc)
- Verification audit: 8/8 PASS
- Security posture: **GREEN**

### AI Toolchain Research (Complete)
- 6 research agents, 25,000+ words across 8 docs at `~/my_projects/2_reference_docs/docs/ai_toolchain/`
- Round-table debrief + AAR with project recommendations
- User started Perplexity AI Pro trial

### macOS Username Rename (Staged)
- Plan approved: `thomaslavoie` -> `snakedoctor`, full name `SD`
- `~/Desktop/rename_phase1.sh` — run from rescue account
- `~/Desktop/rename_phase2.sh` — run as snakedoctor after login
- 129 hardcoded references mapped, all covered by scripts

## Current State

**Codebase**: Clean. 64 tests passing. Zero PII. 11 CVEs patched. Security posture GREEN.

**Kali VM**: CYT cloned at `~/CYT`, venv at `~/.venv/cyt/`, Kismet logs to `/home/parallels/CYT/logs`.

**GitHub**: Clean history, all fixes pushed, PR #2 merged.

**Pinned for later**: Telegram bot + WiGLE credential setup for live alerts.

## Next Steps

1. **macOS username rename** — execute tonight from rescue account
2. **Phase 1A directory restructuring** — capture/analysis/reporting/core/ui split
3. **TUI improvements** — user wants to customize
4. **MCP server for Kismet DB** — highest-leverage tool integration
5. **Telegram/WiGLE credential setup** — enable live alerts

## Blockers

None.

## Key Files

### This Session
- `requirements.txt` — 6 packages patched for CVEs
- `api_server.py` — Flask debug off by default, localhost binding
- `cyt_proxy_server.py` — auth required at startup, 401 on missing key
- `spider_core.py` — UDP IP allowlist
- `watchdog_dashboard.py` — localhost binding
- `start_wardrive.sh`, `stop_wardrive.sh` — hard-fail on missing KISMET_PASS
- `.gitignore` — cyt_history.db, watchlist.db, *.pyc added
- `preflight.sh` — sections 7-8 added (log dir, interface check)
- `start_kismet_clean.sh` — NetworkManager handoff added

### Rename Scripts (Desktop)
- `~/Desktop/rename_phase1.sh` — Phase 1 (from rescue account)
- `~/Desktop/rename_phase2.sh` — Phases 2-6 (from snakedoctor)

### Research (reference docs)
- `~/my_projects/2_reference_docs/docs/ai_toolchain/00-08` — 9 documents

## Commands to Resume

```bash
# macOS — run tests
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
python3 -m pytest tests/ -v

# Kali — start monitoring
cd ~/CYT && git pull origin main
sudo bash start_kismet_clean.sh wlan0
sleep 5 && ./preflight.sh
~/.venv/cyt/bin/python3 cyt_tui.py

# Kali — diagnostic
python3 diag.py

# macOS — username rename (tonight)
# 1. Create rescue admin account first
# 2. Log out, log in as rescue
bash /Users/thomaslavoie/Desktop/rename_phase1.sh
# 3. Log out rescue, log in as snakedoctor
bash ~/Desktop/rename_phase2.sh
```
