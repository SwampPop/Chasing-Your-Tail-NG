# Handoff Document — CYT-NG

**Created**: 2026-04-08 23:00
**Last Updated**: 2026-04-19 10:00 CDT
**Latest Session Duration**: ~1 h (restore from shutdown + Cox opt-out verification)

## Goal

Keep CYT-NG operational for continuous passive RF monitoring, and close out HN-012 (Cox public-hotspot opt-out) now that we have empirical evidence the self-service path failed.

## Progress Summary — 2026-04-19 Session

- ✅ Restored CYT-NG platform from Mac shutdown (Alfa USB + Kismet + dashboard)
- ✅ Confirmed Cox hotspot VAPs (`:78` and `:80`) are **still beaconing** despite the 2026-04-18 self-service opt-out
- ✅ Gateway reboot by user did NOT stop the broadcast — diagnosis: opt-out never propagated to Cox DOCSIS provisioning backend
- ✅ Cox call-script + gateway identifiers filed to `~/Desktop/COX_HOTSPOT_OPT_OUT_FOLLOWUP_2026-04-19.md`
- 🔄 Pending: user calls Cox (1-800-234-3993), requests Tier 2 / provisioning escalation

## Current State

- **Git**: clean, `de68326` HEAD, in sync with origin/main
- **Kali VM**: running; Kismet active (PID 887942 main + 887989 capture subprocess) on `wlan0`
- **Dashboard**: running at `http://10.211.55.12:5002` (LAN-exposed; requires ProtonVPN "Allow LAN connections" on Mac)
- **GPS**: u-blox connected but **NO FIX** (indoors, geopoint `[0, 0]`)
- **Cox hotspot**: still active; user has a call to make
- **Reports**: 3 2026-04-18 field reports + 1 new Cox follow-up doc on Desktop & `2_reference_docs/docs/network/`

## What Worked

- **Immediate physical-first diagnosis** of the shutdown-recovery failure: when Kali had no `wlan0`, we correctly skipped to `lsusb` on Kali + `system_profiler` on Mac, identified the Alfa wasn't bussed at all, and asked user to re-seat instead of chasing software fixes.
- **Bracketing-the-reboot verification**: capturing Cox VAP state both before AND after the user's gateway reboot gave us definitive evidence the opt-out never reached Cox's backend. No ambiguity, no "did the reboot help?" loop.
- **Dedicated Desktop follow-up doc**: keeps the call script + gateway identifiers in one findable place for when the user actually calls Cox (sometimes days later).

## What Didn't Work

- **Cox self-service opt-out** (attempted 2026-04-18) — clicked through cox.com/myprofile flow, UI confirmed the toggle, but backend provisioning never picked it up. Will now require a human at Cox to push it.
- **Gateway reboot as a supposed fix** — reboot only re-pulls whatever config Cox has on file. If the opt-out isn't on file, reboot achieves nothing. Don't suggest this path again for other ISP-provisioned features without confirming the opt-out is actually recorded upstream.

## Next Steps

1. **User calls Cox** (1-800-234-3993) using the script in `~/Desktop/COX_HOTSPOT_OPT_OUT_FOLLOWUP_2026-04-19.md`; escalate to Tier 2 / network-provisioning
2. Wait 10–15 min after Cox confirms the change propagates
3. Run the Kismet verification pull (command inline in the Desktop doc) to confirm `:78` and `:80` are silent
4. **If confirmed silent**: update HN-012 to CLOSED across the 3 field reports in `2_reference_docs/docs/network/`
5. **If still active**: escalate via Cox social (@CoxHelp on Twitter/X) — some users report faster config-propagation from there than phone
6. Still-open from yesterday: BT adapter purchase for HN-009 coverage

## Blockers

- **HN-012 — Cox public hotspot**: blocked on operator phone call to Cox. Not actionable from code / own side.

## Key Files

**Fresh from this session**:
- `~/Desktop/COX_HOTSPOT_OPT_OUT_FOLLOWUP_2026-04-19.md` — the call script + MACs + serials

**Still-current from 2026-04-18**:
- 3 field reports (Desktop + `2_reference_docs/docs/network/`) — HOME_NETWORK_FIELD_REPORT, WPS_VULNERABILITY_TEST_REPORT, HOUSEHOLD_DEVICE_PROFILES

**Session log**:
- `~/AI-Sessions/logs/session-2026-04-19.md`

## Commands to Resume

```bash
# Verify Kismet still running:
prlctl exec "Kali Linux 2025.2 ARM64" "pgrep -af 'kismet -c'"

# Cox hotspot re-verification (run after Cox call + 10-min propagation wait):
prlctl exec "Kali Linux 2025.2 ARM64" \
  "curl -s -u kismet:watchdog2026 http://localhost:2501/devices/last-time/-600/devices.json \
   | python3 -c 'import json,sys; d=json.load(sys.stdin); now=max(x.get(\"kismet.device.base.last_time\",0) for x in d); [print(x[\"kismet.device.base.macaddr\"], \"age:\", now-x.get(\"kismet.device.base.last_time\",0), \"sec\") for x in d if x.get(\"kismet.device.base.macaddr\") in (\"6C:55:E8:7A:29:78\",\"6C:55:E8:7A:29:80\")]'"

# Expected SUCCESS result: either MACs not in output (no beacons in 10-min window), or age > 300 seconds.
# Expected FAILURE result: age < 120 seconds — still actively beaconing.

# Stop Kismet when ready:
prlctl exec "Kali Linux 2025.2 ARM64" "pkill -9 kismet"

# Stop dashboard:
prlctl exec "Kali Linux 2025.2 ARM64" "pkill -f watchdog_dashboard"

# Full restart from scratch (if USB needs re-seating):
# 1. Physically reseat Alfa USB if no wlan0
# 2. prlctl exec "Kali Linux 2025.2 ARM64" "airmon-ng check kill && airmon-ng start wlan0"
# 3. prlctl exec "Kali Linux 2025.2 ARM64" "cd /home/parallels/CYT && ./start_kismet_clean.sh wlan0"
# 4. prlctl exec "Kali Linux 2025.2 ARM64" "cd /home/parallels/CYT && nohup bash -c 'BIND_HOST=0.0.0.0 python3 watchdog_dashboard.py --kismet-url http://localhost:2501 --port 5002' > /tmp/watchdog.log 2>&1 &"
```

## Session Stats

- **Devices captured before session close**: 423 (in ~15-min fresh window, post-restart)
- **Cox VAPs status**: `:78` beaconing 1s ago, `:80` beaconing 9s ago (at last verification)
- **Operator VAPs**: 10 of 10 visible, 45,126 combined packets
- **Commits this session**: 0 (nothing to commit — no repo changes)

---

**Status**: Complete | **Confidence**: High | **Blocker**: Cox call pending
