# CYT on macOS - Quick Start Checklist

**Platform**: MacBook Air M3 (Apple Silicon)
**Timeline**: 1-2 hours total setup time
**Goal**: Get CYT operational on native macOS

---

## Pre-Flight Check

**What You Have**:
- [x] MacBook Air M3 (8-core, M3 chip)
- [x] Alfa AWUS1900 (ordered, arriving soon)
- [ ] USB-C Hub (required - order if you haven't)

**What You Need**:
- [ ] 1-2 hours of uninterrupted time
- [ ] Stable internet connection
- [ ] Admin password for macOS
- [ ] GitHub account (already have)

---

## Phase 1: Hardware Setup (15 minutes)

### Step 1: Acquire USB-C Hub

**When Alfa Arrives, You'll Need**:
```
Problem: MacBook Air M3 only has USB-C ports
Solution: USB-C hub with USB-A ports

Recommended Options:
- Budget: Anker 4-Port USB-C Hub ($25)
  - 3x USB-A 3.0 ports
  - 1x USB-C charging

- Better: Anker 7-in-1 USB-C Hub ($45)
  - 3x USB-A 3.0 ports
  - 1x Ethernet (useful for stable internet)
  - 1x HDMI (for external display)
  - 1x SD/microSD
  - 1x USB-C charging (60W pass-through)
```

**Order Now**: Don't wait for Alfa to arrive!

### Step 2: Physical Connection

When your hardware arrives:

```
Connection Flow:
MacBook Air M3 (USB-C port)
    ↓
USB-C Hub
    ↓
Alfa AWUS1900 (USB-A connector)
    ↓
(Optional) USB Extension Cable (better antenna positioning)
```

**Verification**:
```bash
# Plug in Alfa AWUS1900
# macOS should recognize it

# Open Terminal and check:
system_profiler SPUSBDataType | grep -i realtek

# Should see something like:
# Realtek 802.11ac WLAN Adapter
```

---

## Phase 2: Software Installation (30-45 minutes)

### Step 1: Install Homebrew (if not installed)

**Check if Homebrew exists**:
```bash
brew --version

# If command not found, install:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Follow prompts, enter admin password when asked
# Installation takes 5-10 minutes
```

**Post-Installation**:
```bash
# Add Homebrew to PATH (Apple Silicon)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Verify
brew --version
# Should show: Homebrew 4.x.x
```

### Step 2: Install Kismet

**Add Kismet Tap**:
```bash
# Add official Kismet repository
brew tap kismetwireless/kismet
```

**Install Kismet**:
```bash
# Install Kismet and dependencies
brew install kismet

# This installs:
# - Kismet server
# - Kismet client tools
# - Required libraries
# - macOS-specific drivers

# Installation takes 5-10 minutes
```

**Verify Installation**:
```bash
kismet --version

# Should show:
# Kismet 2024.xx.xx
```

### Step 3: Install Wireless Tools

```bash
# Install aircrack-ng suite
brew install aircrack-ng

# Verify
aircrack-ng --help
```

### Step 4: Install GPS Support (Optional)

**If you plan to use GPS module**:
```bash
# Install gpsd (GPS daemon)
brew install gpsd

# Install gpsd clients
brew install gpsd-clients

# Verify
gpsd -V
```

**If no GPS module**:
- Skip this step
- CYT will work without GPS (but no location correlation)

### Step 5: Install Alfa AWUS1900 Driver

**Check if driver needed**:
```bash
# Plug in Alfa AWUS1900
# Check if macOS recognizes it:
system_profiler SPUSBDataType | grep -i realtek

# If recognized, you might not need custom driver
# Try creating wireless interface first (Step 6)
```

**If driver installation needed** (RTL8814AU chipset):

```bash
# Clone driver repository
cd ~/Downloads
git clone https://github.com/aircrack-ng/rtl8814au.git
cd rtl8814au

# Build for Apple Silicon (M3)
make ARCH=arm64

# Install (requires admin password)
sudo make install

# Load kernel module
sudo modprobe 8814au

# Verify
lsmod | grep 8814au
# Should show: 8814au loaded
```

**Alternative Driver Sources** (if above fails):
```bash
# Try morrownr's driver (often better macOS support)
cd ~/Downloads
git clone https://github.com/morrownr/8814au.git
cd 8814au
sudo ./install-driver.sh
```

### Step 6: Configure Wireless Interface

**Check available interfaces**:
```bash
# List all network interfaces
ifconfig

# Look for wireless interface (usually en0 or en1)
# Example output:
# en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
#     ether 1a:2b:3c:4d:5e:6f
```

**Enable monitor mode** (required for Kismet):
```bash
# Option A: Using airport utility (built-in macOS)
# Create alias for easy access
sudo ln -s /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport /usr/local/bin/airport

# Put interface in monitor mode
sudo airport en0 sniff 1

# Verify
ifconfig

# Should see: en0: mode=monitor
```

**Option B: Using airmon-ng** (from aircrack-ng):
```bash
# Check for interfering processes
sudo airmon-ng check

# Kill interfering processes (if any)
sudo airmon-ng check kill

# Start monitor mode on en0
sudo airmon-ng start en0

# Verify - new interface created (en0mon)
ifconfig
```

---

## Phase 3: CYT Installation (15 minutes)

### Step 1: Clone CYT Repository

**You already have this**, but verify:
```bash
cd ~/Chasing-Your-Tail-NG
git status

# If clean, you're good
# If changes, stash or commit:
git stash  # Save uncommitted changes
```

**If starting fresh**:
```bash
cd ~
git clone https://github.com/SwampPop/Chasing-Your-Tail-NG.git
cd Chasing-Your-Tail-NG
```

### Step 2: Install Python Dependencies

**Check Python version**:
```bash
python3 --version

# Should be Python 3.9+
# MacBook Air M3 ships with Python 3.9+
```

**Install required packages**:
```bash
cd ~/Chasing-Your-Tail-NG

# Install from requirements.txt
pip3 install -r requirements.txt

# This installs:
# - cryptography (encrypted credentials)
# - requests (WiGLE API)
# - flask (API server)
# - kivy (GUI - optional)
```

**Verify installation**:
```bash
python3 -c "import cryptography; print('cryptography OK')"
python3 -c "import requests; print('requests OK')"
python3 -c "import flask; print('flask OK')"
```

### Step 3: Configure CYT

**Validate configuration**:
```bash
cd ~/Chasing-Your-Tail-NG
python3 config_validator.py

# Should show:
# ✓ Configuration is valid
# ✓ All required sections present
# ✓ All paths accessible
```

**If validation fails**:
```bash
# Check config.json exists
ls -la config.json

# If missing, restore from git:
git checkout config.json
```

### Step 4: Create Required Directories

**CYT needs these directories**:
```bash
cd ~/Chasing-Your-Tail-NG

# Create if they don't exist
mkdir -p logs
mkdir -p run
mkdir -p surveillance_reports
mkdir -p kml_files
mkdir -p ignore_lists
mkdir -p secure_credentials

# Verify
ls -la
# Should see all directories listed above
```

### Step 5: Set Up Encrypted Credentials (Optional)

**If using Telegram alerts or WiGLE API**:
```bash
python3 secure_credentials.py

# Follow prompts:
# - Create master password (remember this!)
# - Add Telegram bot token (if you have one)
# - Add WiGLE API key (if you have one)
```

**If skipping for now**:
- CYT will work without credentials
- You can add them later

---

## Phase 4: Kismet Configuration (20-30 minutes)

### Step 1: Configure Kismet for macOS

**Edit Kismet config**:
```bash
# Find Kismet config location
brew --prefix kismet
# Example: /opt/homebrew/opt/kismet

# Edit config (create if doesn't exist)
mkdir -p ~/.kismet
nano ~/.kismet/kismet_site.conf

# Add these lines:
```

**Kismet Configuration** (`~/.kismet/kismet_site.conf`):
```ini
# Kismet macOS Configuration for CYT

# Data source (your wireless adapter)
# Replace 'en0' with your actual interface
source=en0

# Log location
log_prefix=/tmp/kismet

# Enable required logs
log_types=kismet,pcapng

# macOS-specific: Disable plugins that cause issues
allowedhosts=127.0.0.1
allowedhosts=localhost

# Web interface (optional - useful for debugging)
httpd_port=2501
httpd_username=kismet
httpd_password=kismet

# Disable GPS if you don't have module
gps=false

# Or enable if you have GPS module:
# gps=true
# gps=gpsd:host=localhost,port=2947
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

### Step 2: Start Kismet (Test Run)

**Option A: Start Kismet manually**:
```bash
# Start Kismet server
sudo kismet -c en0

# You should see:
# INFO: Kismet starting...
# INFO: Opened source 'en0'
# INFO: Data sources started, waiting for packets...

# Let it run for 30 seconds
# Press Ctrl+C to stop
```

**Check for errors**:
```bash
# If error: "Could not open capture interface"
# Solution: Enable monitor mode first (see Step 6 in Phase 2)

# If error: "Permission denied"
# Solution: Use sudo (or add user to kismet group)

# If error: "No such device"
# Solution: Verify interface name with 'ifconfig'
```

**Option B: Use CYT's Kismet startup script**:

**Note**: The existing `start_kismet_clean.sh` is for Linux. Let's create a macOS version:

```bash
cd ~/Chasing-Your-Tail-NG

# Create macOS-specific startup script
nano start_kismet_macos.sh
```

**Content of `start_kismet_macos.sh`**:
```bash
#!/bin/bash
# Kismet Startup Script for macOS
# Usage: ./start_kismet_macos.sh en0

INTERFACE=${1:-en0}

echo "Starting Kismet on interface: $INTERFACE"

# Check if Kismet already running
if pgrep -x kismet > /dev/null; then
    echo "WARNING: Kismet already running. Stopping..."
    sudo pkill -9 kismet
    sleep 2
fi

# Clean up old log files (optional)
echo "Cleaning up old Kismet logs..."
rm -f /tmp/kismet/*.kismet 2>/dev/null

# Start Kismet
echo "Starting Kismet server..."
sudo kismet -c $INTERFACE --daemonize

# Wait for startup
sleep 5

# Check if running
if pgrep -x kismet > /dev/null; then
    echo "SUCCESS: Kismet started on $INTERFACE"
    echo "Logs: /tmp/kismet/"
    echo "Web UI: http://localhost:2501"
else
    echo "ERROR: Kismet failed to start"
    exit 1
fi
```

**Make executable**:
```bash
chmod +x start_kismet_macos.sh

# Test it
./start_kismet_macos.sh en0

# Should see: SUCCESS: Kismet started on en0
```

### Step 3: Verify Kismet is Capturing

**Check Kismet database**:
```bash
# Wait 1-2 minutes for Kismet to capture some data
# Then check:
ls -lh /tmp/kismet/

# Should see:
# Kismet-*.kismet (SQLite database)
# Kismet-*.pcapng (packet capture)

# Query database
sqlite3 /tmp/kismet/Kismet-*.kismet "SELECT COUNT(*) FROM devices;"

# Should return a number > 0 (number of devices seen)
```

**Check Kismet Web UI** (optional):
```bash
# Open browser to:
open http://localhost:2501

# Login:
# Username: kismet
# Password: kismet

# You should see devices appearing in real-time
```

---

## Phase 5: Run CYT (10-15 minutes)

### Step 1: First Test Run

**Start CYT in a new terminal**:
```bash
cd ~/Chasing-Your-Tail-NG

# Run main monitoring script
python3 chasing_your_tail.py

# Expected output:
# 2025-12-07 10:30:00 - INFO - CYT Monitor starting...
# 2025-12-07 10:30:00 - INFO - Monitoring Kismet database: /tmp/kismet/*.kismet
# 2025-12-07 10:30:00 - INFO - Checking for new devices...
# 2025-12-07 10:30:05 - INFO - Found 15 devices
# 2025-12-07 10:30:05 - INFO - Analyzing devices...
```

**Let it run for 5-10 minutes**, observe output.

### Step 2: Check CYT Logs

**Open another terminal**:
```bash
cd ~/Chasing-Your-Tail-NG

# Watch CYT monitor log
tail -f logs/cyt_monitor.log

# You should see:
# Device checks
# Database queries
# Analysis results
```

### Step 3: Verify Device Detection

**Check CYT history database**:
```bash
cd ~/Chasing-Your-Tail-NG

# Query device history
sqlite3 cyt_history.db "SELECT mac_address, first_seen, last_seen FROM device_history LIMIT 10;"

# Should show devices CYT has tracked
```

### Step 4: Test Behavioral Detection (Optional)

**Run standalone behavioral detector**:
```bash
cd ~/Chasing-Your-Tail-NG

# Test behavioral detection on Kismet data
python3 behavioral_drone_detector.py

# Expected output:
# Analyzing devices from Kismet database...
# Device AA:BB:CC:DD:EE:FF:
#   High Mobility: YES (score: 0.15)
#   Signal Variance: YES (score: 0.10)
#   ...
#   Overall Confidence: 45.2%
```

---

## Phase 6: Advanced Configuration (Optional)

### Step 1: Set Up Telegram Alerts

**Create Telegram Bot** (5 minutes):
```bash
1. Open Telegram app
2. Search for: @BotFather
3. Send: /newbot
4. Follow prompts:
   - Bot name: CYT Alert Bot
   - Username: cyt_alert_bot (or whatever's available)
5. Copy bot token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz

6. Get your Chat ID:
   - Search for: @userinfobot
   - Send: /start
   - Copy your Chat ID: 987654321
```

**Add credentials to CYT**:
```bash
cd ~/Chasing-Your-Tail-NG
python3 secure_credentials.py

# Add Telegram credentials:
# Bot Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
# Chat ID: 987654321
```

**Test alert**:
```bash
# Trigger test alert (edit config.json temporarily)
# Set a very low persistence threshold to trigger alerts
# Or use AlertManager directly:

python3 -c "
from alert_manager import AlertManager
config = {'telegram_enabled': True}
am = AlertManager(config)
am.send_alert('TEST', 'This is a test alert from CYT', 'AA:BB:CC:DD:EE:FF')
"

# Check Telegram - you should receive a message!
```

### Step 2: Configure Auto-Start (Optional)

**Create Launch Agent** (macOS equivalent of systemd):

```bash
# Create launch agent directory
mkdir -p ~/Library/LaunchAgents

# Create plist file
nano ~/Library/LaunchAgents/com.cyt.monitor.plist
```

**Content**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cyt.monitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/thomaslavoie/Chasing-Your-Tail-NG/chasing_your_tail.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/thomaslavoie/Chasing-Your-Tail-NG</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/thomaslavoie/Chasing-Your-Tail-NG/logs/cyt_monitor.out</string>

    <key>StandardErrorPath</key>
    <string>/Users/thomaslavoie/Chasing-Your-Tail-NG/logs/cyt_monitor.err</string>
</dict>
</plist>
```

**Load and start**:
```bash
# Load launch agent
launchctl load ~/Library/LaunchAgents/com.cyt.monitor.plist

# Start now
launchctl start com.cyt.monitor

# Check status
launchctl list | grep cyt

# Stop
launchctl stop com.cyt.monitor

# Unload (disable auto-start)
launchctl unload ~/Library/LaunchAgents/com.cyt.monitor.plist
```

---

## Phase 7: Testing & Validation (30 minutes)

### Step 1: Run Basic Tests

**Test 1: Device Detection**:
```bash
# Let CYT + Kismet run for 10 minutes
# Then check:

cd ~/Chasing-Your-Tail-NG
sqlite3 cyt_history.db "SELECT COUNT(*) FROM device_history;"

# Should return > 10 (depends on your environment)
```

**Test 2: Persistence Scoring**:
```bash
# Run surveillance analyzer in demo mode
python3 surveillance_analyzer.py --demo

# Should generate:
# - Surveillance report in surveillance_reports/
# - KML file in kml_files/ (if GPS configured)
```

**Test 3: API Server** (optional):
```bash
# Start API server
python3 api_server.py

# In another terminal:
curl http://localhost:5000/api/alerts

# Should return JSON with recent alerts
```

### Step 2: Performance Check

**Monitor resource usage**:
```bash
# Open Activity Monitor
open -a "Activity Monitor"

# Look for:
# - kismet: Should use 2-5% CPU, 100-200 MB RAM
# - Python (CYT): Should use 1-3% CPU, 50-100 MB RAM

# Total: Should be well under 10% CPU, < 500 MB RAM
```

**If performance issues**:
```bash
# Check Kismet log for errors
tail -f /tmp/kismet/*.log

# Check CYT log
tail -f ~/Chasing-Your-Tail-NG/logs/cyt_monitor.log

# Restart if needed
sudo pkill kismet
./start_kismet_macos.sh en0
```

### Step 3: Verify All Features

**Checklist**:
```bash
# Core Features
- [ ] Kismet capturing wireless frames
- [ ] CYT detecting devices
- [ ] Device history saved to cyt_history.db
- [ ] Logs being written (logs/cyt_monitor.log)

# Advanced Features
- [ ] Behavioral detection working (test with behavioral_drone_detector.py)
- [ ] Persistence scoring (test with surveillance_analyzer.py --demo)
- [ ] Telegram alerts (if configured)
- [ ] API server (if using)

# Performance
- [ ] CPU usage < 10%
- [ ] RAM usage < 500 MB
- [ ] No crashes or errors in logs
```

---

## Troubleshooting Guide

### Problem 1: "Kismet won't start"

**Symptoms**:
```bash
sudo kismet -c en0
# Error: Could not open capture interface
```

**Solutions**:
```bash
# 1. Check interface exists
ifconfig | grep en0

# 2. Enable monitor mode first
sudo airport en0 sniff 1

# 3. Try different interface
ifconfig
# Look for other wireless: en1, en2, etc.

# 4. Check permissions
sudo kismet -c en0  # Use sudo

# 5. Check if driver loaded
lsmod | grep 8814au
```

### Problem 2: "CYT can't find Kismet database"

**Symptoms**:
```bash
python3 chasing_your_tail.py
# Error: No Kismet database found
```

**Solutions**:
```bash
# 1. Check Kismet is running
pgrep kismet

# 2. Check database location
ls -la /tmp/kismet/

# 3. Update config.json if needed
nano config.json
# Find: "kismet_db_path"
# Update to match actual path

# 4. Wait 1-2 minutes after Kismet starts
# Database may not exist immediately
```

### Problem 3: "Python import errors"

**Symptoms**:
```bash
python3 chasing_your_tail.py
# Error: ModuleNotFoundError: No module named 'cryptography'
```

**Solutions**:
```bash
# 1. Reinstall requirements
pip3 install -r requirements.txt

# 2. Check Python version
python3 --version
# Must be 3.9+

# 3. Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 chasing_your_tail.py
```

### Problem 4: "Alfa adapter not recognized"

**Symptoms**:
```bash
system_profiler SPUSBDataType | grep -i realtek
# No output
```

**Solutions**:
```bash
# 1. Check USB-C hub is working
system_profiler SPUSBDataType | grep -i hub

# 2. Try different USB port on hub

# 3. Try direct connection (USB-C to USB-A adapter)

# 4. Install driver manually (see Phase 2, Step 5)

# 5. Reboot MacBook
sudo reboot
```

### Problem 5: "Permission denied errors"

**Symptoms**:
```bash
python3 chasing_your_tail.py
# Error: Permission denied: /tmp/kismet/Kismet.kismet
```

**Solutions**:
```bash
# 1. Fix ownership
sudo chown -R $USER:staff /tmp/kismet/

# 2. Fix permissions
sudo chmod -R 755 /tmp/kismet/

# 3. Add user to kismet group (Linux-style)
# Not applicable on macOS

# 4. Run with elevated permissions (NOT RECOMMENDED)
sudo python3 chasing_your_tail.py
```

---

## Success Criteria Checklist

**You've successfully set up CYT on macOS when**:

### Hardware
- [x] MacBook Air M3 running smoothly
- [ ] Alfa AWUS1900 connected via USB-C hub
- [ ] Adapter recognized by macOS (`system_profiler SPUSBDataType`)
- [ ] Wireless interface visible (`ifconfig`)

### Software
- [ ] Homebrew installed (`brew --version`)
- [ ] Kismet installed (`kismet --version`)
- [ ] Aircrack-ng installed (`aircrack-ng --help`)
- [ ] Python dependencies installed (`pip3 list | grep cryptography`)

### Kismet
- [ ] Kismet starts without errors (`sudo kismet -c en0`)
- [ ] Database created (`ls /tmp/kismet/*.kismet`)
- [ ] Devices being captured (`sqlite3 /tmp/kismet/*.kismet "SELECT COUNT(*) FROM devices;"`)
- [ ] Web UI accessible (http://localhost:2501)

### CYT
- [ ] CYT starts without errors (`python3 chasing_your_tail.py`)
- [ ] Devices detected (check logs/cyt_monitor.log)
- [ ] History database populated (`sqlite3 cyt_history.db`)
- [ ] Behavioral detection works (`python3 behavioral_drone_detector.py`)

### Optional
- [ ] Telegram alerts configured and working
- [ ] GPS module connected (if purchased)
- [ ] Auto-start configured (launchctl)
- [ ] API server running (`curl http://localhost:5000/api/alerts`)

---

## Next Steps After Setup

### Week 1: Learning & Testing
```bash
1. Let CYT run for 24 hours, monitor logs
2. Walk around with MacBook, observe device detection
3. Test behavioral detection in different environments
4. Review TESTING_GUIDE.md, run test scenarios
```

### Week 2: Tuning
```bash
1. Analyze false positive rate
2. Adjust behavioral thresholds in config.json
3. Configure ignore lists (create_ignore_list.py)
4. Optimize persistence scoring
```

### Week 3: Advanced Features
```bash
1. Set up Telegram alerts
2. Configure API server for remote access
3. Test surveillance analyzer with real data
4. Create KML visualizations
```

### Week 4: Production Readiness
```bash
1. Configure auto-start
2. Test 24/7 operation
3. Monitor battery life (aim for 4-6 hours)
4. Document any macOS-specific issues
5. Share findings with CYT community
```

---

## Estimated Timeline Summary

**Phase 1: Hardware Setup** - 15 minutes
- Get USB-C hub
- Connect Alfa adapter
- Verify recognition

**Phase 2: Software Installation** - 30-45 minutes
- Install Homebrew
- Install Kismet, aircrack-ng, gpsd
- Install Alfa driver
- Configure wireless interface

**Phase 3: CYT Installation** - 15 minutes
- Clone repository (already done)
- Install Python dependencies
- Configure CYT
- Set up encrypted credentials

**Phase 4: Kismet Configuration** - 20-30 minutes
- Configure Kismet for macOS
- Test startup
- Verify packet capture

**Phase 5: Run CYT** - 10-15 minutes
- First test run
- Verify device detection
- Check logs

**Phase 6: Advanced Configuration** - Optional
- Telegram alerts (5 minutes)
- Auto-start (10 minutes)

**Phase 7: Testing** - 30 minutes
- Basic tests
- Performance check
- Feature verification

**Total Time**: **2-3 hours** (including breaks and troubleshooting)

---

## Quick Reference Commands

**Start Everything**:
```bash
# 1. Start Kismet
cd ~/Chasing-Your-Tail-NG
./start_kismet_macos.sh en0

# 2. Start CYT (new terminal)
cd ~/Chasing-Your-Tail-NG
python3 chasing_your_tail.py

# 3. Watch logs (new terminal)
tail -f ~/Chasing-Your-Tail-NG/logs/cyt_monitor.log
```

**Stop Everything**:
```bash
# Stop CYT (Ctrl+C in terminal)

# Stop Kismet
sudo pkill kismet
```

**Check Status**:
```bash
# Kismet running?
pgrep kismet

# CYT running?
ps aux | grep chasing_your_tail

# Recent devices
sqlite3 ~/Chasing-Your-Tail-NG/cyt_history.db "SELECT COUNT(*) FROM device_history;"
```

**View Logs**:
```bash
# CYT monitor log
tail -f ~/Chasing-Your-Tail-NG/logs/cyt_monitor.log

# Kismet log
tail -f /tmp/kismet/*.log
```

---

## macOS-Specific Tips

### Battery Life Optimization

**When on battery**:
```bash
# Reduce Kismet resource usage
# Edit ~/.kismet/kismet_site.conf
# Add:
channel_hop_speed=5  # Default is 3 (slower = less CPU)
track_device_timeout=30  # Faster device expiry
```

**Monitor battery**:
```bash
# Check battery status
pmset -g batt

# Estimate runtime:
# Kismet + CYT: ~4-6 hours on M3
```

### Thermal Management

**If MacBook gets hot**:
```bash
# Check CPU temperature
sudo powermetrics --samplers smc | grep -i "CPU die temperature"

# Reduce load:
# 1. Close unnecessary apps
# 2. Use laptop stand (better airflow)
# 3. Reduce Kismet channel hopping speed
```

### macOS Updates

**Before updating macOS**:
```bash
# 1. Stop all CYT/Kismet processes
sudo pkill kismet
pkill -f chasing_your_tail

# 2. Backup your data
cd ~
tar -czf cyt_backup_$(date +%Y%m%d).tar.gz Chasing-Your-Tail-NG/

# 3. Update macOS
# 4. Reinstall drivers if needed (Alfa AWUS1900)
```

---

## Support & Resources

**CYT Documentation**:
- Main README: `~/Chasing-Your-Tail-NG/README.md`
- Testing Guide: `~/Chasing-Your-Tail-NG/TESTING_GUIDE.md`
- Hardware Requirements: `~/Chasing-Your-Tail-NG/HARDWARE_REQUIREMENTS.md`

**Kismet Resources**:
- Official Docs: https://www.kismetwireless.net/docs/
- macOS Guide: https://www.kismetwireless.net/docs/readme/osx/

**Community**:
- GitHub Issues: https://github.com/SwampPop/Chasing-Your-Tail-NG/issues
- (Add Discord/forum if available)

**Emergency Contact**:
- If stuck, open GitHub issue with:
  - macOS version (`sw_vers`)
  - Error logs (last 50 lines)
  - Steps to reproduce

---

**Last Updated**: 2025-12-07
**Platform**: macOS (Apple Silicon M3)
**Version**: 1.0
**Maintained By**: CYT Project

**Good luck with your CYT deployment on macOS!**
