# CYT Comprehensive Testing Guide

**Systematic testing procedures for validating all CYT features**

This guide provides step-by-step test scenarios with expected outputs and pass/fail criteria.

---

## 📋 Testing Overview

**Testing Phases**:
1. **Pre-Flight Checks** (5 min) - Verify environment ready
2. **Component Tests** (15 min) - Test each component individually
3. **Integration Tests** (30 min) - Test components working together
4. **Feature Tests** (45 min) - Test all detection features
5. **Stress Tests** (2 hours) - Long-running reliability
6. **Production Validation** (24 hours) - Final production check

**Total Time**: ~4 hours active testing + 24 hours monitoring

---

## ✅ Pre-Flight Checks (5 minutes)

### Test 1: Environment Verification

```bash
# 1. Check Python version
python3 --version
# PASS: 3.9.0 or newer
# FAIL: 3.8.x or older

# 2. Check installed dependencies
python3 -c "import flask, requests, jsonschema; print('✓ All dependencies installed')"
# PASS: No errors, message printed
# FAIL: ImportError

# 3. Verify wireless interface
iwconfig
# PASS: Shows wireless interface (wlan0, wlan1, etc.)
# FAIL: No wireless extensions found

# 4. Check Kismet installed
kismet --version
# PASS: Shows version number
# FAIL: command not found

# 5. Verify config valid
python3 config_validator.py
# PASS: ✓ Configuration is VALID
# FAIL: Error messages
```

**Expected Results**:
- All 5 checks PASS
- If any FAIL, fix before proceeding

---

## 🔧 Component Tests (15 minutes)

### Test 2: Wireless Adapter - Monitor Mode

**Purpose**: Verify adapter supports monitor mode

```bash
# 1. Put adapter in monitor mode
sudo airmon-ng start wlan0

# 2. Verify monitor interface created
iwconfig
# PASS: Shows wlan0mon (or similar) in Mode:Monitor
# FAIL: No monitor mode interface

# 3. Test packet capture
sudo airodump-ng wlan0mon
# PASS: Shows networks/devices being captured
# FAIL: No networks appear or errors

# 4. Stop capture (Ctrl+C)

# 5. Stop monitor mode
sudo airmon-ng stop wlan0mon
```

**Pass Criteria**:
- Monitor interface created ✓
- Packets captured ✓
- Can stop cleanly ✓

**Fail Actions**:
- Check adapter chipset (see HARDWARE_REQUIREMENTS.md)
- Try different adapter
- Update drivers

---

### Test 3: Kismet - Standalone Operation

**Purpose**: Verify Kismet works independently

```bash
# 1. Put adapter in monitor mode
sudo airmon-ng start wlan0

# 2. Start Kismet
sudo ./start_kismet_clean.sh wlan0mon

# 3. Wait 30 seconds

# 4. Check Kismet running
pgrep kismet
# PASS: Shows PID numbers (e.g., 12345 12346)
# FAIL: No output

# 5. Check database created
ls -lh /tmp/kismet/*.kismet
# PASS: Shows .kismet file with growing size
# FAIL: No file or size not changing

# 6. Stop Kismet
sudo pkill kismet
```

**Pass Criteria**:
- Kismet process starts ✓
- Database file created ✓
- File size increases (capturing packets) ✓

**Expected Output**:
```
-rw-r--r-- 1 root root 1.2M Dec  1 15:30 /tmp/kismet/Kismet-20251201-15-30-45-1.kismet
```

---

### Test 4: CYT Monitor - Standalone

**Purpose**: Verify CYT Monitor runs without daemon

```bash
# 1. Ensure Kismet is running (from Test 3)
pgrep kismet  # Should show PIDs

# 2. Start CYT Monitor
python3 chasing_your_tail.py

# Expected output within 30 seconds:
# --- CYT Monitoring Session Started ---
# Validating configuration...
# ✓ Configuration validation passed
# Loading configuration and credentials...
# [Password prompt - enter your master password]
# ...
# Starting secure CYT monitoring loop...

# 3. Let run for 2 minutes, observe output

# 4. Stop (Ctrl+C)
```

**Pass Criteria**:
- Starts without errors ✓
- Loads configuration ✓
- Connects to Kismet database ✓
- Shows monitoring loop messages ✓
- Gracefully stops on Ctrl+C ✓

**Expected Logs**:
```
2025-12-01 15:35:20 - INFO - 15 MACs added to the Past 5 minutes list
2025-12-01 15:35:20 - INFO - Starting secure CYT monitoring loop...
2025-12-01 15:35:20 - INFO - Performing Kismet health check (cycle 5)
```

---

### Test 5: Daemon - Process Management

**Purpose**: Verify daemon can start/stop all components

```bash
# 1. Ensure everything stopped
python3 cyt_daemon.py status
# All should show STOPPED

# 2. Start daemon
sudo python3 cyt_daemon.py start

# PASS: All components start successfully
# Expected output:
============================================================
Starting CYT System
============================================================

▶ Starting Kismet...
✓ Kismet started (PID: 12345)

▶ Starting CYT Monitor...
✓ CYT Monitor started (PID: 12346)

============================================================
✓ CYT System Started Successfully
============================================================

# 3. Verify status
python3 cyt_daemon.py status

# PASS:
# ✓ Kismet               RUNNING (PID: 12345)
# ✓ CYT Monitor          RUNNING (PID: 12346)

# 4. Stop daemon
sudo python3 cyt_daemon.py stop

# PASS: All components stop gracefully

# 5. Verify stopped
python3 cyt_daemon.py status
# All should show STOPPED
```

**Pass Criteria**:
- All components start ✓
- PIDs recorded ✓
- All components stop cleanly ✓
- Status accurate ✓

---

## 🔗 Integration Tests (30 minutes)

### Test 6: Health Monitoring Integration

**Purpose**: Verify health monitoring detects failures

```bash
# 1. Start system
sudo python3 cyt_daemon.py start

# 2. Verify health monitoring enabled
tail -f logs/cyt_monitor.log | grep -i "health monitoring"
# PASS: Should see "Kismet health monitoring enabled"

# 3. Wait for first health check (up to 5 minutes)
tail -f logs/cyt_monitor.log | grep -i "health check"

# Expected (healthy):
# INFO - Performing Kismet health check (cycle 5)
# DEBUG - ✓ Kismet health check passed

# 4. Simulate failure - kill Kismet
sudo pkill kismet

# 5. Wait for next health check
# Expected (failure detected):
# ERROR - ⚠️  Kismet health check FAILED: Kismet process not running

# 6. Stop system
sudo python3 cyt_daemon.py stop
```

**Pass Criteria**:
- Health checks run every 5 cycles ✓
- Healthy Kismet passes checks ✓
- Failed Kismet detected within one check cycle ✓
- Error logged clearly ✓

---

### Test 7: History Database Integration

**Purpose**: Verify detections are saved to history

```bash
# 1. Start system
sudo python3 cyt_daemon.py start

# 2. Let run for 10 minutes (to accumulate detections)

# 3. Check history database created
ls -lh cyt_history.db
# PASS: File exists

# 4. Query database
sqlite3 cyt_history.db "SELECT COUNT(*) FROM appearances;"
# PASS: Shows number > 0

# 5. Check specific detections
sqlite3 cyt_history.db "SELECT mac, timestamp FROM appearances LIMIT 5;"
# PASS: Shows MAC addresses and timestamps

# 6. Stop system
sudo python3 cyt_daemon.py stop
```

**Pass Criteria**:
- Database file created ✓
- Detections recorded ✓
- Timestamps correct ✓

---

## 🎯 Feature Tests (45 minutes)

### Test 8: OUI Drone Detection

**Purpose**: Verify known drone manufacturers detected

**Prerequisites**: DJI drone or simulate with MAC spoof

**With Real Drone**:
```bash
# 1. Start system
sudo python3 cyt_daemon.py start

# 2. Turn on DJI drone (or power on)

# 3. Monitor logs
tail -f logs/cyt_monitor.log | grep -i "drone"

# Expected within 60 seconds:
[!!!] DRONE DETECTED [!!!]
   Target: DJI Technology
   MAC:    60:60:1F:AA:BB:CC
   Time:   15:35:22

# PASS: Red alert appears, correct manufacturer
```

**Simulated Test** (no drone required):
```bash
# Check if drone OUIs in database
python3 -c "
from secure_main_logic import DRONE_OUIS
print('Configured drone manufacturers:')
for oui, manuf in DRONE_OUIS.items():
    print(f'  {oui}: {manuf}')
"

# PASS: Shows DJI, Parrot, Autel, etc.
```

**Pass Criteria**:
- Drone detected within 60 seconds of power-on ✓
- Correct manufacturer identified ✓
- RED critical alert displayed ✓
- Alert logged to file ✓

---

### Test 9: Behavioral Drone Detection

**Purpose**: Verify behavioral patterns detected

**Test Setup**:
```bash
# 1. Start system
sudo python3 cyt_daemon.py start

# 2. Walk around with smartphone (Wi-Fi enabled, not connected)
#    - Vary distance (signal variance)
#    - Change altitude (stairs)
#    - Move quickly (high mobility)

# 3. Monitor logs
tail -f logs/cyt_monitor.log | grep -i "behavioral"

# Expected after 10-15 minutes:
[!!!] BEHAVIORAL DRONE DETECTED [!!!]
   MAC:        AA:BB:CC:DD:EE:FF
   Confidence: 65.2%
   Time:       15:45:33
   Patterns:   6/9 detected

# 4. Check pattern details in log
tail -100 logs/cyt_monitor.log | grep -A 20 "BEHAVIORAL DRONE DETECTION"

# Expected:
Detected Patterns:
  ✓ High Mobility: 12.5 m/s
  ✓ Signal Variance: 0.62
  ✓ No Network Association
  ...
```

**Pass Criteria**:
- Suspicious behavior detected (≥60% confidence) ✓
- YELLOW alert displayed ✓
- Confidence score shown ✓
- Pattern details logged ✓

**Note**: May require 10-15 minutes and active movement to accumulate enough data.

---

### Test 10: Persistence Detection

**Purpose**: Verify multi-time-window tracking

```bash
# 1. Start system
sudo python3 cyt_daemon.py start

# 2. Leave Wi-Fi device on for 20+ minutes (phone, laptop)

# 3. Monitor for persistence alerts
tail -f logs/cyt_monitor.log | grep -i "persistent"

# Expected after 20 minutes:
[!!!] PERSISTENT TARGET DETECTED [!!!]
   MAC:    AA:BB:CC:DD:EE:FF
   Score:  7/11
   Time:   16:00:12

# Check threat score calculation
# Score increases as device appears in multiple time windows
```

**Pass Criteria**:
- Device tracked across time windows ✓
- Threat score calculated correctly ✓
- Alert triggered at threshold (≥6/11) ✓

---

### Test 11: AlertManager Integration

**Purpose**: Verify alerts sent (if configured)

**Prerequisites**: `requests` library installed, Telegram bot configured (optional)

```bash
# 1. Test AlertManager standalone
python3 -c "
from alert_manager import AlertManager
am = AlertManager()
am.send_alert('Test alert from CYT', priority='high')
print('Alert sent (check Telegram if configured)')
"

# PASS: No errors
# PASS: Telegram message received (if bot configured)
# PASS: Audio alert played (if configured)

# 2. Test integrated alerts - trigger drone detection
# See Test 8

# 3. Check logs for alert confirmations
tail -f logs/cyt_monitor.log | grep -i "alert"

# Expected:
# INFO - Drone alert sent via AlertManager
```

**Pass Criteria**:
- AlertManager imports successfully ✓
- Test alert sends without errors ✓
- Real detections trigger alerts ✓
- Telegram messages received (if configured) ✓

---

## 💪 Stress Tests (2 hours)

### Test 12: Long-Running Stability

**Purpose**: Verify system runs reliably for extended periods

```bash
# 1. Start system
sudo python3 cyt_daemon.py start

# 2. Run for 2 hours minimum

# 3. Monitor resource usage
watch -n 60 'top -b -n 1 | head -20'

# Check:
# - CPU usage stable (<50% average)
# - Memory usage stable (not growing)
# - No process crashes

# 4. Check logs for errors
tail -f logs/cyt_monitor.log | grep -i "error"
# PASS: No critical errors

# 5. Verify all components still running
python3 cyt_daemon.py status
# PASS: All RUNNING after 2 hours

# 6. Stop system
sudo python3 cyt_daemon.py stop
```

**Pass Criteria**:
- System runs for 2+ hours without crashes ✓
- Memory usage stable ✓
- CPU usage reasonable ✓
- No error accumulation ✓

---

### Test 13: Database Growth

**Purpose**: Verify database doesn't grow excessively

```bash
# During Test 12, monitor database size

# 1. Check initial size
ls -lh /tmp/kismet/*.kismet
# Note size (e.g., 5MB)

# 2. After 1 hour
ls -lh /tmp/kismet/*.kismet
# Check growth (should be linear, not exponential)

# 3. After 2 hours
# Typical growth: 50-500MB per hour (depends on environment)

# 4. Check history database
ls -lh cyt_history.db
# Should be < 100MB after 2 hours
```

**Pass Criteria**:
- Kismet DB grows linearly ✓
- History DB stays manageable (<100MB/day) ✓
- No runaway growth ✓

---

### Test 14: Graceful Degradation

**Purpose**: Verify system handles component failures gracefully

```bash
# 1. Start system normally
sudo python3 cyt_daemon.py start

# 2. Kill Kismet (simulate failure)
sudo pkill kismet

# Expected:
# - Health monitor detects failure
# - CYT Monitor continues running
# - Errors logged, not crashed

# 3. Restart Kismet
sudo ./start_kismet_clean.sh wlan0mon

# Expected:
# - CYT Monitor reconnects
# - Detection resumes

# 4. Kill CYT Monitor (simulate crash)
pkill -f chasing_your_tail.py

# Expected:
# - Kismet keeps running
# - Can restart Monitor independently

# 5. Restart Monitor
python3 chasing_your_tail.py &
```

**Pass Criteria**:
- Component failures don't crash entire system ✓
- Health monitoring detects failures ✓
- Components can restart independently ✓

---

## 🚀 Production Validation (24 hours)

### Test 15: 24-Hour Soak Test

**Purpose**: Final validation before production deployment

```bash
# 1. Start system via systemd
sudo systemctl start cyt

# 2. Run for 24 hours

# 3. Check for crashes
sudo systemctl status cyt
# PASS: Active (running) after 24 hours

# 4. Review logs
sudo journalctl -u cyt --since "24 hours ago" | grep -i "error\|critical"
# PASS: No critical errors or crashes

# 5. Check detection count
sqlite3 cyt_history.db "SELECT COUNT(*) FROM appearances WHERE timestamp > $(date -d '24 hours ago' +%s);"
# PASS: Reasonable number of detections

# 6. Verify no memory leaks
free -h
# Compare to initial memory usage
# PASS: Memory usage stable

# 7. Check disk space
df -h
# PASS: Plenty of space remaining
```

**Pass Criteria**:
- Runs for 24+ hours without intervention ✓
- No crashes or restarts ✓
- Detection working throughout ✓
- Resources stable ✓

---

## 📊 Test Results Template

Create `TEST_RESULTS.md` to document your testing:

```markdown
# CYT Test Results

**Test Date**: [Date]
**Hardware**: [Pi model / Laptop specs]
**Adapter**: [Model]
**OS**: [Ubuntu 22.04 / Raspberry Pi OS / etc.]

## Pre-Flight Checks
- [ ] Python 3.9+ ✓
- [ ] Dependencies installed ✓
- [ ] Wireless adapter present ✓
- [ ] Kismet installed ✓
- [ ] Config valid ✓

## Component Tests
- [ ] Monitor mode works ✓
- [ ] Kismet captures packets ✓
- [ ] CYT Monitor starts ✓
- [ ] Daemon manages processes ✓

## Feature Tests
- [ ] OUI drone detection: PASS / FAIL
- [ ] Behavioral detection: PASS / FAIL
- [ ] Persistence detection: PASS / FAIL
- [ ] Health monitoring: PASS / FAIL
- [ ] AlertManager: PASS / FAIL / N/A

## Stress Tests
- [ ] 2-hour stability: PASS / FAIL
- [ ] Database growth: Normal / Excessive
- [ ] Graceful degradation: PASS / FAIL

## Production Validation
- [ ] 24-hour soak test: PASS / FAIL
- [ ] No memory leaks: PASS / FAIL
- [ ] Detection accuracy: Good / Fair / Poor

## Issues Found
1. [Description of any issues]
2. [Solutions applied]

## Notes
[Any additional observations]

## Recommendation
☐ Ready for production
☐ Needs adjustment (see issues)
☐ Further testing required
```

---

## 🔍 Troubleshooting Test Failures

### Drone Detection Not Working

**Symptoms**: No alerts despite drone present

**Check**:
1. Is Kismet capturing? (`ls -lh /tmp/kismet/*.kismet` - file growing?)
2. Is drone MAC in database? (`sqlite3 *.kismet "SELECT * FROM devices WHERE devmac LIKE '60:60:1F%';"`)
3. Is drone in ignore list? (`cat ignore_lists/mac_ignore.json`)
4. Check logs: `tail -100 logs/cyt_monitor.log | grep -i drone`

---

### Behavioral Detection Too Sensitive

**Symptoms**: Many false positives (normal devices flagged)

**Solution**:
```bash
# Increase threshold in config.json
nano config.json

# Change:
"confidence_threshold": 0.75  # Increase from 0.60
```

---

### Health Monitoring Not Running

**Symptoms**: No health check messages in logs

**Check**:
```bash
# Is health monitoring enabled?
cat config.json | grep -A 5 "kismet_health"

# Should show:
"enabled": true
```

---

### System Crashes After Hours

**Check**:
```bash
# Out of memory?
free -h

# Out of disk space?
df -h

# Check logs for patterns
tail -200 logs/cyt_monitor.log
```

---

## ✅ Testing Checklist

**Before declaring system production-ready**:

- [ ] All Pre-Flight Checks pass
- [ ] All Component Tests pass
- [ ] At least 3 Feature Tests pass
- [ ] 2-hour stability test passes
- [ ] 24-hour soak test passes
- [ ] No critical bugs found
- [ ] All known issues documented
- [ ] Backup/restore tested
- [ ] Documentation reviewed
- [ ] Team trained (if applicable)

---

## 📝 Next Steps After Testing

**If all tests PASS**:
1. Proceed to production deployment
2. See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
3. Monitor for first week
4. Tune detection thresholds based on environment

**If tests FAIL**:
1. Document failures in TEST_RESULTS.md
2. Troubleshoot using this guide
3. Re-test after fixes
4. Escalate if unresolvable

---

**Estimated Testing Time**:
- Basic tests: 1 hour
- Feature tests: 2 hours
- Stress tests: 2 hours
- 24-hour soak: 24 hours (automated)
- **Total**: ~5 hours active + 24 hours monitoring

**Good luck with testing!** 🚀
