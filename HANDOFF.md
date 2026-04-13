# Handoff Document — CYT-NG + Cross-Project Session

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-13 01:30 CDT
**Session Duration**: ~1 hour (pentest remediation — osquery + Zeek)

## Goal

Original: Stabilize CYT-NG for field deployment, harden OPSEC, achieve GREEN security posture.
This session: Recover from unexpected shutdown, close pentest commit gap, deploy Perplexity terminal/MCP integration, assess mempalace coverage for agent projects.

## Progress Summary

### Prior Sessions (Complete — preserved from last handoff)
- 6-phase CYT-NG stabilization, 64 tests passing, security GREEN
- Kali VM deployment, TUI running live with 227+ devices
- PII remediation complete (git history rewritten, zero PII)
- 11 CVEs patched across 6 packages
- ARES-1 security audit: 37 findings resolved, 8/8 verification PASS
- macOS username rename scripts staged on Desktop

### This Session (2026-04-13)
- [x] Added 7 osquery detection queries to `pentest/baselines/phase1-2026-04-09/osquery_security.conf` (R-006/008/010/012/014/016/017)
- [x] Syntax-validated all 7 via osqueryi 5.21.0; live-fire positive tests passed for base64 + zip
- [x] Deployed to `/var/osquery/osquery.conf`, osqueryd kickstarted cleanly (PID 32149)
- [x] Built repo-tracked Zeek config in `pentest/zeek/`: local.zeek, node.cfg, scripts/dns-anomalies.zeek, deploy_zeek.sh, test_capture.sh, README.md
- [x] R-002 Zeek enhancements: MAC logging + Community ID + custom DNS anomaly detection (Long_Qname > 100, NXDOMAIN_Spike >=20/min)
- [x] Live-capture verified on en0: 88 packets, conn.log has orig/resp_l2_addr + community_id, 21 dns.log rows
- [x] Committed Santa lockdown baseline files (leftover from 2026-04-10)
- [x] AAR updated: 10 open findings → 2 (R-005 pending Wazuh, R-019 manual TCC)
- [x] All 5 commits pushed to SwampPop/pentest (`994bee7..526ca09`)

### Prior Session (2026-04-10)
- [x] Diagnosed unexpected shutdown — battery power `sleep 10` caused idle shutdown
- [x] Fixed: `sudo pmset -b sleep 0` — system no longer auto-sleeps on battery
- [x] Completed interrupted pentest commit (`503d992`) — 26 files, Phase 1 ATT&CK results
- [x] Installed `llm` CLI v0.30 + `llm-perplexity` plugin v2026.2.1
  - Venv: `~/.local/llm-env/`, symlinked to `~/.local/bin/llm`
  - 4 models: sonar, sonar-pro, sonar-deep-research, sonar-reasoning-pro
- [x] Installed official Perplexity MCP server v0.9.0 (version-pinned, local install)
  - Location: `~/.local/mcp-servers/node_modules/@perplexity-ai/mcp-server/`
  - Registered with Claude Code (needs API key + restart to activate)
- [x] Deep security research on all Perplexity integration options (5 options evaluated)
- [x] Mempalace audit: globally available but NOT indexed for ARES-1/HELIOS-1 knowledge bases
- [x] Memory saved: never push Workstation_Build_2026 or moroz to GitHub

## Current State

**CYT-NG codebase**: Unchanged this session. Still clean, 64 tests, security GREEN.
**Pentest project**: Commit completed (`503d992`). Not pushed to remote yet.
**Perplexity integration**: Installed but needs API key before first use.
**MCP server**: Registered but inactive — needs `PERPLEXITY_API_KEY` env var + Claude Code restart.

## What Worked
- Battery power investigation via `pmset`, `sysctl kern.shutdownreason`, `kern.bootreason` — clean diagnosis
- Local npm install with version pinning instead of `npx -y` for MCP server — eliminates supply chain risk
- Dedicated venv for llm CLI (same pattern as mempalace) — avoids PEP 668 conflicts

## What Didn't Work
- Subagent for mempalace check failed (permission restrictions in Explore agent) — resolved by direct search
- Subagent for Perplexity research failed (no WebSearch access) — resolved by running research directly

## Next Steps

### Immediate (this session or next)
1. **Set Perplexity API key** — add `PERPLEXITY_API_KEY` to `~/.zshrc`, restart Claude Code
2. **Deploy pentest osquery gap-closing queries** — 7 new detection rules for R-006, R-008, R-010, R-012, R-014, R-016, R-017
3. **Enhance Zeek local.zeek** — MAC logging, community ID, DNS anomaly detection (R-002)
4. **Revoke Terminal TCC permissions** (R-019) — System Settings > Privacy > Screen Recording

### Queued
5. **Mine ARES-1/HELIOS-1 knowledge bases into mempalace** — populate `wing_agent`
6. **Create Claude project configs for ARES-1/HELIOS-1** under `~/.claude/projects/`
7. **CYT-NG Phase 1A directory restructuring** — capture/analysis/reporting/core/ui split
8. **macOS username rename** — execute from rescue account (scripts on Desktop)
9. **Push pentest commit to remote** — when ready

### Pentest Remediation Tracker (Open Items)
| ID | Finding | Can Close Offline? |
|----|---------|-------------------|
| R-002 | Zeek unconfigured | Yes — enhance local.zeek |
| R-005 | Shell profile persistence | Already has osquery query |
| R-006 | launchctl submit bypass | Yes — osquery process query |
| R-008 | Keychain export undetected | Yes — osquery process query |
| R-010 | osascript credential phishing | Yes — osquery process query |
| R-012 | Gatekeeper bypass | Yes — osquery process query |
| R-014 | Base64 decode-to-execute | Yes — osquery process query |
| R-016 | Clipboard monitoring | Yes — osquery process query |
| R-017 | Password-protected zip | Yes — osquery process query |
| R-019 | TCC revocation | Yes — manual GUI action |

## Blockers

- **Perplexity API key** — needed before `llm` or MCP server will function
- **Not on home network** — no network-dependent pentest testing (Phase 2-4 deferred)

## Key Files

### This Session (new/modified)
- `~/.local/llm-env/` — llm CLI venv
- `~/.local/bin/llm` — symlink to llm binary
- `~/.local/mcp-servers/node_modules/@perplexity-ai/mcp-server/` — pinned v0.9.0
- `~/.claude.json` — updated with perplexity MCP server config
- `pentest/` — commit `503d992` (26 files: AAR, baselines, reference docs)

### CYT-NG Untracked (from prior sessions)
- `alpr_context.py`, `ble_tracker_detector.py`, `camera_detector.py`
- `config/`, `drone_signature_matcher.py`, `templates/`, `watchdog_reporter.py`

### Memory
- `~/.claude/projects/.../memory/feedback_no_push_repos.md` — never push Workstation_Build_2026 or moroz

## Commands to Resume

```bash
# Set Perplexity API key (do this first)
echo 'export PERPLEXITY_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc

# Test llm CLI
llm -m sonar "test query"

# Restart Claude Code to activate MCP server
# Then verify: claude mcp list

# Deploy osquery gap-closing queries (needs sudo)
sudo nano /var/osquery/osquery.conf  # or let Claude update it

# CYT-NG tests (unchanged)
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG
python3 -m pytest tests/ -v

# Pentest — push when ready
cd ~/my_projects/0_active_projects/pentest
git push origin main
```
