# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chasing Your Tail (CYT) is a Wi-Fi probe request analyzer that monitors and tracks wireless devices by analyzing their probe requests. The system integrates with Kismet for packet capture and WiGLE API for SSID geolocation analysis.

## Core Architecture

### Main Components
- **chasing_your_tail.py**: Core monitoring engine that queries Kismet SQLite databases in real-time
- **cyt_gui.py**: Enhanced Tkinter GUI interface for controlling the system with surveillance analysis
- **surveillance_analyzer.py**: Main surveillance detection orchestrator with GPS correlation and advanced KML visualization
- **surveillance_detector.py**: Core persistence detection engine for identifying suspicious device patterns
- **gps_tracker.py**: GPS tracking integration with location clustering and spectacular Google Earth KML generation
- **probe_analyzer.py**: Post-processing tool for analyzing collected probe data with WiGLE integration
- **start_kismet_clean.sh**: ONLY working Kismet startup script (all others moved to old_scripts/)
- **Security modules**: `secure_*.py` files providing SQL injection prevention and encrypted credentials

### Data Flow
1. Kismet captures wireless frames and stores in SQLite database
2. Main monitoring script queries database every 60 seconds for new devices/probes
3. System maintains sliding time windows (5, 10, 15, 20 minutes) to track device persistence
4. Probe requests are filtered against ignore lists and logged when devices reappear across time windows
5. Post-analysis tool can query WiGLE API for SSID geolocation data

### Configuration System
All paths, API keys, and timing parameters are centralized in `config.json`:
- Kismet database path pattern
- Log and ignore list directories  
- WiGLE API credentials
- Time window configurations
- Geographic search boundaries

## Common Development Commands

### Security Setup (REQUIRED FIRST TIME)
```bash
# Install secure dependencies
pip3 install -r requirements.txt

# Migrate credentials from insecure config.json (if needed)
python3 migrate_credentials.py

# Verify security hardening
python3 chasing_your_tail.py
# Should show: "🔒 SECURE MODE: All SQL injection vulnerabilities have been eliminated!"
```

### Running the System
```bash
# Start enhanced GUI interface (includes surveillance analysis button)
python3 cyt_gui.py

# Run core monitoring (command line) - NOW SECURE!
python3 chasing_your_tail.py

# Analyze collected data (past 14 days, local only - default, API-safe)
python3 probe_analyzer.py

# Analyze past 7 days only
python3 probe_analyzer.py --days 7

# Analyze ALL logs (may be slow for large datasets)
python3 probe_analyzer.py --all-logs

# Analyze WITH WiGLE API calls (consumes API credits!)
python3 probe_analyzer.py --wigle

# Start Kismet (ONLY working script)
./start_kismet_clean.sh

# Check if running
ps aux | grep kismet
```

### Kismet Startup
Kismet automatically starts on boot via crontab and can be started manually:

```bash
# Manual startup (ONLY working script)
./start_kismet_clean.sh

# Check if running
ps aux | grep kismet

# Kill if needed (use direct kill, not pkill)
for pid in $(pgrep kismet); do sudo kill -9 $pid; done
```

**Auto-start Setup (FIXED July 23, 2025):**
- **Kismet**: Starts automatically 60 seconds after boot via root crontab using `start_kismet_clean.sh`
- **GUI**: Starts automatically 120 seconds after boot via user crontab using `start_gui.sh`
- Root crontab: `sudo crontab -l` - handles Kismet only
- User crontab: `crontab -l` - handles GUI only
- **CRITICAL FIX**: ALL broken startup scripts moved to `old_scripts/` (had hanging pkill commands)
- **GUI FIX**: Restored missing `start_gui.sh` that was accidentally moved during cleanup
- **Key Insight**: Post-reboot startup should NEVER attempt process cleanup

### Surveillance Detection & Advanced Visualization
```bash
# NEW: Automatic GPS extraction from Kismet with spectacular KML visualization
python3 surveillance_analyzer.py

# Run analysis with demo GPS data (for testing - uses Phoenix coordinates)
python3 surveillance_analyzer.py --demo

# Analyze specific Kismet database for surveillance patterns
python3 surveillance_analyzer.py --kismet-db /path/to/kismet.db

# Focus on stalking detection only with persistence scoring
python3 surveillance_analyzer.py --stalking-only --min-persistence 0.8

# Export results to JSON for further analysis
python3 surveillance_analyzer.py --output-json analysis_results.json

# Analyze with external GPS data from JSON file
python3 surveillance_analyzer.py --gps-file gps_coordinates.json
```

### GUI Features
The enhanced GUI (`cyt_gui.py`) now includes:
- **🗺️ Surveillance Analysis** button - Runs GPS-correlated persistence detection with advanced KML visualization
- **📈 Analyze Logs** button - Analyzes historical probe request data
- **Real-time GPS integration** - Automatically uses Bluetooth GPS data from Kismet
- **Spectacular KML generation** - Creates professional Google Earth visualizations with threat-level styling

### GPS Integration & KML Visualization (ENHANCED!)
The system now automatically extracts GPS coordinates from Kismet databases and creates spectacular visualizations:

- **Automatic GPS Detection**: No manual GPS file needed - extracts coordinates from Kismet
- **Real-time Correlation**: Links device appearances to GPS locations with precise timing
- **Location Clustering**: Groups nearby GPS points (within 100m) for analysis
- **Professional KML Generation**: Creates spectacular Google Earth visualizations with:
  - Color-coded persistence level markers (green/yellow/red)
  - Device tracking paths showing movement correlation
  - Rich balloon content with detailed device intelligence
  - Activity heatmaps and intensity zones
  - Temporal analysis with time-based pattern detection
- **Multi-location Tracking**: Detects devices following across different locations with visual tracking paths

### Ignore List Management
```bash
# Create new ignore lists from current Kismet data
python3 legacy/create_ignore_list.py  # Moved to legacy folder
```
**Note**: Ignore lists are now stored as JSON files in `./ignore_lists/`

### Project Structure & Key File Locations

#### Core Files (Main Directory) - CLEANED July 23, 2025
- **Core Python Scripts**: `chasing_your_tail.py`, `surveillance_analyzer.py`, `cyt_gui.py`, `probe_analyzer.py`, `gps_tracker.py`, `surveillance_detector.py`
- **Security Modules**: `secure_*.py` (4 files), `input_validation.py`, `migrate_credentials.py`
- **Configuration**: `config.json`, `requirements.txt`
- **Working Startup Scripts**: `start_kismet_clean.sh` (Kismet), `start_gui.sh` (GUI)
- **Documentation**: `CLAUDE.md`, `README.md`

#### Output Directories
- **Surveillance Reports**: `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.md` (markdown)
- **HTML Reports**: `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.html` (styled HTML with pandoc)
- **KML Visualizations**: `./kml_files/surveillance_analysis_YYYYMMDD_HHMMSS.kml` (spectacular Google Earth files)
- **CYT Logs**: `./logs/cyt_log_MMDDYY_HHMMSS`
- **Analysis Logs**: `./analysis_logs/surveillance_analysis.log`
- **Probe Reports**: `./reports/probe_analysis_report_YYYYMMDD_HHMMSS.txt`

#### Configuration & Data
- **Ignore Lists**: `./ignore_lists/mac_list.json` and `./ignore_lists/ssid_list.json`
- **Kismet Database**: Path specified in config.json (typically `/home/matt/kismet_logs/*.kismet`)

#### Archive Directories - CLEANED July 23, 2025
- **old_scripts/**: All broken startup scripts with hanging pkill commands (temporarily held `start_gui.sh`)
- **docs_archive/**: Session notes, old configs, backup files, duplicate logs
- **legacy/**: Original legacy code archive (pre-security hardening)

## Technical Details

### Time Window System
The core algorithm maintains four overlapping time windows to detect device persistence:
- Recent: Past 5 minutes
- Medium: 5-10 minutes ago  
- Old: 10-15 minutes ago
- Oldest: 15-20 minutes ago

Every 5 cycles (5 minutes), lists are rotated and updated from fresh database queries.

### Database Interaction
System reads from live Kismet SQLite databases using direct SQL queries. Key tables:
- `devices`: Contains MAC addresses, device types, and JSON device details
- Probe request data is embedded in JSON `device` field under `dot11.device.last_probed_ssid_record`

### Ignore List Format
- **MAC lists**: Python list variable `ignore_list = ['MAC1', 'MAC2', ...]`
- **SSID lists**: Python list variable `non_alert_ssid_list = ['SSID1', 'SSID2', ...]`
- Lists are loaded via `exec()` at runtime

### WiGLE Integration
Probe analyzer can query WiGLE API for SSID location data using securely encrypted API credentials.

### Surveillance Detection System
Advanced persistence detection algorithms analyze device behavior patterns:
- **Temporal Persistence**: Detects devices appearing consistently over time
- **Location Correlation**: Identifies devices following across multiple locations  
- **Probe Pattern Analysis**: Analyzes SSID probe requests for suspicious patterns
- **Timing Analysis**: Detects unusual appearance timing (work hours, off-hours, regular intervals)
- **Persistence Scoring**: Assigns weighted scores (0-1.0) based on combined indicators
- **Multi-location Tracking**: Specialized algorithms for detecting following behavior across locations

### GPS Integration & Spectacular KML Export
- **Location Clustering**: Groups nearby GPS coordinates (configurable threshold)
- **Session Management**: Tracks location sessions with timeout handling
- **Device Correlation**: Links device appearances to specific GPS locations
- **Professional KML Generation**: Creates spectacular Google Earth files with:
  - Color-coded location markers with persistence-level styling
  - Device tracking paths with threat-level visualization
  - Rich interactive balloon content with device intelligence
  - Activity heatmaps showing surveillance intensity zones
  - Temporal analysis overlays for time-based pattern detection
  - Professional document metadata and feature descriptions
- **Multi-location Analysis**: Identifies devices seen across multiple locations with visual tracking paths

## Security Hardening (NEW!)

### Critical Vulnerabilities FIXED
- **SQL Injection**: All database queries now use parameterized statements
- **Remote Code Execution**: Eliminated dangerous `exec()` calls in ignore list loading
- **Credential Exposure**: API keys now encrypted with master password
- **Input Validation**: Comprehensive sanitization of all inputs
- **Error Handling**: Security-focused logging and error boundaries

### Security Files
- `secure_ignore_loader.py`: Safe ignore list loading (replaces exec())
- `secure_database.py`: SQL injection prevention 
- `secure_credentials.py`: Encrypted credential management
- `secure_main_logic.py`: Secure monitoring logic
- `input_validation.py`: Input sanitization and validation
- `migrate_credentials.py`: Tool to migrate insecure credentials

### Security Logs
- `cyt_security.log`: Security events and audit trail
- All credential access is logged
- Failed validation attempts are tracked
- Database errors are monitored

**⚠️ IMPORTANT: Run `python3 migrate_credentials.py` before first use to secure your API keys!**