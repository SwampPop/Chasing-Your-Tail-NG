# Kismet Health Monitoring System

## Overview

The Kismet Health Monitoring system provides automated monitoring and recovery for the Kismet packet capture service. This prevents silent failures where CYT continues running but stops detecting threats because Kismet has crashed or frozen.

## Features

### 1. Multi-Layer Health Checks

**Process Check**: Verifies Kismet is running
- Uses `pgrep` to check for running Kismet process
- Logs process IDs when found

**Database Check**: Verifies database exists and is accessible
- Finds latest Kismet database file
- Checks file permissions and accessibility

**Update Check**: Verifies database is being actively written
- Tracks database modification time
- Alerts if database hasn't been updated recently

**Freshness Check**: Verifies Kismet is capturing data
- Queries database for most recent device timestamp
- Configurable threshold (default: 5 minutes)
- Alerts if no new devices detected within threshold

### 2. Auto-Recovery

**Automatic Restart**: Optional automatic Kismet restart on failure
- Kills existing Kismet processes
- Launches Kismet using configured startup script
- Verifies restart was successful

**Restart Protection**:
- Cooldown period prevents restart loops (60 seconds minimum between restarts)
- Maximum restart attempts before manual intervention required (default: 3)
- Consecutive failure tracking

### 3. Alert Integration

**AlertManager Integration**: Sends critical alerts on health failures
- Audio alerts via system speaker
- Telegram notifications (if configured)
- Different priority levels based on severity

**Detailed Logging**: All health events logged
- Health check results
- Failure reasons with specific details
- Recovery attempts and outcomes

## Configuration

Add the following section to `config.json`:

```json
{
  "kismet_health": {
    "enabled": true,
    "check_interval_cycles": 5,
    "data_freshness_threshold_minutes": 5,
    "auto_restart": false,
    "max_restart_attempts": 3,
    "startup_script": "./start_kismet_clean.sh",
    "interface": "wlan0mon"
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable health monitoring |
| `check_interval_cycles` | integer | `5` | How often to check health (in monitoring cycles) |
| `data_freshness_threshold_minutes` | integer | `5` | Alert if no new data in X minutes |
| `auto_restart` | boolean | `false` | Automatically restart Kismet on failure |
| `max_restart_attempts` | integer | `3` | Max auto-restart attempts before giving up |
| `startup_script` | string | `./start_kismet_clean.sh` | Path to Kismet startup script |
| `interface` | string | `wlan0mon` | Wireless interface for Kismet |

## Usage

### Basic Usage (Monitoring Only)

Enable health monitoring without auto-restart:

```json
{
  "kismet_health": {
    "enabled": true,
    "check_interval_cycles": 5,
    "data_freshness_threshold_minutes": 5,
    "auto_restart": false
  }
}
```

This configuration will:
- Check Kismet health every 5 monitoring cycles
- Alert if no new data detected in 5 minutes
- Log all health issues
- Send alerts via AlertManager (if configured)
- **NOT** automatically restart Kismet

### Production Usage (Auto-Recovery)

Enable full auto-recovery for production deployments:

```json
{
  "kismet_health": {
    "enabled": true,
    "check_interval_cycles": 3,
    "data_freshness_threshold_minutes": 3,
    "auto_restart": true,
    "max_restart_attempts": 5,
    "startup_script": "/opt/cyt/start_kismet_clean.sh",
    "interface": "wlan0mon"
  }
}
```

This configuration will:
- Check health every 3 cycles (more frequent)
- Alert if no new data in 3 minutes (tighter threshold)
- **Automatically restart Kismet** on failure
- Allow up to 5 restart attempts
- Use production startup script path

## Health Check Flow

```
Every N Cycles:
├─ 1. Check if Kismet process is running
│  └─ FAIL → Attempt restart (if auto_restart enabled)
│
├─ 2. Check if database exists
│  └─ FAIL → Alert + Log (cannot auto-recover)
│
├─ 3. Check if database is being updated
│  └─ FAIL → Log warning (may be normal if no activity)
│
└─ 4. Check data freshness (query database)
   └─ FAIL → Alert + Attempt restart (if auto_restart enabled)
```

## Alerts

### Alert Levels

**CRITICAL**: Sent when Kismet is unhealthy
- Process not running
- No fresh data detected
- Auto-restart failed

**WARNING**: Sent when auto-restart succeeds
- Kismet was down but is now recovered

### Alert Messages

**Example: Kismet Not Running**
```
Kismet Health Alert: Kismet process not running | Auto-restart SUCCESSFUL
```

**Example: No Fresh Data**
```
Kismet Health Alert: No fresh data in 5 minutes | Auto-restart FAILED - manual intervention required!
```

**Example: Database Missing**
```
Kismet Health Alert: Kismet database not found
```

## Logging

All health monitoring events are logged to the main CYT log file:

```
INFO - Performing Kismet health check (cycle 5)
DEBUG - ✓ Kismet health check passed | Last check: 0s ago | Consecutive failures: 0 | Restart count: 0/3
```

```
ERROR - ⚠️  Kismet health check FAILED: No fresh data in 5 minutes
WARNING - Attempting to restart Kismet (attempt 1)
INFO - Kismet restart initiated. Waiting 10s for startup...
INFO - ✓ Kismet restart successful!
```

## Testing

### Test the Health Monitor

Run the standalone health monitor test:

```bash
python3 kismet_health_monitor.py
```

This will:
- Check if Kismet is running
- Check database status
- Check data freshness
- Display detailed health report

### Simulate Failures

**Test Process Failure**:
```bash
# Stop Kismet
sudo pkill kismet

# Check logs - should detect failure and alert
tail -f logs/cyt_log_*.log
```

**Test Database Freshness**:
```bash
# Stop Kismet but leave database in place
sudo pkill kismet

# Wait for freshness threshold (5 minutes)
# Health monitor will detect stale data and alert
```

**Test Auto-Restart**:
```bash
# Enable auto_restart in config.json
# Stop Kismet
sudo pkill kismet

# Health monitor should automatically restart Kismet
# Check logs for restart success/failure
```

## Troubleshooting

### Health Monitor Not Running

**Symptom**: No health check messages in logs

**Solutions**:
1. Check `kismet_health.enabled` is `true` in config.json
2. Verify config validation passed at startup
3. Check for initialization errors in logs

### False Positives (Healthy Kismet Flagged as Unhealthy)

**Symptom**: Health alerts when Kismet appears to be working

**Solutions**:
1. Increase `data_freshness_threshold_minutes` (no activity in monitored area)
2. Verify Kismet is actually capturing packets (`kismet_server --version`)
3. Check Kismet logs for errors

### Auto-Restart Not Working

**Symptom**: Health monitor detects failure but doesn't restart Kismet

**Solutions**:
1. Verify `auto_restart` is `true` in config.json
2. Check `startup_script` path is correct and executable
3. Verify CYT is running with sufficient permissions (sudo may be required)
4. Check if max restart attempts reached
5. Verify restart cooldown hasn't prevented restart

### Restart Loops

**Symptom**: Kismet keeps restarting repeatedly

**Solutions**:
1. Check Kismet logs for startup errors
2. Verify wireless interface exists and is in monitor mode
3. Check for hardware issues with wireless adapter
4. Reduce `max_restart_attempts` to prevent endless loops
5. Disable `auto_restart` and investigate root cause manually

## Architecture

### Components

**KismetHealthMonitor** (`kismet_health_monitor.py`)
- Standalone health monitoring class
- No dependencies on CYT core logic
- Can be used independently for testing

**CYTMonitorApp Integration** (`chasing_your_tail.py`)
- Initializes health monitor from config
- Calls health checks in main monitoring loop
- Integrates with AlertManager for notifications

**Config Validation** (`config_validator.py`)
- Validates health monitoring configuration
- Ensures valid parameter ranges

### Health Check Cycle

```
Main Loop (every check_interval seconds):
│
├─ Process devices (every cycle)
├─ Rotate tracking lists (every list_update_interval cycles)
├─ Health check (every health_check_interval cycles) ← NEW
│  ├─ Run comprehensive health check
│  ├─ Attempt auto-recovery if needed
│  └─ Send alerts via AlertManager
└─ Archive detections to history
```

## Security Considerations

### Auto-Restart Risks

**Privilege Escalation**: Auto-restart requires root privileges to kill and start Kismet
- Ensure CYT runs with appropriate permissions
- Consider using sudo with NOPASSWD for specific commands only

**Restart Script Security**: The startup script is executed with elevated privileges
- Verify `startup_script` path points to trusted script
- Ensure script cannot be modified by unauthorized users
- Use absolute paths in configuration

### Resource Exhaustion

**Restart Limits**: Max restart attempts prevent infinite restart loops
- Default: 3 attempts before manual intervention required
- Cooldown: 60 seconds minimum between restarts
- Prevents resource exhaustion from rapid restarts

## Performance Impact

Health monitoring has minimal performance overhead:

**CPU Usage**: Negligible (simple process checks and database queries)

**Memory Usage**: < 1 MB for health monitor instance

**Database Impact**: One query per health check cycle
- Default: Every 5 monitoring cycles (every 5 minutes if check_interval=60s)
- Query is simple and fast (SELECT MAX(last_time))

**Network Impact**: None (local checks only)

## Best Practices

1. **Start without auto-restart**: Monitor alerts manually for a few days
2. **Tune thresholds**: Adjust `data_freshness_threshold_minutes` based on your environment
3. **Monitor logs**: Watch for false positives before enabling auto-restart
4. **Use AlertManager**: Configure Telegram notifications for remote monitoring
5. **Test recovery**: Regularly test auto-restart by stopping Kismet manually
6. **Plan for failures**: Have manual recovery procedures documented

## Roadmap

Future enhancements planned:

- [ ] Health metrics export (Prometheus/Grafana)
- [ ] Configurable restart strategies (exponential backoff)
- [ ] Integration with system monitoring (systemd watchdog)
- [ ] Database corruption detection and recovery
- [ ] Network connectivity checks before restart
- [ ] Smart restart scheduling (avoid restarts during active detections)

## Related Documentation

- [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) - Overview of all system integrations
- [CLAUDE.md](CLAUDE.md) - Project overview and architecture
- [alert_manager.py](alert_manager.py) - Alert system documentation

---

**Last Updated**: December 1, 2025
**Version**: 1.0
**Status**: Production Ready
