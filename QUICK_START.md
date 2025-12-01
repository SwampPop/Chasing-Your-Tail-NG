# CYT Quick Start Guide

**Get from zero to detecting threats in 30 minutes**

This guide assumes you have hardware ready. If not, see [HARDWARE_REQUIREMENTS.md](HARDWARE_REQUIREMENTS.md) first.

---

## ⚡ 30-Second Overview

```bash
# 1. Clone repository
git clone https://github.com/SwampPop/Chasing-Your-Tail-NG.git
cd Chasing-Your-Tail-NG

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Configure
python3 secure_credentials.py
nano config.json  # Edit paths if needed

# 4. Put wireless adapter in monitor mode
sudo airmon-ng start wlan0

# 5. Start everything
sudo python3 cyt_daemon.py start

# 6. Monitor
tail -f logs/cyt_monitor.log
```

**Done!** System is now detecting threats.

---

## 📋 Complete Setup (Step-by-Step)

### Prerequisites Checklist

Before starting, verify you have:

- [ ] Linux system (Ubuntu 20.04+ recommended, Raspberry Pi OS works)
- [ ] Python 3.9 or newer (`python3 --version`)
- [ ] Wireless adapter supporting monitor mode
- [ ] Root/sudo access
- [ ] Internet connection (for initial setup)

---

### Step 1: Install System Dependencies (5 minutes)

```bash
# Update system
sudo apt-get update

# Install Python and pip
sudo apt-get install -y python3 python3-pip

# Install Kismet
sudo apt-get install -y kismet

# Install wireless tools
sudo apt-get install -y aircrack-ng wireless-tools

# Verify installations
python3 --version   # Should be 3.9+
kismet --version    # Should show version
airmon-ng --help    # Should show help
```

**Troubleshooting**:
- If `kismet` not found: See [Kismet installation guide](https://www.kismetwireless.net/docs/readme/installing/linux/)
- If `airmon-ng` not found: `sudo apt-get install aircrack-ng`

---

### Step 2: Clone Repository (2 minutes)

```bash
# For production (recommended location)
cd /opt
sudo git clone https://github.com/SwampPop/Chasing-Your-Tail-NG.git cyt
cd cyt

# OR for development (home directory)
cd ~
git clone https://github.com/SwampPop/Chasing-Your-Tail-NG.git
cd Chasing-Your-Tail-NG
```

**Note**: This guide assumes `/opt/cyt` - adjust paths if using different location.

---

### Step 3: Install Python Dependencies (3 minutes)

```bash
cd /opt/cyt

# Install requirements
sudo pip3 install -r requirements.txt

# Verify critical imports
python3 -c "import flask, requests, jsonschema, kivy; print('✓ All dependencies installed')"
```

**If import errors**:
```bash
# Install missing packages individually
sudo pip3 install flask
sudo pip3 install requests
sudo pip3 install jsonschema
sudo pip3 install kivy  # Optional, for GUI
```

---

### Step 4: Configure Credentials (5 minutes)

```bash
# Set up encrypted credential storage
python3 secure_credentials.py
```

**Interactive prompts**:
```
Enter master password: [choose strong password]
Confirm password: [same password]

WiGLE API credentials (optional - press Enter to skip):
WiGLE API Name: [your wigle username or skip]
WiGLE API Key: [your wigle key or skip]

✓ Credentials saved to ./secure_credentials/encrypted_credentials.json
```

**Important**:
- Remember this password - you'll need it every time CYT starts
- WiGLE is optional (for SSID geolocation)
- Can skip WiGLE for now, add later

**Generate API Key** (if using API server):
```bash
python3 generate_api_key.py
# Copy the generated key

# Add to environment
echo 'export CYT_API_KEY="your_generated_key_here"' >> ~/.bashrc
source ~/.bashrc
```

---

### Step 5: Configure System (5 minutes)

```bash
# Edit configuration
nano config.json
```

**Minimal required changes**:
```json
{
  "paths": {
    "kismet_logs": "/tmp/kismet",  // ← Verify this exists or change
    "ignore_lists": {
      "mac": "ignore_lists/mac_ignore.json",
      "ssid": "ignore_lists/ssid_ignore.json"
    }
  }
}
```

**Key settings to verify**:
- `kismet_logs`: Where Kismet stores databases (default: `/tmp/kismet`)
- `interface`: Your wireless interface name (check with `iwconfig`)

**Validate configuration**:
```bash
python3 config_validator.py

# Expected output:
# ✓ Configuration is VALID
```

**Create ignore lists** (optional but recommended):
```bash
# Create empty ignore lists for first run
mkdir -p ignore_lists
echo '[]' > ignore_lists/mac_ignore.json
echo '[]' > ignore_lists/ssid_ignore.json
```

---

### Step 6: Prepare Wireless Adapter (3 minutes)

```bash
# Find your wireless interface
iwconfig

# Look for: wlan0, wlan1, wlp3s0, etc.
# Example output:
# wlan0     IEEE 802.11  ESSID:off/any

# Put in monitor mode
sudo airmon-ng start wlan0

# Verify monitor mode enabled
iwconfig

# Should now show: wlan0mon (or similar)
# Example:
# wlan0mon  IEEE 802.11  Mode:Monitor
```

**Update config.json with monitor interface**:
```json
{
  "kismet_health": {
    "interface": "wlan0mon"  // ← Match your monitor interface
  }
}
```

**Troubleshooting**:
- If `airmon-ng` fails: Kill interfering processes with `sudo airmon-ng check kill`
- If no monitor interface: Your adapter may not support monitor mode (see HARDWARE_REQUIREMENTS.md)

---

### Step 7: Test Kismet (3 minutes)

```bash
# Test Kismet startup script
sudo ./start_kismet_clean.sh wlan0mon

# Wait 10 seconds, then verify
pgrep kismet

# Should output PIDs (e.g., 12345 12346)

# Check Kismet is capturing
ls -lh /tmp/kismet/*.kismet

# Should show growing .kismet file

# Stop Kismet for now
sudo pkill kismet
```

**If Kismet fails to start**:
```bash
# Check Kismet logs
sudo journalctl -u kismet -n 50

# Try manual start
sudo kismet -c wlan0mon

# Common issues:
# - Interface not in monitor mode → airmon-ng start wlan0
# - Permission denied → Running as root?
# - Interface busy → airmon-ng check kill
```

---

### Step 8: First System Start (2 minutes)

```bash
# Start entire system
sudo python3 cyt_daemon.py start

# Expected output:
============================================================
Starting CYT System
============================================================

▶ Starting Kismet...
✓ Kismet started (PID: 12345)

▶ Starting CYT Monitor...
✓ CYT Monitor started (PID: 12346)

⊘ Skipping API Server (CYT_API_KEY not configured)

============================================================
✓ CYT System Started Successfully
============================================================

Logs: ./logs/
PIDs: ./run/

Monitor logs: tail -f ./logs/cyt_monitor.log
Stop system: sudo python3 cyt_daemon.py stop
```

**Verify all components running**:
```bash
python3 cyt_daemon.py status

# Expected:
# ✓ Kismet               RUNNING (PID: 12345)
# ✓ CYT Monitor          RUNNING (PID: 12346)
# ✗ API Server           STOPPED (optional)
```

---

### Step 9: Monitor Detection (Ongoing)

```bash
# Watch for detections in real-time
tail -f logs/cyt_monitor.log

# Watch for specific alerts
tail -f logs/cyt_monitor.log | grep -E "(DRONE|BEHAVIORAL|PERSISTENT)"

# Check health monitoring
tail -f logs/cyt_monitor.log | grep -i health
```

**What to expect**:
- Initial device discovery (first 5 minutes)
- Persistence alerts after 10-20 minutes (if devices tracked)
- Drone alerts immediately (if DJI/Parrot/etc. present)
- Behavioral drone alerts after 3+ appearances (if suspicious devices)

---

### Step 10: Test Detection (Optional)

**Test OUI Drone Detection**:
- If you have a DJI drone: Turn it on
- Expected: Immediate RED alert "DRONE DETECTED: DJI Technology"

**Test Behavioral Detection**:
- Walk around with phone Wi-Fi enabled
- Change altitude rapidly (stairs)
- Expected: Eventually yellow "BEHAVIORAL DRONE DETECTED" (may take 10-15 minutes)

**Test Persistence Detection**:
- Keep Wi-Fi device on for 20+ minutes
- Expected: Persistence alerts with threat scores

---

### Step 11: Stop System (1 minute)

```bash
# Graceful shutdown
sudo python3 cyt_daemon.py stop

# Expected:
============================================================
Stopping CYT System
============================================================

◼ Stopping API Server...
⚠ API Server is not running

◼ Stopping CYT Monitor...
✓ CYT Monitor stopped

◼ Stopping Kismet...
✓ Kismet stopped

============================================================
✓ CYT System Stopped
============================================================

# Verify all stopped
python3 cyt_daemon.py status

# All should show: ✗ STOPPED
```

---

## ✅ Success Checklist

After completing setup, verify:

- [ ] `python3 cyt_daemon.py start` succeeds
- [ ] `python3 cyt_daemon.py status` shows all RUNNING
- [ ] `tail -f logs/cyt_monitor.log` shows activity
- [ ] Kismet database exists (`ls -lh /tmp/kismet/*.kismet`)
- [ ] No errors in logs
- [ ] Health check messages appear every 5 cycles
- [ ] Can gracefully stop with `cyt_daemon.py stop`

---

## 🚀 Production Deployment (Systemd)

For permanent installation with auto-start on boot:

```bash
# 1. Verify everything works manually first
sudo python3 cyt_daemon.py start
# ... test ...
sudo python3 cyt_daemon.py stop

# 2. Install systemd service
sudo cp cyt.service /etc/systemd/system/
sudo systemctl daemon-reload

# 3. Enable auto-start on boot
sudo systemctl enable cyt

# 4. Start service
sudo systemctl start cyt

# 5. Check status
sudo systemctl status cyt

# Expected: Active (running)

# 6. View logs
sudo journalctl -u cyt -f
```

**Systemd commands**:
```bash
sudo systemctl start cyt       # Start
sudo systemctl stop cyt        # Stop
sudo systemctl restart cyt     # Restart
sudo systemctl status cyt      # Status
sudo journalctl -u cyt -f      # Follow logs
sudo systemctl disable cyt     # Disable auto-start
```

---

## 🔧 Common Issues & Fixes

### Issue: "Failed to start Kismet"

**Check**:
```bash
# Is interface in monitor mode?
iwconfig

# Try manual Kismet start
sudo kismet -c wlan0mon
```

**Fix**:
```bash
# Put interface in monitor mode
sudo airmon-ng start wlan0

# Update config.json with correct interface
nano config.json
# Set: "interface": "wlan0mon"
```

---

### Issue: "CYT Monitor exited immediately"

**Check logs**:
```bash
tail -50 logs/cyt_monitor.log
```

**Common causes**:
1. **Kismet not running**: Start Kismet first
2. **Config error**: Run `python3 config_validator.py`
3. **Missing credentials**: Run `python3 secure_credentials.py`
4. **Database not found**: Check `config.json` → `paths.kismet_logs`

---

### Issue: "No detections appearing"

**Verify**:
```bash
# Is Kismet capturing?
ls -lh /tmp/kismet/*.kismet

# File should be growing in size

# Are devices nearby?
# Walk around with phone Wi-Fi on
```

**Check detection thresholds**:
```bash
# May be set too high in config.json
nano config.json

# Try lowering:
"confidence_threshold": 0.40  # Lower from 0.60
```

---

### Issue: "Permission denied"

**Everything needs sudo**:
```bash
# Wrong:
python3 cyt_daemon.py start

# Correct:
sudo python3 cyt_daemon.py start
```

**Why**: Kismet requires root for packet capture

---

### Issue: AlertManager not sending alerts

**Check**:
```bash
# Is requests library installed?
python3 -c "import requests; print('✓ Installed')"

# If not:
sudo pip3 install requests

# Is Telegram bot configured?
python3 secure_credentials.py
# Add Telegram bot token
```

**Test alert**:
```bash
python3 -c "
from alert_manager import AlertManager
am = AlertManager()
am.send_alert('Test alert', priority='high')
"
```

---

## 📊 What Should I See?

### Successful Start Output:
```
============================================================
Starting CYT System
============================================================

▶ Starting Kismet...
[waiting 10 seconds]
✓ Kismet started (PID: 12345)

▶ Starting CYT Monitor...
[waiting 3 seconds]
✓ CYT Monitor started (PID: 12346)

============================================================
✓ CYT System Started Successfully
============================================================
```

### Healthy Running Logs:
```
2025-12-01 15:30:15 - INFO - --- CYT Monitoring Session Started ---
2025-12-01 15:30:15 - INFO - Validating configuration...
2025-12-01 15:30:15 - INFO - ✓ Configuration validation passed
2025-12-01 15:30:16 - INFO - Behavioral drone detection enabled
2025-12-01 15:30:16 - INFO - Kismet health monitoring enabled
2025-12-01 15:30:20 - INFO - 15 MACs added to the Past 5 minutes list
2025-12-01 15:30:20 - INFO - Starting secure CYT monitoring loop...
```

### Detection Alerts:
```
[!!!] DRONE DETECTED [!!!]
   Target: DJI Technology
   MAC:    60:60:1F:AA:BB:CC
   Time:   15:35:22

[!!!] BEHAVIORAL DRONE DETECTED [!!!]
   MAC:        AA:BB:CC:DD:EE:FF
   Confidence: 75.1%
   Time:       15:36:45
   Patterns:   7/9 detected
```

---

## 🎯 Next Steps

After successful setup:

1. **Monitor for 24 Hours**: Let system run and observe detections
2. **Tune Thresholds**: Adjust `config.json` based on your environment
3. **Create Ignore Lists**: Add known devices to reduce noise
4. **Enable AlertManager**: Set up Telegram for remote notifications
5. **Review Documentation**: Read BEHAVIORAL_DRONE_DETECTION.md, HEALTH_MONITORING.md, DAEMON.md

**Read more**:
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Comprehensive testing procedures
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Production deployment
- [HARDWARE_REQUIREMENTS.md](HARDWARE_REQUIREMENTS.md) - Hardware recommendations

---

## 🆘 Getting Help

If stuck:

1. **Check logs**: `tail -f logs/cyt_monitor.log logs/cyt_daemon.log`
2. **Validate config**: `python3 config_validator.py`
3. **Test components**:
   - Kismet: `sudo kismet -c wlan0mon`
   - Monitor: `python3 chasing_your_tail.py`
   - Daemon: `python3 cyt_daemon.py status`
4. **Review documentation** in this repository
5. **Check GitHub issues**: https://github.com/SwampPop/Chasing-Your-Tail-NG/issues

---

**Estimated Total Time**: 30 minutes (with hardware ready)

**Difficulty**: Intermediate (requires Linux knowledge)

**Success Rate**: High (if hardware compatible)

---

✅ **You should now have a fully operational CYT system detecting wireless threats!**
