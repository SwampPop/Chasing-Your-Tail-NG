# Project Context - Chasing Your Tail - Next Generation (CYT-NG)

**Last Updated**: 2025-12-01 17:50
**Project Type**: IT/Hardware
**Primary Language/Tool**: Python 3.9+

---

## Project Overview

### Purpose
Chasing Your Tail (CYT) is an advanced wireless surveillance detection system that monitors and tracks wireless devices by analyzing Kismet packet capture logs. The system employs multi-layer threat detection (OUI matching, behavioral analysis, persistence scoring) combined with GPS correlation to identify potential surveillance activities, with a particular focus on drone detection.

### Current Goals
1. ✅ **Complete** - Implement Kismet health monitoring with auto-restart capability
2. ✅ **Complete** - Implement advanced behavioral drone detection (9-pattern analysis)
3. ✅ **Complete** - Create unified daemon orchestration system
4. ✅ **Complete** - Create comprehensive deployment documentation
5. ⏸️ **Pending** - Deploy to hardware and perform systematic testing
6. ⏸️ **Pending** - Tune behavioral detection thresholds based on real-world data

### Success Criteria
- ✅ All three priority improvements implemented and tested (dev environment)
- ✅ Comprehensive documentation created for deployment
- ⏸️ System runs continuously for 7 days without intervention (hardware pending)
- ⏸️ Behavioral detection achieves <10% false positive rate (hardware pending)
- ⏸️ Health monitoring successfully recovers from Kismet crashes (hardware pending)

---

## Current Workflow Phase

**Current Status**: **Development Complete - Awaiting Hardware Testing**

All Priority #1-3 improvements are implemented, tested in dev environment, and committed to GitHub. Comprehensive deployment documentation created. Next phase requires hardware (wireless adapter + Kismet) for full system testing.

**Phase Checklist**:
- [x] Initial setup and configuration
- [x] Core functionality implementation (Priorities #1-3)
- [x] Development environment testing
- [x] Documentation (deployment guides + architecture diagrams)
- [ ] Hardware deployment (waiting on equipment)
- [ ] Full system testing (15 test scenarios)
- [ ] Threshold tuning (based on real-world data)
- [ ] Production deployment sign-off

---

## Key Decisions & Technical Context

### Architecture & Design (IT/Hardware)

**Multi-Layer Threat Detection System**:
CYT employs three complementary detection layers that work together:

1. **Layer 1: OUI Matching** (Instant Detection)
   - Manufacturer lookup via MAC prefix database
   - Detects known drones: DJI, Parrot, 3DR, Autel, etc.
   - **Alert**: Immediate RED alert on match
   - **Use Case**: Known commercial drones

2. **Layer 2: Behavioral Analysis** (Pattern Detection - NEW)
   - 9 weighted behavioral patterns analyzed
   - Requires minimum 3 device appearances
   - Confidence scoring: 0.0-1.0 scale
   - **Alert**: YELLOW alert at 60%+ confidence (configurable)
   - **Use Case**: Custom drones, unknown manufacturers, randomized MACs

3. **Layer 3: Persistence Scoring** (Time-Based Tracking)
   - Four time windows: 5, 10, 15, 20 minutes
   - Weighted persistence calculation
   - Identifies surveillance patterns
   - **Alert**: RED/YELLOW based on score thresholds
   - **Use Case**: Devices following/stalking patterns

**9 Behavioral Patterns** (with weights):
1. High Mobility (>15 m/s) - 15%
2. Signal Variance (>20 dBm) - 10%
3. Hovering (<50m radius) - 12%
4. Brief Appearance (<5 min) - 8%
5. No Association (never joins network) - 15%
6. High Signal Strength (>-50 dBm) - 10%
7. Probe Frequency (>10/min) - 10%
8. Channel Hopping (>2 channels) - 10%
9. No Clients (isolated device) - 10%

**Health Monitoring System** (NEW):
Three-layer health checking for Kismet:
- **Process Layer**: pgrep verification
- **Database Layer**: File existence + SQLite readability
- **Data Layer**: Timestamp freshness (<5 min threshold)

Auto-restart capability:
- Configurable via `config.json` (`auto_restart: true/false`)
- Max 3 restart attempts (prevents loops)
- Comprehensive logging of all restart events
- Integration with AlertManager for notifications

**Daemon Orchestration** (NEW):
Unified process management system:
- **Managed Processes**: Kismet (required), CYT Monitor (required), API Server (optional)
- **PID Tracking**: ./run/[process].pid files
- **Startup Order**: Dependency-aware (Kismet → Monitor → API)
- **Shutdown**: Graceful (SIGTERM) with fallback (SIGKILL)
- **Commands**: start, stop, restart, status

### Environment & Dependencies

**Language/Runtime**: Python 3.9+
**Key Libraries**:
- Standard library only (no external dependencies for core system)
- `subprocess` - Process management
- `sqlite3` - Kismet database queries
- `time`, `datetime` - Timing and timestamps
- `math` - Haversine distance calculations
- `dataclasses` - Structured data (DeviceHistory)
- `typing` - Type hints for code clarity
- `json` - Configuration management
- `cryptography` (external) - Encrypted credential storage
- `requests` (external) - WiGLE API integration
- `flask` (external) - API server
- `kivy` (external) - GUI interface

**Hardware**:
- **Required**: Wireless adapter supporting monitor mode
- **Recommended**: Alfa AWUS036ACH (dual-band, $40-50)
- **Budget**: TP-Link TL-WN722N v1 (2.4GHz only, $15-20)
- **Professional**: Alfa AWUS1900 (long-range, $80-100)
- **Platform**: Raspberry Pi 4 4GB (recommended, $55) or existing laptop
- **Optional**: GPS module (GlobalSat BU-353-S4, $30-40)

**External Services**:
- **Kismet** (required) - Wireless packet capture and database
- **WiGLE API** (optional) - SSID geolocation lookup
- **Telegram** (optional) - Alert delivery via AlertManager

**Operating System**:
- Ubuntu 20.04+ LTS (recommended)
- Raspberry Pi OS (for Raspberry Pi deployments)
- Kali Linux (alternative, pre-configured for wireless)
- Any Debian-based Linux with kernel 4.x+

### Known Issues & Blockers

**No Active Blockers** - All development work complete.

**Pending Items** (Not blockers):
1. **Hardware Testing**: Full system testing requires:
   - Wireless adapter in monitor mode (not available in dev environment)
   - Kismet installation and running
   - Real wireless devices for detection testing
   - GPS module for location correlation (optional)

2. **Threshold Tuning**: Default behavioral detection thresholds may need adjustment:
   - Confidence threshold (current: 60%)
   - Movement speed threshold (current: 15 m/s)
   - Hovering radius (current: 50 meters)
   - Signal variance threshold (current: 20 dBm)
   - Adjust based on real-world false positive/negative rates

3. **Health Monitor**: Auto-restart currently disabled by default
   - Config: `auto_restart: false` (conservative approach)
   - Enable after testing in target environment
   - Verify restart logic works correctly

---

## Session History

### Session 2025-12-01 (Session 3 - Continued from Context Overflow)
- **Focus**: Complete Priorities #1-3, create comprehensive deployment documentation
- **Accomplishments**:
  - ✅ Implemented Kismet health monitoring system (442 lines)
  - ✅ Implemented behavioral drone detection (615 lines, 9 patterns)
  - ✅ Created unified CYT daemon orchestration (600+ lines)
  - ✅ Created 5 comprehensive deployment guides (~3,600 lines)
  - ✅ Tested behavioral detector: 75.1% confidence on simulated drone
  - ✅ All code committed to GitHub (5 commits)
- **Key Changes**:
  - Created: `kismet_health_monitor.py`, `behavioral_drone_detector.py`, `cyt_daemon.py`
  - Modified: `chasing_your_tail.py`, `secure_main_logic.py`, `config.json`, `config_validator.py`
  - Documentation: HEALTH_MONITORING.md, BEHAVIORAL_DRONE_DETECTION.md, DAEMON.md, QUICK_START.md, HARDWARE_REQUIREMENTS.md, TESTING_GUIDE.md, DEPLOYMENT_CHECKLIST.md, SYSTEM_DIAGRAM.md
- **Next Steps**:
  1. Wait for hardware availability
  2. Deploy using QUICK_START.md (30-minute guide)
  3. Execute TESTING_GUIDE.md systematically (15 test scenarios)
  4. Tune behavioral detection thresholds based on results

### Session 2025-11-30 (Session 2 - Meta-System Configuration)
- **Focus**: Implement session management hooks (automatic context loading)
- **Accomplishments**:
  - Created SessionStart hook (automatic context loading at session start)
  - Created SessionEnd hook (mechanical tasks + reminder)
  - Configured ~/.claude/settings.json with hook system
  - Chose "Hybrid Approach Option C" (auto + manual)
- **Key Changes**: Session management system now production-ready
- **Next Steps**: Restart Claude Code to activate hooks, continue with homelab/CYT work

### Session 2025-11-30 (Session 1 - Session Management Design)
- **Focus**: Design comprehensive session management system
- **Accomplishments**:
  - Designed three-component session workflow (input/processing/output)
  - Created /session-close command for intelligent session logging
  - Documented session management philosophy ("Future Self Documentation")
- **Key Changes**: Established meta-system for zero context loss
- **Next Steps**: Implement hooks (completed in Session 2)

---

## Working Instructions

### Current Focus
**Wait for hardware availability, then deploy and test systematically.**

The development work is complete. All three priority improvements are implemented, tested (dev environment), and committed to GitHub. Comprehensive deployment documentation has been created. The next phase requires hardware to perform full system testing.

### Immediate Next Actions

**When hardware arrives**:
1. **Read QUICK_START.md** - 30-minute deployment guide with step-by-step instructions
2. **Deploy System** - Follow installation procedures (should take ~30 minutes)
3. **Execute Testing** - Use TESTING_GUIDE.md (15 test scenarios with pass/fail criteria)
4. **Review Results** - Document test outcomes, identify issues
5. **Tune Thresholds** - Adjust behavioral detection parameters based on false positive/negative rates
6. **Production Deploy** - Use DEPLOYMENT_CHECKLIST.md for final production deployment

**Hardware Shopping** (if equipment not yet acquired):
1. **Read HARDWARE_REQUIREMENTS.md** - Complete shopping guide
2. **Choose Budget Tier**:
   - Budget ($50-80): TP-Link TL-WN722N v1 + Raspberry Pi Zero 2 W
   - Recommended ($120-180): Alfa AWUS036ACH + Raspberry Pi 4 4GB
   - Professional ($250-350): Alfa AWUS1900 + Raspberry Pi 4 8GB + PoE
3. **Order Equipment** - Specific models and links provided in guide
4. **Wait for Delivery** - Then proceed with deployment steps above

### Context for Next Session

**Critical Context**:
- All Priorities #1-3 complete and committed (commits: ba88c6e, 9efbe6f, c023ef9, a2c7855, ddbe9a4)
- Comprehensive documentation created (3,600 lines across 5 guides)
- No hardware testing yet - all code validated in dev environment only
- Behavioral detector test: 75.1% confidence achieved on simulated drone
- Health monitoring: Auto-restart disabled by default (conservative approach)
- Daemon orchestration: Ready for production use with systemd integration

**Design Decisions to Remember**:
1. Chose weighted confidence scoring (vs. binary yes/no) for behavioral detection
2. Chose multi-layer health checking (vs. simple process check)
3. Chose PID file tracking (vs. systemd-only) for daemon management
4. Chose comprehensive documentation (vs. minimal) - "Future Self Documentation" philosophy

**Token Consumption Decision**:
- User chose NOT to optimize session management overhead
- Rationale: Full context saves more tokens in long run
- Overhead: 8-14% of budget per session (acceptable)
- Matches comprehensive documentation style

**Next Session Will Need**:
- Hardware availability status
- Deployment timeline/schedule
- Any questions about deployment procedure
- Context will auto-load via SessionStart hook

---

## File Structure

```
Chasing-Your-Tail-NG/
├── Core Python Modules
│   ├── chasing_your_tail.py          # Main monitoring engine
│   ├── cyt_daemon.py                 # NEW: Unified process orchestration
│   ├── secure_main_logic.py          # Core detection logic (integrated behavioral)
│   ├── kismet_health_monitor.py      # NEW: Health monitoring system
│   ├── behavioral_drone_detector.py  # NEW: 9-pattern behavioral analysis
│   ├── surveillance_detector.py      # Persistence scoring system
│   ├── surveillance_analyzer.py      # Deep analysis orchestration
│   ├── report_generator.py           # Markdown/HTML report creation
│   ├── gps_tracker.py                # GPS correlation and KML generation
│   ├── alert_manager.py              # Telegram alerting
│   └── api_server.py                 # REST API interface
│
├── Security Modules
│   ├── secure_database.py            # Parameterized SQL, read-only connections
│   ├── secure_credentials.py         # Encrypted credential storage (Fernet)
│   ├── secure_ignore_loader.py       # Safe file loading (no exec())
│   └── input_validation.py           # Input sanitization
│
├── Configuration & Validation
│   ├── config.json                   # System configuration (NEW sections added)
│   ├── config_validator.py           # JSON schema validation (extended)
│   └── template.kml                  # KML template for Google Earth
│
├── Scripts & Services
│   ├── start_kismet_clean.sh         # Robust Kismet startup script
│   ├── test_health_monitor.sh        # NEW: Automated health monitor tests
│   └── cyt.service                   # NEW: Systemd service file
│
├── Documentation (NEW - Comprehensive)
│   ├── QUICK_START.md                # 30-minute deployment guide
│   ├── HARDWARE_REQUIREMENTS.md      # Hardware shopping guide
│   ├── TESTING_GUIDE.md              # 15 test scenarios
│   ├── DEPLOYMENT_CHECKLIST.md       # Production deployment checklist
│   ├── SYSTEM_DIAGRAM.md             # ASCII architecture diagrams
│   ├── HEALTH_MONITORING.md          # Health monitoring deep dive
│   ├── BEHAVIORAL_DRONE_DETECTION.md # Behavioral detection guide
│   ├── DAEMON.md                     # Daemon usage guide
│   ├── CLAUDE.md                     # Claude Code project instructions
│   └── README.md                     # Project overview
│
├── Output Directories
│   ├── logs/                         # All system logs
│   │   ├── cyt_monitor.log
│   │   ├── cyt_daemon.log
│   │   ├── kismet_health.log
│   │   └── surveillance_analysis.log
│   ├── run/                          # NEW: PID files for daemon
│   │   ├── kismet.pid
│   │   ├── cyt_monitor.pid
│   │   └── api_server.pid
│   ├── surveillance_reports/         # Generated Markdown/HTML reports
│   ├── kml_files/                    # Google Earth visualizations
│   └── ignore_lists/                 # Safe ignore lists (txt format)
│       ├── mac_list.txt
│       └── ssid_list.txt
│
├── Data Storage
│   ├── cyt_history.db                # Device history database
│   └── secure_credentials/           # Encrypted API keys
│       └── encrypted_credentials.json
│
└── Project Management (NEW)
    ├── PROJECT_CONTEXT.md            # This file (auto-syncs to GEMINI.md)
    └── todo.md                       # Task tracking
```

---

## Quick Reference

### Frequent Commands

```bash
# Unified daemon control (NEW - preferred method)
sudo python3 cyt_daemon.py start      # Start all components
sudo python3 cyt_daemon.py stop       # Stop all components
sudo python3 cyt_daemon.py restart    # Restart all components
sudo python3 cyt_daemon.py status     # Check status

# Systemd service (for production deployment)
sudo systemctl start cyt              # Start service
sudo systemctl stop cyt               # Stop service
sudo systemctl status cyt             # Check status
sudo journalctl -u cyt -f             # Follow logs

# Manual component startup (legacy/debugging)
sudo ./start_kismet_clean.sh wlan0mon # Start Kismet
python3 chasing_your_tail.py          # Start CYT Monitor
python3 api_server.py                 # Start API Server

# Testing & Validation
python3 config_validator.py           # Validate configuration
python3 behavioral_drone_detector.py  # Standalone behavioral test
./test_health_monitor.sh              # Run health monitor tests

# Monitoring
tail -f logs/cyt_monitor.log          # Watch main log
tail -f logs/kismet_health.log        # Watch health checks
tail -f logs/cyt_daemon.log           # Watch daemon operations

# Wireless adapter setup
sudo airmon-ng start wlan0            # Enable monitor mode
iwconfig                              # Verify monitor mode active
```

### Important File Locations

**Configuration**:
- Main config: `./config.json`
- Credentials: `./secure_credentials/encrypted_credentials.json`
- Ignore lists: `./ignore_lists/*.txt`

**Data**:
- Kismet databases: `/tmp/kismet/*.kismet`
- Device history: `./cyt_history.db`
- Logs: `./logs/*.log`
- PID files: `./run/*.pid`

**Documentation**:
- Deployment: `./QUICK_START.md`
- Hardware: `./HARDWARE_REQUIREMENTS.md`
- Testing: `./TESTING_GUIDE.md`
- Architecture: `./SYSTEM_DIAGRAM.md`

### External Links

**Documentation**:
- Kismet: https://www.kismetwireless.net/docs/
- WiGLE API: https://api.wigle.net/
- Raspberry Pi: https://www.raspberrypi.org/documentation/

**Repository**:
- GitHub: https://github.com/SwampPop/Chasing-Your-Tail-NG
- Latest commit: ddbe9a4

**Hardware Resources**:
- Alfa adapters: https://www.rokland.com/
- Raspberry Pi official: https://www.raspberrypi.com/
- GPS modules: https://www.adafruit.com/

---

**Last Session**: 2025-12-01
**Confidence Level**: **Very High**
**Ready for Next Session**: **Yes** - All development complete, comprehensive documentation created, clear next steps defined (hardware deployment + testing)

---

## Deployment Readiness Checklist

**Development Phase** ✅:
- [x] Priority #1: Health Monitoring (complete)
- [x] Priority #2: Behavioral Detection (complete)
- [x] Priority #3: Unified Daemon (complete)
- [x] Documentation Sprint (complete)
- [x] Code committed to GitHub (complete)

**Hardware Phase** ⏸️:
- [ ] Acquire wireless adapter (see HARDWARE_REQUIREMENTS.md)
- [ ] Acquire computing platform (Raspberry Pi or laptop)
- [ ] Install operating system (Ubuntu/Raspberry Pi OS)
- [ ] Deploy system (follow QUICK_START.md)
- [ ] Execute testing (follow TESTING_GUIDE.md)
- [ ] Tune thresholds (based on real-world results)
- [ ] Production deployment (follow DEPLOYMENT_CHECKLIST.md)

**Production Phase** ⏸️:
- [ ] 24-hour soak test (verify stability)
- [ ] 7-day continuous operation (verify reliability)
- [ ] False positive analysis (tune behavioral thresholds)
- [ ] Health monitoring validation (verify auto-restart works)
- [ ] AlertManager integration (test Telegram notifications)
- [ ] Deployment sign-off (complete DEPLOYMENT_CHECKLIST.md)

---

**Next milestone**: Hardware acquisition and deployment
**Estimated timeline**: 30 minutes for deployment (with hardware ready)
**Estimated testing**: 2-4 hours for comprehensive testing (15 scenarios)
