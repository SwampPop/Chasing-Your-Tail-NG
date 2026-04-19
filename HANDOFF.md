# Handoff Document — CYT-NG

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-19 20:00 CDT
**Latest Session Duration**: ~2 h evening (delta analysis + supplemental report + clean shutdown)

## Goal

Maintain CYT-NG as an ongoing passive-monitoring platform for operator's residential RF environment. Close out HN-012 (Cox public-hotspot opt-out, now confirmed non-self-resolvable — pending Cox Tier 2 phone call).

## Progress Summary — 2026-04-19 (two sessions)

### Morning (restoration + Cox verification)
- ✅ Restored CYT-NG platform from Mac shutdown (Alfa re-seat required)
- ✅ Kismet + dashboard back online
- ✅ Empirically proved Cox self-service opt-out failed (pre-/post-reboot bracket)
- ✅ Cox call-script filed to Desktop

### Evening (delta + supplemental report + shutdown)
- ✅ Delta-analyzed 4-hour capture: 666 devices, 58 probers, 40 new arrivals in last 10 min
- ✅ Discovered **10 camera detections** in `watchdog_live.db` (Nest ×4, TP-Link ×4, Reolink ×1, Ubiquiti ×1)
- ✅ HN-008 ("No surveillance infra") SUPERSEDED by HN-019 (neighbor cameras present)
- ✅ 6 new findings documented: HN-019 through HN-024
- ✅ `SUPPLEMENTAL_FIELD_REPORT_2026-04-19.md` (HNFR-SUPP-001, 20 KB) filed to both locations
- ✅ Kismet + dashboard clean-shutdown — no orphan processes, DB preserved for next session

## Current State

- **Git**: clean, `9512b9c` HEAD, in sync with origin/main
- **Kali VM**: running, idle (nothing active except OS)
- **Kismet**: **STOPPED** (clean shutdown this evening)
- **Dashboard**: **STOPPED**
- **Alfa + GPS**: still passed through to Kali
- **watchdog_live.db on Kali**: preserved (24 KB, 10 camera detections baseline)
- **Field reports**: 3 original (2026-04-18) + 1 supplemental (2026-04-19) + 1 Cox call-script (Desktop)
- **Blocker**: user needs to call Cox Tier 2 (HN-012)

## What Worked

- **Sqlite detection-log discovery**: checking `/home/parallels/CYT/watchdog_live.db` after 4+ hours of capture revealed the 10 camera detections we missed yesterday. Demonstrates the importance of longer observation windows.
- **Supplemental report format**: cleaner than editing three dated reports. New findings IDs (HN-019–HN-024) extend the existing numbering cleanly; old findings get status updates in a table.
- **Bracket-around-reboot verification**: capturing Cox VAP state pre- and post-user-reboot definitively closed the "did reboot help?" question.

## What Didn't Work

- **Self-service Cox hotspot opt-out**: click-through completed yesterday, empirically disproven today. Documented as anti-pattern (HN-024).
- **Gateway reboot as public-hotspot mitigation**: same — boot just re-pulls same DOCSIS config.

## Next Steps

1. **User calls Cox Tier 2** (1-800-234-3993). Script: `~/Desktop/COX_HOTSPOT_OPT_OUT_FOLLOWUP_2026-04-19.md`. Explicitly reference BSSIDs `:78` and `:80`, CM MAC `6C:55:E8:7A:29:6F`, serial `212930060123104946`.
2. After Cox confirms: wait 10–15 min for propagation, tell ARES-1 "check now".
3. ARES-1 restarts Kismet + dashboard, runs verification query, updates HN-012 → CLOSED across reports if successful.
4. Optional: if operator wants, longer runtime continues to accumulate camera / transient-prober data for weekly trend analysis.

## Blockers

- **HN-012**: blocked on operator phone call to Cox. Not actionable from code / own side.

## Key Files

**Fresh this evening**:
- `~/my_projects/2_reference_docs/docs/network/SUPPLEMENTAL_FIELD_REPORT_2026-04-19.md` + Desktop copy

**Still-current from earlier sessions**:
- 3 2026-04-18 field reports (HNFR-001, WPS-001, HDP-001)
- `~/Desktop/COX_HOTSPOT_OPT_OUT_FOLLOWUP_2026-04-19.md` (call script)

**Session logs**:
- `~/AI-Sessions/logs/session-2026-04-19.md` (morning)
- `~/AI-Sessions/logs/session-2026-04-19-evening.md` (this evening)

## Commands to Resume

```bash
# Re-start Kismet + dashboard on Kali after Mac/VM wake:
prlctl exec "Kali Linux 2025.2 ARM64" "iw dev wlan0 info 2>&1 | grep type"
# If "no wlan0": physically re-seat Alfa USB first

prlctl exec "Kali Linux 2025.2 ARM64" "airmon-ng check kill && airmon-ng start wlan0"
prlctl exec "Kali Linux 2025.2 ARM64" "cd /home/parallels/CYT && ./start_kismet_clean.sh wlan0"
prlctl exec "Kali Linux 2025.2 ARM64" \
  "cd /home/parallels/CYT && nohup bash -c 'BIND_HOST=0.0.0.0 python3 watchdog_dashboard.py --kismet-url http://localhost:2501 --port 5002' > /tmp/watchdog.log 2>&1 &"

# Post-Cox-call verification (one-liner):
prlctl exec "Kali Linux 2025.2 ARM64" \
  "curl -s -u kismet:watchdog2026 http://localhost:2501/devices/last-time/-600/devices.json \
   | python3 -c 'import json,sys; d=json.load(sys.stdin); now=max(x.get(\"kismet.device.base.last_time\",0) for x in d); [print(x[\"kismet.device.base.macaddr\"], \"age:\", now-x.get(\"kismet.device.base.last_time\",0), \"sec\") for x in d if x.get(\"kismet.device.base.macaddr\") in (\"6C:55:E8:7A:29:78\",\"6C:55:E8:7A:29:80\")]'"

# Query detection database (persistent across sessions):
prlctl exec "Kali Linux 2025.2 ARM64" \
  "sqlite3 -header -column /home/parallels/CYT/watchdog_live.db 'SELECT * FROM detections ORDER BY rowid DESC LIMIT 15;'"
```

## Session Stats

- Devices in 4-hour window: 666
- Camera detections in DB: 10 (across yesterday + today)
- Probers captured: 58
- Operator VAPs visible: 10 / 10
- Commits this evening: 0 (clean git state; supplemental report lives in private reference_docs)

---

**Status**: Complete — platform at rest | **Confidence**: High | **Blocker**: Cox Tier 2 call pending
