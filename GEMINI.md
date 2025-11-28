# CYT Project Analysis (GEMINI.md)

## Project Overview

The "Chasing Your Tail" (CYT) project is a sophisticated Wi-Fi probe request analyzer designed for monitoring and tracking wireless devices, with a particular focus on detecting surveillance activities. It integrates with Kismet for raw packet capture and the WiGLE API for SSID geolocation analysis. The project emphasizes security hardening against common vulnerabilities.

**Key Features:**

*   **Real-time Wi-Fi Monitoring:** Integrates with Kismet for continuous data collection.
*   **Advanced Surveillance Detection:** Utilizes multi-location tracking algorithms, temporal persistence, and probe pattern analysis with persistence scoring.
*   **Automatic GPS Integration:** Extracts coordinates from Bluetooth GPS via Kismet, enabling location clustering and device-to-location correlation.
*   **Spectacular KML Visualization:** Generates professional Google Earth KML files with color-coded markers, tracking paths, interactive content, and activity heatmaps for advanced visualization of surveillance.
*   **Multi-format Reporting:** Produces reports in Markdown, HTML, and KML formats.
*   **Time-Window Tracking:** Analyzes device presence across multiple time windows (5, 10, 15, 20 minutes) for persistence detection.
*   **Enhanced GUI Interface:** Provides a user-friendly Kivy-based graphical interface (`cyt_gui.py`, `cyt.kv`) with surveillance analysis capabilities, device aliasing, and real-time status updates.
*   **Organized File Structure:** Employs dedicated output directories for logs, reports, and visualizations.
*   **Comprehensive Logging:** Features robust logging for monitoring sessions and analysis events.

**Security Hardening:**

A core focus of the project is security, implementing measures to mitigate vulnerabilities:

*   **SQL Injection Prevention:** All database interactions utilize parameterized queries (`secure_database.py`).
*   **Encrypted Credential Management:** API keys (e.g., WiGLE) are stored encrypted using `cryptography.fernet` and a master password, with a migration utility provided (`secure_credentials.py`, `migrate_credentials.py`).
*   **Input Validation and Sanitization:** Ensures safe handling of user and configuration inputs (`input_validation.py`).
*   **Secure Ignore List Loading:** Prevents code execution risks by safely loading ignore lists (`secure_ignore_loader.py`).
*   **Read-Only Database Connections:** Kismet database connections are explicitly read-only to prevent accidental or malicious modifications (`secure_database.py`).

**Technologies Used:**

*   **Python 3.6+:** The primary programming language.
*   **Kismet:** Wireless packet capture tool for data acquisition.
*   **WiGLE API:** Used for SSID geolocation.
*   **Kivy:** Python framework for developing the cross-platform GUI.
*   **sqlite3:** Used for interacting with Kismet databases.
*   **cryptography:** Python library for secure credential encryption.
*   **pandoc:** (Inferred) For multi-format report generation (Markdown to HTML).

**Technical Architecture Highlights:**

*   **Time Window System:** The `SecureCYTMonitor` (`secure_main_logic.py`) manages device and SSID tracking across four overlapping time windows to identify consistent presence.
*   **Secure Data Access:** `SecureKismetDB` (`secure_database.py`) acts as a secure wrapper for all Kismet database operations, enforcing read-only access and parameterized queries.
*   **Credential Manager:** `SecureCredentialManager` (`secure_credentials.py`) handles the encryption, storage, and retrieval of sensitive API keys.

**Output Files:**

*   **Surveillance Reports:** `./surveillance_reports/surveillance_report_YYYYMMDD_HHMMSS.md` (Markdown), `.html` (styled HTML).
*   **KML Visualizations:** `./kml_files/surveillance_analysis_YYYYMMDD_HHMMSS.kml` (Google Earth files).
*   **CYT Logs:** `./logs/cyt_log_MMDDYY_HHMMSS`.
*   **Analysis Logs:** `./analysis_logs/surveillance_analysis.log`.
*   **Probe Reports:** `./reports/probe_analysis_report_YYYYMMDD_HHMMSS.txt`.
*   **Configuration & Data:** `config.json`, `./ignore_lists/mac_list.json`, `./ignore_lists/ssid_list.json`, `./secure_credentials/encrypted_credentials.json`.

**Development Status:**

This is a personal development fork, with ongoing implementation of V2.0 features such as device aliasing and a persistent watchlist.

## Building and Running

### Requirements

*   Python 3.6+
*   Kismet wireless packet capture software
*   Wi-Fi adapter supporting monitor mode
*   Linux-based operating system
*   WiGLE API key (optional, but recommended for full functionality)

### Installation

1.  **Install Python Dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```
    (Dependencies include `Kivy`, `cryptography`, `requests`, etc.)

2.  **Security Setup (REQUIRED FIRST TIME):**
    Migrate any existing API keys from `config.json` to secure, encrypted storage.
    ```bash
    python3 migrate_credentials.py
    ```
    Verify secure mode:
    ```bash
    python3 chasing_your_tail.py
    # Expected output: "🔒 SECURE MODE: All SQL injection vulnerabilities have been eliminated!"
    ```
    *   *Important:* After migration, remove API keys from `config.json` and replace it with the sanitized version generated (e.g., `config_sanitized.json`).

3.  **Configure System:**
    Edit `config.json` to define paths (Kismet database pattern, log/ignore list directories), time window configurations, and optional geographic search boundaries.

### Usage

*   **GUI Interface:**
    ```bash
    python3 cyt_gui.py
    ```
    (Provides real-time status, follower lists, alerts, and access to surveillance analysis.)

*   **Command Line Monitoring (Core Engine):**
    ```bash
    python3 chasing_your_tail.py
    ```
    (Runs the secure monitoring loop in the terminal.)

*   **Kismet Startup:**
    ```bash
    ./start_kismet_clean.sh
    ```
    (Starts Kismet for packet capture. Note: this is identified as the "ONLY working script" as of July 2025.)

*   **Data Analysis (Post-processing):**
    ```bash
    python3 probe_analyzer.py [--days N] [--all-logs] [--wigle]
    ```
    (Analyzes collected probe data, with options for timeframes and WiGLE integration.)

*   **Surveillance Detection & Advanced Visualization:**
    ```bash
    python3 surveillance_analyzer.py [--demo] [--kismet-db /path/to/db] [--stalking-only] [--min-persistence VAL] [--output-json FILE] [--gps-file FILE]
    ```
    (Performs GPS surveillance detection and generates KML visualizations.)

## Development Conventions

*   **Security-First Approach:** Strong emphasis on preventing common vulnerabilities (SQLi, insecure credential storage).
*   **Modular Design:** Logic is separated into concerns (database, credentials, main logic, GUI).
*   **Configuration Management:** Centralized `config.json` for settings, with secure handling of sensitive data.
*   **Standard Python Practices:** Adheres to Python 3+, utilizes standard libraries, and employs logging.
*   **Version Control & Archiving:** Features `old_scripts/`, `docs_archive/`, and `legacy/` directories for managing older code and documentation, indicating a clean-up effort.
*   **Kivy for GUI:** Utilizes Kivy for its graphical interface, with UI defined in `.kv` files.
