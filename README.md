# Chasing Your Tail (CYT)

A comprehensive wireless threat detection system that monitors and classifies wireless devices using behavioral pattern analysis. The system detects drones, war driving, rogue access points, packet sniffers, stalking patterns, and more - providing intelligent threat classification with specific response recommendations.

## 🚨 Security Notice

This project has been security-hardened to eliminate critical vulnerabilities:
- **SQL injection prevention** with parameterized queries
- **Encrypted credential management** for API keys
- **Input validation** and sanitization
- **Secure ignore list loading** (no more `exec()` calls)

**⚠️ REQUIRED: Run `python3 migrate_credentials.py` before first use to secure your API keys!**

## Features

### Core Detection
- **Real-time Wi-Fi monitoring** with Kismet integration
- **🆕 Multi-threat classification system** - Automatically identifies 8 threat types:
  - **🚁 DRONE** - Aerial vehicles / drones
  - **🚗 WAR_DRIVING** - Mobile reconnaissance from vehicles
  - **📡 ROGUE_AP** - Evil twin / rogue access points
  - **👁️ PACKET_SNIFFER** - Passive monitoring devices
  - **🎯 STALKING** - Following patterns across locations
  - **🚶 WALK_BY_ATTACK** - Brief proximity attacks
  - **🔍 PENETRATION_TEST** - Active security scanning
  - **❓ UNKNOWN** - Suspicious but unclassified behavior
- **Multi-layer threat detection**:
  - **OUI matching** - Instant detection of known drones (DJI, Parrot, 3DR, Autel)
  - **Behavioral analysis** - 9-pattern analysis with confidence scoring
  - **Persistence scoring** - Time-window based surveillance detection
- **🆕 Intelligent threat classification** - Pattern-based threat type identification
- **🆕 Threat-specific recommendations** - Tailored response strategies for each threat type
- **🆕 Comprehensive behavioral reports** - Detailed analysis with GPS tracking and pattern breakdowns
- **🆕 Kismet health monitoring** - Multi-layer health checking with auto-restart capability

### Analysis & Visualization
- **Advanced surveillance detection** with GPS correlation and location clustering
- **🆕 Automatic GPS integration** - extracts coordinates from Bluetooth GPS via Kismet
- **Spectacular KML visualization** for Google Earth with professional styling and interactive content
- **Multi-format reporting** - Markdown, HTML (with pandoc), and KML outputs
- **WiGLE API integration** for SSID geolocation
- **Multi-location tracking algorithms** for detecting following behavior

### System Management
- **🆕 Unified daemon orchestration** - Single-command start/stop/restart/status for all components
- **Enhanced GUI interface** with surveillance analysis button
- **🆕 Live device feed in both GUI and TUI** backed by shared normalized device records
- **🆕 Shared Kismet DB freshness reporting** across interfaces
- **Organized file structure** with dedicated output directories
- **Comprehensive logging** and analysis tools
- **Systemd integration** for production deployments

## Multi-Threat Detection

CYT is not just a drone detector - it's a general-purpose wireless threat intelligence platform:

### What It Detects

**8 Distinct Threat Types** identified automatically:
- **Drones** (DJI, custom-built, aerial surveillance)
- **War Driving** (vehicle-based network mapping)
- **Rogue APs** (evil twin attacks, credential harvesting)
- **Packet Sniffers** (passive traffic monitoring)
- **Stalking** (devices following your movements)
- **Walk-By Attacks** (pedestrian proximity threats)
- **Penetration Tests** (active security scanning)
- **Unknown Threats** (suspicious but unclassified)

### How It Works

- **9 Behavioral Patterns** analyzed per device
- **Speed-Based Discrimination** (aerial/vehicle/pedestrian/stationary)
- **Pattern Combination Matching** for accurate classification
- **Confidence Scoring** for both detection and classification
- **Threat-Specific Recommendations** for each type

📖 **See the [Multi-Threat Detection Guide](MULTI_THREAT_DETECTION.md) for complete details, real-world scenarios, and response strategies.**

## 📱 Documentation as Kindle Ebooks

**Read CYT documentation on the go!** All documentation is available as Kindle ebooks for offline reference in the field.

### Available Ebook Collections

```bash
cd ~/my_projects/2_reference_docs

# Generate all 3 CYT ebooks
./generate_ebook_library.sh --cyt
```

This creates:
1. **CYT Complete User Manual** - Setup, deployment, investigation guides
2. **CYT Technical Reference** - Detection algorithms, health monitoring, testing
3. **CYT Beast Mode Deployment** - High-performance hardware, Pi 5 builds, deployment guides

**Perfect for**:
- Field deployments (offline access to full docs)
- Learning detection algorithms during downtime
- Hardware shopping (Beast Mode spec sheets)
- Troubleshooting without laptop access

**See Also**: `/my_projects/2_reference_docs/EBOOK_CONFIGURATIONS.md` for detailed configurations

## Requirements

- Python 3.6+
- Kismet wireless packet capture
- Wi-Fi adapter supporting monitor mode
- Linux-based system
- WiGLE API key (optional)

## Installation & Setup

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Security Setup (REQUIRED FIRST TIME)
```bash
# Migrate credentials from insecure config.json
python3 migrate_credentials.py

# Verify security hardening
python3 chasing_your_tail.py
# Should show: "🔒 SECURE MODE: All SQL injection vulnerabilities have been eliminated!"
```

### 3. Configure System
Edit `config.json` with your paths and settings:
- Kismet database path pattern
- Log and ignore list directories
- Time window configurations
- Geographic search boundaries

## Usage

### GUI Interface
```bash
python3 cyt_gui.py  # Enhanced GUI with surveillance analysis
```
**GUI Features:**
- 📡 **Live Feed tab** - Recently seen devices with signal, channel, type, and manufacturer
- 🩺 **DB freshness indicators** - active/stale status and database age
- 🗺️ **Surveillance Analysis** button - GPS-correlated persistence detection with spectacular KML visualization
- 📈 **Analyze Logs** button - Historical probe request analysis
- Real-time status monitoring and file generation notifications

### Terminal UI
```bash
python3 cyt_tui.py
```
**TUI Features:**
- `[1] Live Feed` with threat-coded rows (`D`, `B`, `P`)
- `[2] Dashboard` with Kismet DB freshness, age, alert counts, and subsystem status
- Filter and sort controls for rapid triage:
  - `f` cycle filters
  - `s` toggle sort
  - `h` help overlay
  - `1` / `2` / `Tab` switch views

### Command Line Monitoring

**🆕 Unified Daemon** (Recommended - starts all components):
```bash
# Start all components (Kismet + Monitor + API)
sudo python3 cyt_daemon.py start

# Check status
python3 cyt_daemon.py status

# Stop all components
sudo python3 cyt_daemon.py stop

# Restart all components
sudo python3 cyt_daemon.py restart
```

**Manual Component Startup** (Legacy/Debugging):
```bash
# Start core monitoring (secure)
python3 chasing_your_tail.py

# Start Kismet (ONLY working script - July 23, 2025 fix)
sudo ./start_kismet_clean.sh wlan0mon
```

**Production Deployment** (Systemd):
```bash
# Install and enable service
sudo cp cyt.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cyt
sudo systemctl start cyt

# Check status
sudo systemctl status cyt

# View logs
sudo journalctl -u cyt -f
```

### Data Analysis
```bash
# Analyze collected probe data (past 14 days, local only - default)
python3 probe_analyzer.py

# Analyze past 7 days only
python3 probe_analyzer.py --days 7

# Analyze ALL logs (may be slow for large datasets)
python3 probe_analyzer.py --all-logs

# Analyze WITH WiGLE API calls (consumes API credits!)
python3 probe_analyzer.py --wigle
```

### Surveillance Detection & Advanced Visualization
```bash
# 🆕 NEW: Automatic GPS extraction with spectacular KML visualization
python3 surveillance_analyzer.py

# Run analysis with demo GPS data (for testing - uses Phoenix coordinates)
python3 surveillance_analyzer.py --demo

# Analyze specific Kismet database
python3 surveillance_analyzer.py --kismet-db /path/to/kismet.db

# Focus on stalking detection with high persistence threshold
python3 surveillance_analyzer.py --stalking-only --min-persistence 0.8

# Export results to JSON for further analysis
python3 surveillance_analyzer.py --output-json analysis_results.json

# Analyze with external GPS data from JSON file
python3 surveillance_analyzer.py --gps-file gps_coordinates.json
```

### Ignore List Management
```bash
# Create new ignore lists from current Kismet data
python3 legacy/create_ignore_list.py  # Moved to legacy folder
```
**Note**: Ignore lists are now stored as JSON files in `./ignore_lists/`

## Core Components

- **chasing_your_tail.py**: Core monitoring engine with real-time Kismet database queries
- **cyt_gui.py**: Enhanced Tkinter GUI with surveillance analysis capabilities
- **cyt_tui.py**: Curses-based live monitoring interface for field/terminal use
- **surveillance_analyzer.py**: GPS surveillance detection with automatic coordinate extraction and advanced KML visualization
- **surveillance_detector.py**: Core persistence detection engine for suspicious device patterns
- **gps_tracker.py**: GPS tracking with location clustering and spectacular Google Earth KML generation
- **probe_analyzer.py**: Post-processing tool with WiGLE integration
- **start_kismet_clean.sh**: ONLY working Kismet startup script (July 23, 2025 fix)

### Security Components
- **secure_database.py**: SQL injection prevention
- **secure_credentials.py**: Encrypted credential management
- **secure_ignore_loader.py**: Safe ignore list loading
- **secure_main_logic.py**: Secure monitoring logic
- **input_validation.py**: Input sanitization and validation
- **migrate_credentials.py**: Credential migration tool

### Shared UI/Data Helpers
- **lib/gui_logic.py**: Shared dashboard stats, live-feed data, and latest-Kismet DB discovery

## Testing

Targeted tests now run cleanly from the repo root without manual path hacks.

```bash
cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG

pytest -q tests/test_secure_database.py tests/test_secure_time_windows.py tests/test_gui_logic.py
pytest -q tests/test_report_generator.py tests/test_surveillance_analyzer.py
pytest -q tests/test_tui_logic.py
```

Current targeted coverage includes:
- secure database queries
- time-window handling
- GUI dashboard/live-feed helpers
- report generation
- surveillance analyzer stalking logic
- TUI filtering, sorting, threat labeling, and alert counting

## Current UI/Data Architecture

- Both GUI and TUI resolve the latest Kismet database through shared helpers in `lib/gui_logic.py`
- Both GUI and TUI use the same live-feed normalization path from `SecureKismetDB.get_live_devices()`
- DB freshness is derived from Kismet DB file modification time and surfaced consistently in both interfaces
- `ui_settings.live_feed_window_seconds` controls the recent-device window for GUI and TUI live feeds

## Output Files & Project Structure

### Organized Output Directories
- **Surveillance Reports**: `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.md` (markdown)
- **HTML Reports**: `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.html` (styled HTML with pandoc)
- **KML Visualizations**: `./kml_files/surveillance_analysis_YYYYMMDD_HHMMSS.kml` (spectacular Google Earth files)
- **CYT Logs**: `./logs/cyt_log_MMDDYY_HHMMSS`
- **Analysis Logs**: `./analysis_logs/surveillance_analysis.log`
- **Probe Reports**: `./reports/probe_analysis_report_YYYYMMDD_HHMMSS.txt`

### Configuration & Data
- **Ignore Lists**: `./ignore_lists/mac_list.json`, `./ignore_lists/ssid_list.json`
- **Encrypted Credentials**: `./secure_credentials/encrypted_credentials.json`

### Archive Directories (Cleaned July 23, 2025)
- **old_scripts/**: All broken startup scripts with hanging pkill commands
- **docs_archive/**: Session notes, old configs, backup files, duplicate logs
- **legacy/**: Original legacy code archive (pre-security hardening)

## Technical Architecture

### Time Window System
Maintains four overlapping time windows to detect device persistence:
- Recent: Past 5 minutes
- Medium: 5-10 minutes ago
- Old: 10-15 minutes ago
- Oldest: 15-20 minutes ago

### Surveillance Detection
Advanced persistence detection algorithms analyze device behavior patterns:
- **Temporal Persistence**: Consistent device appearances over time
- **Location Correlation**: Devices following across multiple locations
- **Probe Pattern Analysis**: Suspicious SSID probe requests
- **Timing Analysis**: Unusual appearance patterns
- **Persistence Scoring**: Weighted scores (0-1.0) based on combined indicators
- **Multi-location Tracking**: Specialized algorithms for detecting following behavior

### GPS Integration & Spectacular KML Visualization (Enhanced!)
- **🆕 Automatic GPS extraction** from Kismet database (Bluetooth GPS support)
- **Location clustering** with 100m threshold for grouping nearby coordinates
- **Session management** with timeout handling for location transitions
- **Device-to-location correlation** links Wi-Fi devices to GPS positions
- **Professional KML generation** with spectacular Google Earth visualizations featuring:
  - Color-coded persistence level markers (green/yellow/red)
  - Device tracking paths showing movement correlation
  - Rich interactive balloon content with detailed device intelligence
  - Activity heatmaps and surveillance intensity zones
  - Temporal analysis overlays for time-based pattern detection
- **Multi-location tracking** detects devices following across locations with visual tracking paths

## Configuration

All settings are centralized in `config.json`:
```json
{
  "kismet_db_path": "/path/to/kismet/*.kismet",
  "log_directory": "./logs/",
  "ignore_lists_directory": "./ignore_lists/",
  "time_windows": {
    "recent": 5,
    "medium": 10,
    "old": 15,
    "oldest": 20
  }
}
```

WiGLE API credentials are now securely encrypted in `secure_credentials/encrypted_credentials.json`.

## Security Features

- **Parameterized SQL queries** prevent injection attacks
- **Encrypted credential storage** protects API keys
- **Input validation** prevents malicious input
- **Audit logging** tracks all security events
- **Safe ignore list loading** eliminates code execution risks

## Author

@matt0177

## License

MIT License

## Disclaimer

This tool is intended for legitimate security research, network administration, and personal safety purposes. Users are responsible for complying with all applicable laws and regulations in their jurisdiction.
---

## Personal Development Fork

This repository is a personal fork used for learning and development purposes. V2.0 features, including device aliasing and a persistent watchlist, are being implemented here.
