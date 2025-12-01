# CYT Daemon - Unified System Orchestration

## Overview

The CYT Daemon (`cyt_daemon.py`) is a unified orchestration system that manages all Chasing Your Tail components from a single command. No more manually starting Kismet, CYT Monitor, and API Server separately!

**One command starts everything:**
```bash
sudo python3 cyt_daemon.py start
```

---

## Components Managed

The daemon orchestrates three components in the correct dependency order:

### 1. Kismet (Required)
- **Purpose**: Wireless packet capture
- **Startup**: Configured from `config.json` → `kismet_health.startup_script`
- **Health Check**: Process monitoring via `pgrep`
- **Logs**: `./logs/kismet.log`
- **PID**: `./run/kismet.pid`

### 2. CYT Monitor (Required)
- **Purpose**: Threat detection and analysis
- **Startup**: `python3 chasing_your_tail.py`
- **Dependencies**: Requires Kismet running
- **Logs**: `./logs/cyt_monitor.log` (native CYT logs)
- **PID**: `./run/cyt_monitor.pid`

### 3. API Server (Optional)
- **Purpose**: REST API for mobile/web apps
- **Startup**: `python3 api_server.py`
- **Condition**: Only starts if `CYT_API_KEY` environment variable is set
- **Logs**: `./logs/api_server.log`
- **PID**: `./run/api_server.pid`

---

## Usage

### Basic Commands

```bash
# Start all components
sudo python3 cyt_daemon.py start

# Stop all components
sudo python3 cyt_daemon.py stop

# Restart all components
sudo python3 cyt_daemon.py restart

# Check status
python3 cyt_daemon.py status
```

### Command Output

**Start:**
```
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

**Status:**
```
============================================================
CYT System Status
============================================================

✓ Kismet               RUNNING (PID: 12345)
✓ CYT Monitor          RUNNING (PID: 12346)
✗ API Server           STOPPED (optional)

============================================================
```

**Stop:**
```
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
```

---

## How It Works

### Startup Sequence

```
1. Kismet
   ├─ Execute startup script (./start_kismet_clean.sh wlan0mon)
   ├─ Wait 10 seconds for Kismet to initialize
   ├─ Verify Kismet process is running (pgrep)
   ├─ Write PID to ./run/kismet.pid
   └─ ✓ Kismet ready

2. CYT Monitor
   ├─ Launch: python3 chasing_your_tail.py
   ├─ Redirect output to ./logs/cyt_monitor.log
   ├─ Wait 3 seconds for initialization
   ├─ Write PID to ./run/cyt_monitor.pid
   └─ ✓ CYT Monitor ready

3. API Server (optional)
   ├─ Check: CYT_API_KEY environment variable set?
   ├─ If yes:
   │  ├─ Launch: python3 api_server.py
   │  ├─ Redirect output to ./logs/api_server.log
   │  ├─ Wait 2 seconds for initialization
   │  ├─ Write PID to ./run/api_server.pid
   │  └─ ✓ API Server ready
   └─ If no: Skip (API Server is optional)
```

### Shutdown Sequence

```
Shutdown Order (reverse of startup):
1. API Server  → SIGTERM → Wait 30s → SIGKILL if needed
2. CYT Monitor → SIGTERM → Wait 30s → SIGKILL if needed
3. Kismet      → pkill kismet → Verify stopped
```

**Graceful Shutdown**:
- Sends SIGTERM first (allows cleanup)
- Waits up to 30 seconds for process to exit
- Forces SIGKILL if process doesn't respond

---

## Process Management

### PID Files

All component PIDs are tracked in `./run/`:
- `./run/kismet.pid` - Kismet main process PID
- `./run/cyt_monitor.pid` - CYT Monitor PID
- `./run/api_server.pid` - API Server PID

**PID File Management**:
- Created when process starts
- Removed when process stops cleanly
- Auto-cleaned if stale (process no longer exists)

### Health Checking

The daemon verifies processes are running using:

1. **PID File Check**: Read PID from file, send signal 0 to verify existence
2. **Process Name Check**: For Kismet, use `pgrep -x kismet`
3. **Poll Check**: For tracked subprocesses, check `proc.poll()` returns None

### Logging

All component output is redirected to log files:

```bash
./logs/
├── cyt_daemon.log       # Daemon orchestration logs
├── kismet.log          # Kismet output
├── cyt_monitor.log     # CYT detection logs (native output)
└── api_server.log      # API server logs
```

**Log Rotation**: Not automatic - configure logrotate or use systemd journal

---

## Configuration

The daemon reads `config.json` for Kismet settings:

```json
{
  "kismet_health": {
    "startup_script": "./start_kismet_clean.sh",
    "interface": "wlan0mon"
  }
}
```

**Kismet Start Command**:
```bash
sudo ./start_kismet_clean.sh wlan0mon
```

---

## API Server Setup (Optional)

To enable the API Server:

```bash
# 1. Generate API key
python3 generate_api_key.py

# 2. Set environment variable
export CYT_API_KEY="your_generated_key"

# 3. Add to shell profile for persistence
echo 'export CYT_API_KEY="your_key"' >> ~/.bashrc
source ~/.bashrc

# 4. Now the daemon will start API Server automatically
sudo python3 cyt_daemon.py start
```

**Verify API Server Started**:
```bash
python3 cyt_daemon.py status
# Should show: ✓ API Server RUNNING (PID: xxxx)

# Test API
curl -H "X-API-Key: your_key" http://localhost:8080/status
```

---

## Systemd Integration (Production)

For production deployments, install CYT as a systemd service:

### Installation

```bash
# 1. Install CYT to /opt/cyt
sudo mkdir -p /opt/cyt
sudo cp -r /path/to/Chasing-Your-Tail-NG/* /opt/cyt/
cd /opt/cyt

# 2. Install Python dependencies
sudo pip3 install -r requirements.txt

# 3. Configure CYT (edit config.json)
sudo nano config.json

# 4. Set up credentials
sudo python3 secure_credentials.py
sudo python3 generate_api_key.py  # Optional, for API server

# 5. Install systemd service
sudo cp cyt.service /etc/systemd/system/
sudo systemctl daemon-reload

# 6. Enable service (start on boot)
sudo systemctl enable cyt.service

# 7. Start service
sudo systemctl start cyt.service
```

### Systemd Commands

```bash
# Start service
sudo systemctl start cyt

# Stop service
sudo systemctl stop cyt

# Restart service
sudo systemctl restart cyt

# Check status
sudo systemctl status cyt

# View logs
sudo journalctl -u cyt -f

# Enable autostart on boot
sudo systemctl enable cyt

# Disable autostart
sudo systemctl disable cyt
```

### Service Configuration

Edit `/etc/systemd/system/cyt.service` to customize:

```ini
[Unit]
Description=Chasing Your Tail - Wireless Surveillance Detection
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/opt/cyt
ExecStart=/usr/bin/python3 /opt/cyt/cyt_daemon.py start
ExecStop=/usr/bin/python3 /opt/cyt/cyt_daemon.py stop
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Key Settings**:
- `Type=forking`: Daemon spawns subprocesses
- `User=root`: Required for Kismet
- `Restart=on-failure`: Auto-restart if crashes
- `StandardOutput=journal`: Logs to systemd journal

---

## Troubleshooting

### Issue: Daemon Won't Start

**Symptom**: `cyt_daemon.py start` fails

**Diagnosis**:
```bash
# Check if running as root
whoami  # Should output: root

# Check config.json is valid
python3 config_validator.py

# Check dependencies
python3 -c "import flask, requests, jsonschema"

# Check Kismet script exists
ls -lh ./start_kismet_clean.sh
```

**Solutions**:
1. Must run with `sudo` (Kismet requires root)
2. Fix config.json validation errors
3. Install missing dependencies: `pip3 install -r requirements.txt`
4. Ensure `start_kismet_clean.sh` is executable: `chmod +x start_kismet_clean.sh`

---

### Issue: Kismet Fails to Start

**Symptom**: "✗ Kismet failed to start"

**Diagnosis**:
```bash
# Check Kismet logs
tail -50 ./logs/kismet.log

# Test Kismet manually
sudo ./start_kismet_clean.sh wlan0mon
pgrep kismet  # Should show PIDs

# Check wireless interface
iwconfig
# Should show wlan0mon in monitor mode
```

**Common Causes**:
- Wireless interface doesn't exist
- Interface not in monitor mode
- Kismet not installed
- Permission issues

**Solutions**:
```bash
# Put interface in monitor mode
sudo airmon-ng start wlan0

# Install Kismet
sudo apt-get install kismet

# Check permissions
ls -lh ./start_kismet_clean.sh  # Should be executable
```

---

### Issue: CYT Monitor Exits Immediately

**Symptom**: "✗ CYT Monitor failed to start (exited with code 1)"

**Diagnosis**:
```bash
# Check CYT Monitor logs
tail -50 ./logs/cyt_monitor.log

# Test CYT Monitor manually
python3 chasing_your_tail.py
# Watch for errors
```

**Common Causes**:
- Kismet not running (dependency)
- Database validation failed
- Config.json errors
- Missing dependencies

**Solutions**:
1. Ensure Kismet is running: `python3 cyt_daemon.py status`
2. Fix config.json: `python3 config_validator.py`
3. Install dependencies: `pip3 install -r requirements.txt`
4. Check database exists: `ls -lh *.kismet`

---

### Issue: API Server Doesn't Start

**Symptom**: "⊘ Skipping API Server (CYT_API_KEY not configured)"

**This is normal!** API Server is optional.

**To enable**:
```bash
# Set API key environment variable
export CYT_API_KEY="your_key"

# Restart daemon
sudo python3 cyt_daemon.py restart

# Verify
python3 cyt_daemon.py status
# Should show: ✓ API Server RUNNING
```

---

### Issue: Processes Won't Stop

**Symptom**: "⚠ Some components may still be running"

**Force stop all**:
```bash
# Force kill Kismet
sudo pkill -9 kismet

# Force kill CYT Monitor
pkill -9 -f chasing_your_tail.py

# Force kill API Server
pkill -9 -f api_server.py

# Clean up PID files
rm -f ./run/*.pid

# Verify all stopped
python3 cyt_daemon.py status
```

---

### Issue: Stale PID Files

**Symptom**: Status shows "RUNNING" but process doesn't exist

**Clean up**:
```bash
# Remove stale PID files
rm -f ./run/*.pid

# Verify status
python3 cyt_daemon.py status
# Should show all STOPPED

# Restart
sudo python3 cyt_daemon.py start
```

---

## Advanced Usage

### Custom Startup Order

Edit `PROCESSES` dictionary in `cyt_daemon.py`:

```python
# Modify startup delay (seconds)
PROCESSES['kismet']['startup_delay'] = 15  # Wait 15s instead of 10s

# Make API Server required
PROCESSES['api_server']['required'] = True
```

### Environment Variables

Set environment variables for all components:

```bash
# In shell before starting
export CYT_API_KEY="your_key"
export PYTHONUNBUFFERED=1  # Disable Python buffering
export LOG_LEVEL=DEBUG     # Increase logging verbosity

sudo -E python3 cyt_daemon.py start  # -E preserves environment
```

### Custom Log Locations

Edit `cyt_daemon.py`:

```python
# Change log directory
LOG_DIR = Path("/var/log/cyt")

# Change PID directory
PID_DIR = Path("/var/run/cyt")
```

---

## Performance Impact

**Resource Usage**:
- **Daemon itself**: Negligible (just manages subprocesses)
- **Memory**: ~5 MB for daemon + subprocess tracking
- **CPU**: <0.1% (only during start/stop operations)

**Process Tree**:
```
cyt_daemon.py (parent)
├── kismet (detached)
├── chasing_your_tail.py (managed)
└── api_server.py (managed)
```

---

## Security Considerations

### Root Privileges

The daemon requires root because:
1. Kismet needs root for packet capture
2. Monitor mode requires root
3. Raw socket access requires root

**Minimize exposure**:
- Only `Kismet` truly needs root
- Consider running CYT Monitor as non-root user (advanced)
- Use systemd security hardening (see cyt.service)

### PID File Security

PID files in `./run/` can be read by anyone:
- No sensitive data in PID files
- Just process IDs (public information)

### Log File Security

Logs may contain MAC addresses and SSIDs:
- Restrict read access: `chmod 600 ./logs/*.log`
- Rotate and archive securely
- Consider encrypting archived logs

---

## Monitoring & Debugging

### Real-time Log Monitoring

```bash
# Follow all logs simultaneously
tail -f ./logs/*.log

# Just CYT Monitor
tail -f ./logs/cyt_monitor.log | grep -E '(DRONE|BEHAVIORAL|PERSISTENT)'

# Just daemon
tail -f ./logs/cyt_daemon.log
```

### Process Monitoring

```bash
# Watch process tree
watch -n 1 'pstree -p | grep -E "(kismet|python)"'

# Monitor resource usage
top -p $(cat ./run/*.pid | tr '\n' ',' | sed 's/,$//')
```

### Debugging Failed Starts

```bash
# Increase daemon verbosity (edit cyt_daemon.py)
logging.basicConfig(level=logging.DEBUG)  # Change INFO to DEBUG

# Run in foreground (see all output)
sudo python3 cyt_daemon.py start
# Watch console output

# Check exit codes
echo $?  # 0 = success, 1 = failure
```

---

## Production Deployment Checklist

- [ ] Install to `/opt/cyt` (not home directory)
- [ ] Install systemd service
- [ ] Enable autostart: `systemctl enable cyt`
- [ ] Configure log rotation
- [ ] Set up AlertManager (Telegram bot)
- [ ] Generate and secure API key
- [ ] Test start/stop/restart
- [ ] Verify health monitoring working
- [ ] Test graceful shutdown
- [ ] Monitor for 24 hours
- [ ] Document any custom configuration

---

## Migration from Manual Start

**Before** (manual):
```bash
# Start Kismet
sudo ./start_kismet_clean.sh wlan0mon

# Wait...

# Start CYT
python3 chasing_your_tail.py

# In another terminal...
# Start API
python3 api_server.py

# To stop: Ctrl+C in each terminal, pkill kismet
```

**After** (daemon):
```bash
# Start everything
sudo python3 cyt_daemon.py start

# To stop
sudo python3 cyt_daemon.py stop
```

**Benefits**:
- ✅ Single command for all components
- ✅ Correct startup order guaranteed
- ✅ Unified logging
- ✅ Graceful shutdown
- ✅ Process tracking
- ✅ Status monitoring
- ✅ Systemd integration

---

## Comparison: Daemon vs Manual

| Feature | Manual Start | Daemon |
|---------|--------------|--------|
| **Commands** | 3+ separate commands | 1 command |
| **Startup Order** | Manual coordination | Automatic |
| **Dependency Handling** | User must wait | Automatic delays |
| **Shutdown** | Ctrl+C + pkill | Graceful SIGTERM |
| **Process Tracking** | Manual (ps/top) | Automatic PID files |
| **Logs** | Scattered terminals | Unified in ./logs/ |
| **Status Check** | ps/pgrep commands | `status` command |
| **Systemd Integration** | Manual service files | Included |
| **Error Handling** | Manual diagnosis | Logged + exit codes |

---

## Future Enhancements

Planned improvements:

- [ ] **Auto-recovery**: Restart failed components automatically
- [ ] **Email alerts**: Notify on component failures
- [ ] **Web dashboard**: Real-time status via web UI
- [ ] **Metrics export**: Prometheus/Grafana integration
- [ ] **Multi-instance**: Run multiple CYT instances
- [ ] **Configuration reload**: Update config without restart
- [ ] **Rollback**: Revert to previous version on failure

---

**Last Updated**: December 1, 2025
**Version**: 1.0
**Status**: Production Ready

---

## Quick Reference

```bash
# Start everything
sudo python3 cyt_daemon.py start

# Stop everything
sudo python3 cyt_daemon.py stop

# Restart
sudo python3 cyt_daemon.py restart

# Check status
python3 cyt_daemon.py status

# View logs
tail -f ./logs/cyt_monitor.log

# Systemd service
sudo systemctl start cyt      # Start
sudo systemctl stop cyt       # Stop
sudo systemctl status cyt     # Status
sudo journalctl -u cyt -f     # Logs
```
