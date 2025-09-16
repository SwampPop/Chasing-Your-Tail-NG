# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chasing Your Tail (CYT) is a wireless device analyzer that monitors and tracks devices by analyzing Kismet logs. The system integrates with GPS data for location correlation and generates advanced reports and KML visualizations to identify potential surveillance patterns.

## Core Architecture

### Main Components
- **`cyt_gui.py`**: The main Kivy-based GUI for real-time monitoring and analysis.
- **`chasing_your_tail.py`**: The core command-line monitoring engine that continuously queries Kismet databases.
- **`surveillance_analyzer.py`**: The main orchestration script for performing deep analysis, correlating GPS data, and generating reports.
- **`surveillance_detector.py`**: The core detection engine containing the algorithms for identifying suspicious device patterns and calculating persistence scores.
- **`report_generator.py`**: A dedicated module for creating detailed, professional-grade Markdown and HTML reports from analysis results.
- **`gps_tracker.py`**: Handles GPS data, location clustering, session management, and KML visualization export.
- **`secure_*.py` modules**: A suite of modules providing security features like SQL injection prevention, encrypted credential storage, and safe data loading.

### Data Flow
1. Kismet captures wireless frames and stores data in SQLite databases.
2. The main monitoring script (`chasing_your_tail.py` or `cyt_gui.py`) queries the latest database for new devices.
3. The system analyzes device appearances over time and across locations to identify persistent or following behavior.
4. The `surveillance_analyzer.py` script can be run to perform a deep analysis, correlating device data with GPS tracks and generating detailed reports and KML files.

### Configuration System
All paths, API keys, and tuning parameters are centralized in `config.json`:
- Kismet database path pattern.
- Log and ignore list directories.
- Time window configurations.
- Geographic search boundaries.
- GPS tracker settings (location clustering, session timeouts).

## Common Development Commands

### Security Setup (REQUIRED FIRST TIME)
```bash
# Install dependencies
pip3 install -r requirements.txt

# Migrate credentials from an insecure config.json (if present)
# This will prompt for a master password to create the encrypted store
python3 secure_credentials.py # (Assuming a main block is added for migration)

Running the System
# Start the Kivy GUI for real-time monitoring
python3 cyt_gui.py

# Run the core command-line monitoring engine
python3 chasing_your_tail.py

# Perform a deep analysis on recent Kismet logs and generate reports/KML
python3 surveillance_analyzer.py

# Run a demo analysis using simulated GPS data
python3 surveillance_analyzer.py --demo

# Start Kismet using the robust startup script
sudo ./start_kismet_clean.sh wlan0mon

Kismet Startup

Kismet is managed by the robust start_kismet_clean.sh script.
# Manual startup for interface wlan0mon
sudo ./start_kismet_clean.sh wlan0mon

# Check if running
pgrep kismet

# Kill if needed (use direct kill, not pkill)
for pid in $(pgrep kismet); do sudo kill -9 $pid; done

Auto-start Setup:

Kismet: Can be started automatically on boot via root crontab using start_kismet_clean.sh.

GUI: Can be started automatically after boot via user crontab using start_gui.sh.

Note: The startup scripts are now portable and robust, removing the need for process cleanup commands (pkill).

Ignore List Management
# Create new, safe ignore lists from the latest Kismet data
python3 create_ignore_list.py

Note: This script generates simple .txt files, which are loaded securely.

Project Structure & Key File Locations

Core Files

Python Scripts: cyt_gui.py, chasing_your_tail.py, surveillance_analyzer.py, surveillance_detector.py, report_generator.py, gps_tracker.py, create_ignore_list.py

Security Modules: secure_database.py, secure_credentials.py, secure_ignore_loader.py, input_validation.py

Configuration: config.json, requirements.txt, template.kml

Startup Scripts: start_kismet_clean.sh, start_gui.sh

Data Layer: lib/watchlist_manager.py

Output Directories

Surveillance Reports: ./surveillance_reports/

KML Visualizations: ./kml_files/

Logs: ./logs/

Configuration & Data

Ignore Lists: ./ignore_lists/mac_list.txt and ./ignore_lists/ssid_list.txt

Watchlist Database: ./watchlist.db

Encrypted Credentials: ./secure_credentials/

Technical Details
Ignore List Format (SECURE)

Format: Ignore lists are stored as plain text files (.txt) with one MAC address or SSID per line. This is a simple, secure, and portable format.

Example (mac_list.txt):

AA:BB:CC:DD:EE:FF
11:22:33:44:55:66
Loading: The dangerous exec() command has been eliminated. Lists are loaded safely by secure_ignore_loader.py, which parses the text files as plain data.

Database Interaction

All interactions with the Kismet SQLite database are routed through the secure_database.py module.

This module enforces parameterized queries to prevent SQL injection and uses read-only connections for safety.

WiGLE Integration

The probe_analyzer.py script can query the WiGLE API for SSID location data.

API credentials are not stored in config.json. They are managed by secure_credentials.py, which encrypts them using a master password.

Surveillance Detection System

Advanced persistence detection algorithms analyze device behavior patterns:

Temporal Persistence: Detects devices appearing consistently over time.

Location Correlation: Identifies devices following across multiple locations.

Persistence Scoring: Assigns weighted scores (0-1.0) based on combined indicators.

GPS Integration & KML Visualization

Location Clustering: Groups nearby GPS coordinates (configurable via config.json).

Session Management: Tracks location sessions with timeouts (configurable via config.json).

Professional KML Generation: The report_generator.py and gps_tracker.py modules work together to create spectacular Google Earth files from a template.kml file.

Security Hardening
SQL Injection: Prevented by enforcing parameterized queries in secure_database.py.

Remote Code Execution: Eliminated dangerous exec() calls for ignore list loading.

Credential Exposure: API keys are moved from config.json to an encrypted store managed by secure_credentials.py.

Input Validation: Handled by a dedicated input_validation.py module.

***

### Summary of Key Changes

* **Ignore List System**: The documentation now accurately describes the secure `.txt` file format and the removal of the dangerous `exec()` command.
* **Configuration**: Added the new `gps_settings` to the overview and ensured all file paths are consistent with our refactored code.
* **Startup Scripts**: Descriptions are updated to reflect their new, robust, and portable nature.
* **Clarity and Consistency**: The entire document has been reviewed to ensure the descriptions of components match the improved, secure code we have developed.