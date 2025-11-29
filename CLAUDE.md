# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chasing Your Tail (CYT) is a wireless device analyzer that monitors and tracks devices by analyzing Kismet logs. The system integrates with GPS data for location correlation and generates advanced reports and KML visualizations to identify potential surveillance patterns.

## Core Architecture

### Main Components
- **`cyt_gui.py`**: Kivy-based GUI for real-time monitoring with surveillance analysis capabilities
- **`chasing_your_tail.py`**: Core command-line monitoring engine that continuously queries Kismet databases
- **`surveillance_analyzer.py`**: Main orchestration script for deep analysis, GPS correlation, and report generation
- **`surveillance_detector.py`**: Core detection engine with algorithms for identifying suspicious device patterns and persistence scoring
- **`report_generator.py`**: Dedicated module for creating detailed Markdown and HTML reports
- **`gps_tracker.py`**: GPS data handling, location clustering, session management, and KML visualization export
- **`probe_analyzer.py`**: Post-processing tool with WiGLE API integration for SSID geolocation
- **`secure_*.py` modules**: Security layer providing SQL injection prevention, encrypted credential storage, and safe data loading

### Security Architecture (Critical)
All database operations **must** use the secure modules:
- **`secure_database.py`**: Parameterized queries, read-only connections, context managers
- **`secure_credentials.py`**: PBKDF2-based encryption for API keys with master password
- **`secure_main_logic.py`**: Secure monitoring logic with proper exception handling
- **`input_validation.py`**: Input sanitization and validation

**Never** bypass these security layers - all Kismet database access goes through `SecureKismetDB`.

### Data Flow
1. Kismet captures wireless frames → SQLite databases (`.kismet` files)
2. Monitoring scripts query databases via `SecureKismetDB` context manager
3. Device appearances tracked across time windows (5/10/15/20 minutes)
4. Surveillance detection analyzes persistence patterns across time and locations
5. Reports and KML visualizations generated with GPS correlation

### Type System & Constants
The codebase uses centralized enums and constants from `cyt_constants.py`:
- **`DeviceType`**: WI_FI_CLIENT, WI_FI_AP, UAV, DRONE, BLUETOOTH, UNKNOWN
- **`AlertType`**: DRONE, WATCHLIST, CONFIRMED_THREAT, STATUS_MONITORING
- **`PersistenceLevel`**: CRITICAL (0.8+), HIGH (0.6+), MEDIUM (0.4+), LOW (0.0+)
- **`SystemConstants`**: All magic numbers (Earth radius, PBKDF2 iterations, timeouts, file permissions)

**Always use these enums** instead of string literals to prevent typos and enable type safety.

### Configuration System
All tunable parameters are in `config.json`:
- `detection_thresholds`: min_appearances, persistence scores, time spans
- `gps_settings`: location_threshold_meters (100m), session_timeout_seconds (600s)
- `ui_settings`: animation_duration, archive_interval
- `report_settings`: detection_accuracy, pandoc_timeout
- `timing.time_windows`: recent (5m), medium (10m), old (15m), oldest (20m)

**Never hardcode thresholds** - make them configurable via config.json.

### Database Architecture
Two centralized database schemas in `lib/database_utils.py`:
- **`HISTORY_SCHEMA`** (`cyt_history.db`): Device appearances archive with timestamps and locations
- **`WATCHLIST_SCHEMA`** (`watchlist.db`): Persistent watchlist with aliases and notes

Both use `DatabaseSchema` class with automatic initialization and the `safe_db_connection` context manager.

## Common Development Commands

### Setup & Installation
```bash
# Install dependencies (includes cryptography for secure credentials)
pip3 install -r requirements.txt

# Or with system override on macOS
pip3 install --break-system-packages -r requirements.txt
```

### Running the System
```bash
# Start Kismet (REQUIRED for live monitoring)
sudo ./start_kismet_clean.sh wlan0mon

# GUI interface with surveillance analysis button
python3 cyt_gui.py

# Command-line monitoring
python3 chasing_your_tail.py

# Deep surveillance analysis with GPS correlation and KML export
python3 surveillance_analyzer.py

# Demo mode with simulated GPS data (Phoenix coordinates)
python3 surveillance_analyzer.py --demo
```

### Drone Detection
```bash
# Analyze Kismet database for drone MAC addresses (DJI, Parrot, Autel, Skydio)
python3 probe_analyzer.py

# With WiGLE API integration (requires encrypted API key)
python3 probe_analyzer.py --wigle
```

### Testing
```bash
# Run comprehensive integration tests (21 tests)
python3 test_integration.py

# Expected output: 100% success rate, all 21 tests passing
```

### Credential Management
```bash
# Credentials are encrypted in ./secure_credentials/encrypted_credentials.json
# Managed via master password (prompted or CYT_MASTER_PASSWORD env var)
# WiGLE API token stored securely, never in config.json
```

### Ignore List Management
```bash
# Generate new ignore lists from Kismet data
python3 create_ignore_list.py

# Format: Plain .txt files (mac_list.txt, ssid_list.txt)
# One MAC/SSID per line - no dangerous exec() calls
```

## Key Technical Details

### Resource Management (Critical Bug Fix - Nov 2025)
**Always use context managers** for database connections:
```python
# CORRECT - uses context manager
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    # ... operations ...

# WRONG - resource leak
conn = sqlite3.connect(db_path)
# ... operations ...
conn.close()  # May not execute if exception occurs
```

### Thread Safety (Critical Bug Fix - Nov 2025)
Shared data structures between threads **must** use locks:
```python
# CORRECT - thread-safe queue access
with self.appearance_archive_lock:
    self.appearance_archive_queue.append(item)

# WRONG - race condition
self.appearance_archive_queue.append(item)  # Unsafe from multiple threads
```

### Exception Handling (Refactored Nov 2025)
Use **specific exception types**, never bare `except`:
```python
# CORRECT - specific exceptions
except sqlite3.Error as e:
    logger.error(f"Database error: {e}")
except (IOError, OSError) as e:
    logger.error(f"File system error: {e}")

# WRONG - masks bugs
except Exception as e:
    pass
```

### Type Hints (Added Nov 2025)
All new code should include comprehensive type hints:
```python
from typing import List, Dict, Optional, Any

def process_devices(macs: List[str], config: Dict[str, Any]) -> Optional[str]:
    """Process device list and return location ID or None."""
    ...
```

### Surveillance Detection Algorithm
Persistence score calculation combines:
- **Temporal persistence**: Consistency of appearances over time windows
- **Location correlation**: Following behavior across multiple GPS locations
- **Probe pattern analysis**: Suspicious SSID probe requests
- **Multi-location tracking**: Devices appearing at 2+ locations with user

Thresholds (configurable in `config.json`):
- `min_appearances`: Default 3
- `min_locations`: Default 2
- `persistence_score_critical`: Default 0.8
- `persistence_score_high`: Default 0.6

### GPS Integration & KML Visualization
- **Location clustering**: Groups GPS coordinates within 100m (configurable)
- **Session management**: Location sessions with 600s timeout (configurable)
- **Automatic GPS extraction**: From Kismet database (Bluetooth GPS support)
- **KML generation**: Uses `template.kml` for professional Google Earth visualizations
  - Color-coded markers (green/yellow/red by persistence level)
  - Device tracking paths
  - Interactive balloon content
  - Temporal analysis overlays

### WiGLE API Integration
- API token stored encrypted via `secure_credentials.py`
- Query timeout: 10 seconds (`SystemConstants.WIGLE_API_TIMEOUT_SECONDS`)
- Specific exception handling for timeouts, connection errors, invalid responses
- Local-only mode available (`--local` flag)

## Project Structure

### Core Python Scripts
- `cyt_gui.py` - GUI with real-time monitoring
- `chasing_your_tail.py` - CLI monitoring engine
- `surveillance_analyzer.py` - Deep analysis orchestrator
- `surveillance_detector.py` - Detection algorithms
- `report_generator.py` - Report generation (MD/HTML)
- `gps_tracker.py` - GPS and KML handling
- `probe_analyzer.py` - Drone detection and WiGLE

### Security Modules
- `secure_database.py` - SQL injection prevention
- `secure_credentials.py` - Encrypted credential management
- `secure_main_logic.py` - Secure monitoring logic
- `input_validation.py` - Input sanitization

### Shared Libraries (`lib/`)
- `database_utils.py` - Centralized database schemas and context managers
- `history_manager.py` - Device appearance archiving
- `watchlist_manager.py` - Persistent watchlist management
- `gui_logic.py` - GUI helper functions

### Constants & Configuration
- `cyt_constants.py` - Type-safe enums and system constants
- `config.json` - All tunable parameters (detection, GPS, UI, reports)
- `template.kml` - KML template for Google Earth visualization

### Output Directories
- `./surveillance_reports/` - Markdown and HTML reports
- `./kml_files/` - Google Earth KML visualizations
- `./logs/` - System logs
- `./ignore_lists/` - MAC and SSID ignore lists (plain .txt)
- `./secure_credentials/` - Encrypted API keys

### Testing
- `test_integration.py` - 21 comprehensive integration tests (100% pass rate)
- `tests/` - Additional test modules

### Startup Scripts
- `start_kismet_clean.sh` - Robust Kismet startup (ONLY working script)
- `start_gui.sh` - GUI auto-start for cron

## Important Code Patterns

### Adding New Detection Thresholds
1. Add to `config.json` under appropriate section
2. Load in detector: `config.get('detection_thresholds', {}).get('new_threshold', default_value)`
3. Document in README.md
4. Add test case in `test_integration.py`

### Adding New Device Types
1. Add to `DeviceType` enum in `cyt_constants.py`
2. Update detection logic in `surveillance_detector.py`
3. Add visualization support in `report_generator.py`
4. Update tests

### Working with Kismet Database
```python
from secure_database import SecureKismetDB

# Always use context manager
with SecureKismetDB(db_path) as db:
    devices = db.get_devices_by_time_range(start_time, end_time)
    # Process devices...
```

### Credential Management
```python
from secure_credentials import secure_config_loader

# Load config and credentials together
config, credential_manager = secure_config_loader('config.json')

# Get encrypted API token
wigle_token = credential_manager.get_wigle_token()
```

### Logging Best Practices
```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.error(f"Critical error: {e}")  # Errors requiring attention
logger.warning(f"Potential issue: {e}")  # Warnings
logger.info(f"Status update: {msg}")  # Information
logger.debug(f"Debug data: {data}")  # Debugging
```

## Recent Major Changes (November 2025)

### Comprehensive Bug Fixes & Refactoring
See `BUGFIX_REFACTOR_v2.2.md` for full details:
- Fixed 5 critical syntax errors preventing code execution
- Fixed resource leak in `probe_analyzer.py` (database connections)
- Fixed race condition in `cyt_gui.py` (thread-unsafe queue)
- Replaced 18+ broad exception handlers with specific types
- Completed stub implementations in `report_generator.py`
- Created `cyt_constants.py` for type-safe enums
- Created `lib/database_utils.py` to eliminate code duplication
- Made all detection thresholds configurable via `config.json`
- Added comprehensive type hints throughout codebase
- 100% integration test pass rate (21/21 tests)

### Architecture Improvements
- Centralized constants and enums for type safety
- DRY principle applied to database schemas
- All magic numbers documented in `SystemConstants`
- Thread-safe queue operations with proper locking
- Resource management with context managers
- Configuration-driven thresholds (no hardcoded values)

## Security Hardening

### SQL Injection Prevention
- All queries use parameterized statements via `SecureKismetDB`
- Read-only database connections enforced
- Input validation on all user-provided data

### Credential Security
- PBKDF2 key derivation with 250,000 iterations
- Fernet encryption for API keys
- Master password-based encryption key
- File permissions: 0o600 (owner read/write only)

### Input Validation
- MAC address format validation
- SSID sanitization (max 50 characters)
- Path validation to prevent directory traversal
- JSON schema validation for configuration

### Eliminated Vulnerabilities
- Removed dangerous `exec()` calls for ignore list loading
- Replaced string SQL concatenation with parameterized queries
- Added proper exception handling with specific types
- Fixed resource leaks with context managers

## Troubleshooting

### Common Issues

**Kismet not starting**
- Use `./start_kismet_clean.sh wlan0mon` (ONLY working script)
- Check interface with `iwconfig`
- Kill existing processes: `for pid in $(pgrep kismet); do sudo kill -9 $pid; done`

**Credential errors**
- Set `CYT_MASTER_PASSWORD` environment variable
- Or let system prompt for password interactively
- For testing: `export CYT_TEST_MODE=true`

**Test failures**
- Ensure `cryptography` package installed
- Check Python version (3.11+ recommended)
- Run: `python3 -m py_compile <filename>` to check syntax

**Import errors**
- Add project root to PYTHONPATH: `export PYTHONPATH=$PYTHONPATH:/path/to/Chasing-Your-Tail-NG`
- Verify all dependencies: `pip3 install -r requirements.txt`

**Database locked errors**
- Kismet may have database open - wait for capture to complete
- Use read-only mode via `SecureKismetDB` (enforced by default)

## Development Workflow

1. **Read existing code** before making changes (use Read tool)
2. **Check for security implications** (SQL injection, credential exposure)
3. **Use type hints** for all new functions
4. **Use enums** from `cyt_constants.py` instead of string literals
5. **Make thresholds configurable** via `config.json`
6. **Add specific exception handling** (never bare `except`)
7. **Use context managers** for resources (databases, files)
8. **Test thoroughly** - add integration test cases
9. **Document changes** in commit messages and BUGFIX reports
10. **Run integration tests** before committing: `python3 test_integration.py`

## Additional Resources

- **README.md**: User-facing documentation with usage examples
- **BUGFIX_REFACTOR_v2.2.md**: Detailed bug fix documentation (Nov 2025)
- **config.json**: All configurable parameters with defaults
- **requirements.txt**: Python dependencies
