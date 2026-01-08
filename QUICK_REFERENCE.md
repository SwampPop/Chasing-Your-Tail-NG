# CYT Quick Reference Card

**Chasing Your Tail - Next Generation**
**Quick Command Reference for Daily Operations**

---

## Starting the System

### 1. Start Kismet (captures WiFi/BT devices)
```bash
cd ~/Chasing-Your-Tail-NG
sudo kismet -c wlan0 --daemonize
```

### 2. Start CYT Monitoring (analyzes behavior)
```bash
cd ~/Chasing-Your-Tail-NG
python3 chasing_your_tail.py > logs/cyt_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

**OR** use the GUI:
```bash
python3 cyt_gui.py &
```

---

## Checking Status

### Verify Kismet is Running
```bash
ps aux | grep kismet | grep -v grep
```

### Verify CYT is Running
```bash
ps aux | grep chasing_your_tail | grep -v grep
```

### View Live Monitoring Log
```bash
cd ~/Chasing-Your-Tail-NG
tail -f logs/cyt_*.log
```

### Check Kismet Web UI
Open browser to: **http://localhost:2501**

---

## Investigating Devices

### Interactive Investigation Tool (RECOMMENDED)
```bash
cd ~/Chasing-Your-Tail-NG
python3 investigate_devices.py
```

**Menu Options:**
1. Device type summary
2. WiFi Access Points by signal strength
3. WiFi Clients by mobility patterns
4. Bluetooth/BTLE devices
5. Devices by manufacturer (OUI lookup)
6. Investigate specific device (by MAC)
7. Generate all reports

### Manual SQL Queries
```bash
# See DEVICE_INVESTIGATION_QUERIES.md for ready-to-use queries
cd ~/Chasing-Your-Tail-NG
sqlite3 ~/logs/kismet/*.kismet
```

---

## Managing Ignore Lists

### Edit Ignore Lists (Add Your Devices)
```bash
cd ~/Chasing-Your-Tail-NG
nano ignore_lists/mac_list.txt      # MAC addresses
nano ignore_lists/ssid_list.txt     # WiFi network names
```

**Format:**
```
AA:BB:CC:DD:EE:FF  # My iPhone
11:22:33:44:55:66  # My Apple Watch
MyHomeWiFi         # Home router
```

### Regenerate Ignore List from Kismet
```bash
cd ~/Chasing-Your-Tail-NG
python3 create_ignore_list.py
```
**Note:** Smart merge preserves your # comments!

### Test Ignore List Syntax
```bash
cd ~/Chasing-Your-Tail-NG
python3 -c "from secure_ignore_loader import SecureIgnoreLoader; print(SecureIgnoreLoader().load_ignore_list('ignore_lists/mac_list.txt'))"
```

---

## Daily Workflow

### Morning Routine (Start Monitoring)
```bash
# 1. Connect Alfa WiFi adapter to VM
# 2. Start Kismet
sudo kismet -c wlan0 --daemonize

# 3. Start CYT
cd ~/Chasing-Your-Tail-NG
python3 chasing_your_tail.py > logs/cyt_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### Evening Routine (Review Alerts)
```bash
# 1. Check for alerts
cd ~/Chasing-Your-Tail-NG
tail -50 logs/cyt_*.log | grep -i alert

# 2. Investigate unknown devices
python3 investigate_devices.py

# 3. Add YOUR devices to ignore list
nano ignore_lists/mac_list.txt
```

### Work → Home Detection
**Devices appearing at BOTH locations are yours!**

1. Run monitoring at work all day
2. Check which devices followed you home
3. Add those to ignore list:
   - Your phone (WiFi + Bluetooth)
   - Your smartwatch (Bluetooth)
   - Your car (Bluetooth)
   - Your laptop (WiFi)

---

## Categorizing Devices

### Signal Strength Guide
- **> -50 dBm**: Very close (your devices or immediate neighbors)
- **-50 to -70 dBm**: Nearby (neighbors' routers, nearby devices)
- **< -70 dBm**: Distant (far neighbors, passing cars)

### What to IGNORE (add to ignore list)
- ✅ Your routers/access points (strong signal, static location)
- ✅ Your phones, laptops, tablets (known devices)
- ✅ Your Bluetooth devices (watch, earbuds, car)
- ✅ Neighbor routers (always present, static location)

### What to WATCH (DO NOT ignore)
- ⚠️ Unknown clients with strong signal
- ⚠️ Devices that move with you (same locations as you)
- ⚠️ Devices with suspicious names (hidden SSIDs, probe spam)
- ⚠️ Unknown Bluetooth devices (could be AirTag tracker)
- ⚠️ Devices only seen when you're mobile (following pattern)

---

## Stopping the System

### Stop CYT
```bash
pkill -f chasing_your_tail.py
```

### Stop Kismet
```bash
sudo killall kismet
```

### Stop Everything
```bash
pkill -f chasing_your_tail.py
sudo killall kismet
```

---

## Troubleshooting

### Kismet Won't Start
```bash
# Check if already running
ps aux | grep kismet

# Check interface is in monitor mode
sudo airmon-ng start wlan0

# Check Kismet logs
tail -50 ~/.kismet/kismet_error.log
```

### CYT Won't Start
```bash
# Check Python dependencies
cd ~/Chasing-Your-Tail-NG
python3 -c "import sqlite3, json, gpsd; print('Dependencies OK')"

# Check config file
python3 config_validator.py
```

### No Devices Detected
```bash
# Check Kismet is capturing
sqlite3 ~/logs/kismet/*.kismet "SELECT COUNT(*) FROM devices;"

# Check CYT can read Kismet database
cd ~/Chasing-Your-Tail-NG
python3 -c "import glob; print(glob.glob('~/logs/kismet/*.kismet'))"
```

### GPS Not Working
```bash
# Check gpsd is running
ps aux | grep gpsd

# Test GPS connection
cgps -s

# Enable GPS in config.json
nano config.json  # Set "gps_enabled": true
```

---

## File Locations

### Important Files
- **Config**: `~/Chasing-Your-Tail-NG/config.json`
- **Ignore Lists**: `~/Chasing-Your-Tail-NG/ignore_lists/`
- **CYT Logs**: `~/Chasing-Your-Tail-NG/logs/cyt_*.log`
- **Kismet Databases**: `~/logs/kismet/*.kismet`
- **CYT History**: `~/Chasing-Your-Tail-NG/cyt_history.db`

### Investigation Tools
- **Interactive Tool**: `investigate_devices.py`
- **SQL Reference**: `DEVICE_INVESTIGATION_QUERIES.md`
- **Probe Analyzer**: `probe_analyzer.py`
- **Surveillance Analyzer**: `surveillance_analyzer.py`

---

## Alert Timeline

### Immediate Alerts (Real-Time Threats)
- Drone signatures detected
- Known surveillance equipment
- Devices on watchlist

### 30-60 Minute Alerts (Following Patterns)
- Device appears at 3+ of your locations
- Device moves in sync with your location changes
- Device persists across multiple sessions

**Strategy:**
Don't panic on first detection. Wait to see if pattern develops over time.

---

## VM Snapshots (Rollback Points)

### Current Snapshot Chain
```
Root
├── Pre-Kismet-Test-Clean-State (40% deployment)
│   └── Known-Good-Kismet-Working (80% deployment)
│       └── CYT-Integration-Success (95% deployment)
│           └── GPS-Integration-Complete (100%) ★ CURRENT
```

### Restore Snapshot
```bash
# From macOS:
prlctl snapshot-list "{f058900f-7772-4cd7-8443-655c19cf868c}"
prlctl restore-snapshot "{f058900f-7772-4cd7-8443-655c19cf868c}" --id <snapshot-id>
```

---

## Safety Reminders

### DO NOT in VM
- ❌ `sudo apt upgrade` - May break WiFi driver
- ❌ `sudo apt dist-upgrade` - Will break kernel
- ❌ Update kernel without snapshot

### Safe in VM
- ✅ `sudo apt update` - Just updates package lists
- ✅ `sudo apt install <package>` - Individual packages OK
- ✅ Python package updates

### Before Major Changes
```bash
# Create snapshot from macOS:
prlctl snapshot "{f058900f-7772-4cd7-8443-655c19cf868c}" --name "Before-<change-description>"
```

---

## Quick Tips

1. **First Time Setup**: Use `investigate_devices.py` to categorize 50-100 devices at work/home
2. **Continuous Refinement**: Add to ignore list whenever you identify a new device
3. **False Positives**: Better to monitor neighbor than miss a stalker - when in doubt, DON'T ignore
4. **Signal Strength**: Primary indicator for "is this mine?" (> -50 dBm = very close)
5. **Persistence**: Routers are static, suspicious devices follow you
6. **Comments**: Always annotate ignore list entries with # comments for future reference
7. **Backups**: Smart merge creates `.backup` files automatically

---

**Version**: 1.0
**Last Updated**: 2025-12-21
**VM**: CYT-Kali-Fresh (UUID: f058900f-7772-4cd7-8443-655c19cf868c)
**Kernel**: 6.16.8+kali-arm64 (PINNED)
