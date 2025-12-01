# CYT Production Deployment Checklist

**Complete checklist for production deployment**

Use this checklist to ensure nothing is missed when deploying CYT to production.

---

## 📋 Pre-Deployment (Before Installation)

### Hardware Verification
- [ ] Wireless adapter verified working (see HARDWARE_REQUIREMENTS.md)
- [ ] Adapter supports monitor mode (tested with airmon-ng)
- [ ] Computing platform meets minimum specs
- [ ] Sufficient storage space (32GB+ recommended)
- [ ] Power supply adequate (3A for Raspberry Pi)
- [ ] Network connectivity available (for AlertManager/API)
- [ ] GPS module working (if using location features)

### Software Preparation
- [ ] Linux OS installed and updated (`sudo apt-get update && sudo apt-get upgrade`)
- [ ] Python 3.9+ installed (`python3 --version`)
- [ ] pip installed (`pip3 --version`)
- [ ] Kismet installed (`kismet --version`)
- [ ] Git installed (`git --version`)
- [ ] Wireless tools installed (`airmon-ng --help`)

### Account Setup
- [ ] Root/sudo access confirmed
- [ ] User account created (if not using root)
- [ ] SSH access configured (for remote management)
- [ ] SSH keys generated and deployed
- [ ] Firewall rules planned (if applicable)

### Credentials Prepared
- [ ] Master password chosen (strong, documented securely)
- [ ] WiGLE API credentials obtained (optional)
- [ ] Telegram bot token obtained (optional, for alerts)
- [ ] API key generated (optional, for API server)

### Documentation Reviewed
- [ ] QUICK_START.md read
- [ ] HARDWARE_REQUIREMENTS.md consulted
- [ ] TESTING_GUIDE.md reviewed
- [ ] DAEMON.md understood
- [ ] HEALTH_MONITORING.md reviewed
- [ ] BEHAVIORAL_DRONE_DETECTION.md reviewed

---

## 📦 Installation Phase

### Step 1: System Preparation
- [ ] System updated: `sudo apt-get update && sudo apt-get upgrade`
- [ ] Reboot if kernel updated
- [ ] System time correct (`date`)
- [ ] Timezone set correctly (`sudo timedatectl set-timezone America/New_York`)
- [ ] Hostname set (`sudo hostnamectl set-hostname cyt-monitor-01`)

### Step 2: Install Dependencies
- [ ] Python dependencies: `sudo pip3 install -r requirements.txt`
- [ ] Kismet installed: `sudo apt-get install kismet`
- [ ] Wireless tools: `sudo apt-get install aircrack-ng`
- [ ] All imports verify: `python3 -c "import flask, requests, jsonschema"`

### Step 3: Install CYT
- [ ] Create installation directory: `sudo mkdir -p /opt/cyt`
- [ ] Clone repository: `cd /opt && sudo git clone <repo> cyt`
- [ ] Set ownership: `sudo chown -R $USER:$USER /opt/cyt`
- [ ] Verify files: `ls -lh /opt/cyt`

### Step 4: Configuration
- [ ] Master password set: `cd /opt/cyt && python3 secure_credentials.py`
- [ ] WiGLE credentials added (if using)
- [ ] Config.json reviewed: `nano config.json`
- [ ] Paths verified (kismet_logs, ignore_lists)
- [ ] Interface name set (wlan0mon, etc.)
- [ ] Config validated: `python3 config_validator.py`

### Step 5: Create Ignore Lists
- [ ] MAC ignore list created: `echo '[]' > ignore_lists/mac_ignore.json`
- [ ] SSID ignore list created: `echo '[]' > ignore_lists/ssid_ignore.json`
- [ ] Permissions set: `chmod 644 ignore_lists/*.json`

### Step 6: Optional Components
- [ ] API key generated: `python3 generate_api_key.py` (if using API)
- [ ] API key added to environment: `export CYT_API_KEY="..."`
- [ ] API key persisted: `echo 'export CYT_API_KEY="..."' >> ~/.bashrc`
- [ ] Telegram bot token in credentials (if using alerts)

---

## 🧪 Testing Phase

### Basic Function Tests
- [ ] Wireless adapter in monitor mode: `sudo airmon-ng start wlan0`
- [ ] Kismet starts manually: `sudo ./start_kismet_clean.sh wlan0mon`
- [ ] Kismet captures packets: `ls -lh /tmp/kismet/*.kismet`
- [ ] Kismet stops cleanly: `sudo pkill kismet`
- [ ] CYT Monitor starts: `python3 chasing_your_tail.py` (test 30 seconds)
- [ ] Daemon starts: `sudo python3 cyt_daemon.py start`
- [ ] All components running: `python3 cyt_daemon.py status`
- [ ] Daemon stops cleanly: `sudo python3 cyt_daemon.py stop`

### Feature Tests
- [ ] Health monitoring messages in logs
- [ ] Detections appear after 10 minutes
- [ ] History database created: `ls -lh cyt_history.db`
- [ ] AlertManager works (if configured): Test alert sent
- [ ] API server accessible (if enabled): `curl localhost:8080`

### Stress Test
- [ ] 2-hour stability test completed
- [ ] No memory leaks observed: `free -h`
- [ ] No disk space issues: `df -h`
- [ ] Logs reviewed for errors: `tail -200 logs/cyt_monitor.log`

---

## 🚀 Production Deployment

### Systemd Service Installation
- [ ] Service file copied: `sudo cp cyt.service /etc/systemd/system/`
- [ ] Working directory updated in service file (if not /opt/cyt)
- [ ] Systemd reloaded: `sudo systemctl daemon-reload`
- [ ] Service enabled: `sudo systemctl enable cyt`
- [ ] Service started: `sudo systemctl start cyt`
- [ ] Service status verified: `sudo systemctl status cyt`
- [ ] Journal logs accessible: `sudo journalctl -u cyt -f`

### Log Rotation Setup
- [ ] Logrotate configured:
```bash
sudo nano /etc/logrotate.d/cyt

# Add:
/opt/cyt/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 0644 root root
}
```
- [ ] Logrotate tested: `sudo logrotate -d /etc/logrotate.d/cyt`

### Monitoring Setup
- [ ] Monitoring solution chosen (manual / systemd / external)
- [ ] Alert destinations configured (Telegram / email / etc.)
- [ ] Test alert sent and received
- [ ] Monitoring dashboard created (if applicable)

### Backup Configuration
- [ ] Backup directory created: `/opt/cyt/backups`
- [ ] Backup script created (config, credentials, history DB)
- [ ] Backup cron job configured
- [ ] Test backup performed and verified
- [ ] Restore procedure documented and tested

### Security Hardening
- [ ] Firewall configured (if applicable): `sudo ufw status`
- [ ] SSH hardened (key-only, no root login)
- [ ] File permissions verified: `ls -lha /opt/cyt`
- [ ] Credentials file protected: `chmod 600 secure_credentials/*`
- [ ] Unnecessary services disabled
- [ ] fail2ban configured (optional but recommended)

---

## 🔍 Post-Deployment Verification

### Immediate Checks (First Hour)
- [ ] System running: `sudo systemctl status cyt`
- [ ] All components started: `python3 /opt/cyt/cyt_daemon.py status`
- [ ] Packets being captured: Check Kismet DB growth
- [ ] No errors in logs: `tail -100 /opt/cyt/logs/cyt_monitor.log`
- [ ] Health checks appearing: `grep "health check" /opt/cyt/logs/*.log`

### 24-Hour Checks
- [ ] Service still running: `sudo systemctl status cyt`
- [ ] No crashes in journal: `sudo journalctl -u cyt --since yesterday`
- [ ] Detections recorded: `sqlite3 /opt/cyt/cyt_history.db "SELECT COUNT(*) FROM appearances;"`
- [ ] Disk space adequate: `df -h`
- [ ] Memory usage stable: `free -h`
- [ ] CPU usage reasonable: `top -b -n 1`

### One-Week Checks
- [ ] No service restarts: `sudo systemctl status cyt`
- [ ] Log rotation working: `ls -lh /opt/cyt/logs/*.gz`
- [ ] Backup successful: `ls -lh /opt/cyt/backups/`
- [ ] Detections accurate (no excessive false positives)
- [ ] AlertManager working (if configured)
- [ ] API server accessible (if enabled)
- [ ] GPS tracking working (if applicable)

---

## 📊 Performance Tuning

### After One Week of Operation
- [ ] Review detection logs for patterns
- [ ] Identify false positives (add to ignore lists)
- [ ] Tune confidence thresholds:
  - Behavioral detection: `behavioral_drone_detection.confidence_threshold`
  - Persistence scoring: `detection_thresholds.persistence_score_critical`
- [ ] Adjust time windows if needed
- [ ] Optimize database size (if growing too fast)
- [ ] Review and update ignore lists

### Ignore List Management
- [ ] Create baseline ignore list: `python3 create_ignore_list.py`
- [ ] Review current ignore lists: `cat ignore_lists/*.json`
- [ ] Add known devices (home network, personal devices)
- [ ] Remove stale entries (devices no longer present)
- [ ] Backup ignore lists before changes

---

## 🆘 Incident Response Plan

### Documented Procedures
- [ ] Restart procedure documented
- [ ] Troubleshooting guide accessible
- [ ] Contact information recorded (if team deployment)
- [ ] Escalation path defined
- [ ] Rollback procedure tested

### Common Scenarios
- [ ] **Kismet crashes**: Health monitor detects, auto-restart (if enabled)
- [ ] **CYT crashes**: Systemd restarts service automatically
- [ ] **Disk full**: Log rotation + manual cleanup procedure
- [ ] **False positives**: Add to ignore list, tune thresholds
- [ ] **No detections**: Check Kismet capturing, adapter working

---

## 📝 Documentation

### Required Documentation
- [ ] Deployment notes created (date, version, configuration)
- [ ] Network diagram updated (if applicable)
- [ ] IP addresses documented
- [ ] Credentials stored securely (password manager)
- [ ] Contact information current
- [ ] Change log initialized

### Runbook Created
- [ ] Start/stop procedures
- [ ] Monitoring procedures
- [ ] Backup/restore procedures
- [ ] Troubleshooting steps
- [ ] Maintenance schedule
- [ ] Update procedure

---

## 🔄 Maintenance Schedule

### Daily
- [ ] Automated: Health checks (built-in)
- [ ] Automated: Detection logging

### Weekly
- [ ] Manual: Review logs for errors
- [ ] Manual: Check disk space
- [ ] Automated: Backup configuration

### Monthly
- [ ] Manual: Update ignore lists
- [ ] Manual: Review detections for false positives
- [ ] Manual: Tune detection thresholds
- [ ] Manual: Check for software updates

### Quarterly
- [ ] Manual: Test restore from backup
- [ ] Manual: Review and update documentation
- [ ] Manual: Security review
- [ ] Manual: Performance review

### Annually
- [ ] Manual: Major version upgrade (if available)
- [ ] Manual: Hardware refresh assessment
- [ ] Manual: Full system audit

---

## ✅ Production Readiness Sign-Off

**Pre-Production Approval** (before going live):
- [ ] Hardware verified and working
- [ ] Software installed and tested
- [ ] All tests passed (see TESTING_GUIDE.md)
- [ ] Configuration reviewed by team/yourself
- [ ] Security measures in place
- [ ] Backup/restore tested
- [ ] Documentation complete
- [ ] Monitoring configured
- [ ] Runbook created

**Deployment Approval** (ready to deploy):
- [ ] Maintenance window scheduled
- [ ] Team notified (if applicable)
- [ ] Backup of current system (if replacing existing)
- [ ] Rollback plan ready
- [ ] Final configuration review

**Post-Deployment Sign-Off** (after 24 hours):
- [ ] System running stable for 24 hours
- [ ] No critical errors in logs
- [ ] Detections working as expected
- [ ] Monitoring confirmed working
- [ ] Team trained (if applicable)
- [ ] Documentation updated with actual deployment details

---

## 📋 Deployment Record

**Fill out after deployment**:

```markdown
# CYT Deployment Record

**Deployment Date**: [Date]
**Deployed By**: [Name]
**Location**: [Physical location / Hostname]
**Version**: [Git commit hash or tag]

## Hardware
- **Platform**: [Raspberry Pi 4 4GB / Laptop / etc.]
- **Adapter**: [Model]
- **Storage**: [32GB microSD / etc.]
- **Power**: [Official PSU / PoE / etc.]

## Network
- **IP Address**: [Static IP or DHCP]
- **Interface**: [wlan0mon]
- **Network**: [SSID if applicable]

## Configuration
- **Kismet Health Monitoring**: Enabled / Disabled
- **Behavioral Detection**: Enabled / Disabled
- **AlertManager**: Enabled / Disabled
- **API Server**: Enabled / Disabled
- **GPS**: Enabled / Disabled

## Credentials
- **Master Password**: [Stored in: location]
- **API Key**: [Stored in: environment variable / file]
- **Telegram Bot**: [Configured: Yes / No]

## Testing Results
- **Pre-deployment tests**: Pass / Fail
- **Post-deployment verification**: Pass / Fail
- **24-hour soak test**: Pass / Fail

## Notes
[Any deployment-specific notes, issues encountered, workarounds, etc.]

## Sign-Off
- **Technical Review**: [Name] [Date]
- **Operational Approval**: [Name] [Date]
```

---

## 🎯 Success Criteria

**Deployment considered successful when**:
- ✅ System runs continuously for 7 days without intervention
- ✅ Detections working accurately (OUI, Behavioral, Persistence)
- ✅ Health monitoring functional
- ✅ No critical errors in logs
- ✅ Resource usage stable (CPU, memory, disk)
- ✅ Backups successful
- ✅ Monitoring/alerting working
- ✅ Documentation complete and accurate
- ✅ Team trained and comfortable with system

---

## 🔚 Decommissioning Checklist (Future)

**When retiring a CYT installation**:
- [ ] Backup final configuration and data
- [ ] Export important detections from history database
- [ ] Stop service: `sudo systemctl stop cyt`
- [ ] Disable service: `sudo systemctl disable cyt`
- [ ] Archive logs
- [ ] Document reason for decommission
- [ ] Update network documentation
- [ ] Securely wipe if redeploying hardware

---

**Estimated Deployment Time**: 2-4 hours (with testing)

**Recommended Team Size**: 1 person (can be done solo)

**Difficulty**: Intermediate (Linux admin skills required)

**Good luck with your deployment!** 🚀
