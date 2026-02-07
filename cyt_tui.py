#!/usr/bin/env python3
"""
CYT Terminal UI (TUI)
Curses-based live monitoring display with two switchable views:
  [1] Live Feed  - Scrolling device table (MAC, signal, channel, type, manufacturer)
  [2] Dashboard  - System status overview (tracking buckets, recent alerts, health)

Usage:
    python3 cyt_tui.py

Keys:
    1 / 2 / Tab  - Switch views
    Up / Down    - Scroll device list
    q            - Quit
"""
import curses
import glob
import io
import json
import logging
import os
import pathlib
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# CYT imports
from config_validator import validate_config_file
from secure_credentials import secure_config_loader
from secure_database import SecureKismetDB
from secure_ignore_loader import load_ignore_lists
from secure_main_logic import SecureCYTMonitor
from lib import history_manager

# Optional CYT imports
try:
    from alert_manager import AlertManager
    ALERT_MANAGER_AVAILABLE = True
except ImportError:
    ALERT_MANAGER_AVAILABLE = False

try:
    from context_engine import ContextEngine
    CONTEXT_ENGINE_AVAILABLE = True
except ImportError:
    CONTEXT_ENGINE_AVAILABLE = False

try:
    from kismet_health_monitor import KismetHealthMonitor
    HEALTH_MONITOR_AVAILABLE = True
except ImportError:
    HEALTH_MONITOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# Minimum terminal size
MIN_COLS = 80
MIN_ROWS = 24

# Ring buffer size for captured output
MAX_LOG_LINES = 500
MAX_ALERT_LINES = 50


# ---------------------------------------------------------------------------
# TUIOutputCapture - sys.stdout replacement
# ---------------------------------------------------------------------------
class TUIOutputCapture(io.TextIOBase):
    """Replaces sys.stdout to capture print() calls into a ring buffer.

    Anything written to this object is stored line-by-line in `lines`.
    The original stdout is preserved for fallback and flush purposes.
    """

    def __init__(self, original_stdout, lines: deque):
        self._original = original_stdout
        self._lines = lines
        self._buf = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            stripped = self._strip_ansi(line)
            if stripped:
                self._lines.append(stripped)
        return len(s)

    def flush(self):
        if self._buf:
            stripped = self._strip_ansi(self._buf)
            if stripped:
                self._lines.append(stripped)
            self._buf = ""

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from text."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)

    def fileno(self):
        return self._original.fileno()

    @property
    def encoding(self):
        return self._original.encoding

    def isatty(self):
        return False


# ---------------------------------------------------------------------------
# TUIMonitor - SecureCYTMonitor subclass
# ---------------------------------------------------------------------------
class TUIMonitor(SecureCYTMonitor):
    """Overrides _log_to_console to route output to the TUI alert buffer
    instead of printing directly to stdout."""

    def __init__(self, config, ignore_list, ssid_ignore_list, log_file,
                 alert_buffer: deque, alert_manager=None):
        super().__init__(config, ignore_list, ssid_ignore_list, log_file,
                         alert_manager=alert_manager)
        self._alert_buffer = alert_buffer

    def _log_to_console(self, message: str) -> None:
        """Route to TUI alert buffer instead of print()."""
        # Strip ANSI for display
        clean = message
        for code in ("\033[91m", "\033[93m", "\033[92m", "\033[0m"):
            clean = clean.replace(code, "")

        # Determine alert level from original message
        ts = datetime.now().strftime('%H:%M:%S')
        if "\033[91m" in message:
            prefix = "CRIT"
        elif "\033[93m" in message:
            prefix = "WARN"
        else:
            prefix = "INFO"

        for line in clean.strip().split("\n"):
            line = line.strip()
            if line:
                self._alert_buffer.append(f"[{ts}] {prefix}: {line}")

        # Still write to log file
        if self.log_file:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_file.write(f"[{timestamp}] {clean}\n")
            self.log_file.flush()


# ---------------------------------------------------------------------------
# DeviceRow - flattened device for display
# ---------------------------------------------------------------------------
@dataclass
class DeviceRow:
    mac: str = ""
    signal: int = -100
    channel: str = ""
    dev_type: str = ""
    manufacturer: str = ""
    last_seen: str = ""
    threat: str = ""  # "drone", "behavioral", "persistent", ""


# ---------------------------------------------------------------------------
# CYTTerminalUI - main curses controller
# ---------------------------------------------------------------------------
class CYTTerminalUI:
    """Curses-based TUI for CYT monitoring."""

    def __init__(self):
        self.config: Optional[dict] = None
        self.credential_manager = None
        self.ignore_list: Set[str] = set()
        self.probe_ignore_list: Set[str] = set()
        self.latest_kismet_db: Optional[str] = None
        self.monitor: Optional[TUIMonitor] = None
        self.health_monitor = None
        self.alert_manager_instance = None
        self.context_engine = None
        self.log_file_handle = None
        self.log_file_path: Optional[pathlib.Path] = None

        # TUI state
        self.log_lines: deque = deque(maxlen=MAX_LOG_LINES)
        self.alert_lines: deque = deque(maxlen=MAX_ALERT_LINES)
        self.current_view = 1  # 1=Live Feed, 2=Dashboard
        self.scroll_offset = 0
        self.cycle_count = 0
        self.start_time = time.time()
        self.device_rows: List[DeviceRow] = []
        self.running = True

    # -------------------------------------------------------------------
    # Initialization (mirrors CYTMonitorApp.initialize)
    # -------------------------------------------------------------------
    def initialize(self) -> bool:
        """Load config and initialize all CYT components."""
        try:
            # Set up logging to file only (no StreamHandler - TUI owns the screen)
            log_dir = pathlib.Path('./logs')
            log_dir.mkdir(parents=True, exist_ok=True)
            filename = f'cyt_log_{time.strftime("%m%d%y_%H%M%S")}.log'
            self.log_file_path = log_dir / filename
            self.log_file_handle = open(self.log_file_path, "w", buffering=1)

            # Configure logging - file handler only, no stdout
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            # Remove any existing handlers
            for h in root_logger.handlers[:]:
                root_logger.removeHandler(h)
            fh = logging.FileHandler(self.log_file_path)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            root_logger.addHandler(fh)

            logging.info("--- CYT TUI Session Started ---")

            # Validate config
            logging.info("Validating configuration...")
            is_valid, error_msg, _ = validate_config_file('config.json')
            if not is_valid:
                logging.critical(f"Configuration validation failed: {error_msg}")
                return False

            logging.info("Loading configuration and credentials...")
            self.config, self.credential_manager = secure_config_loader('config.json')

            logging.info("Loading ignore lists...")
            self.ignore_list, self.probe_ignore_list = load_ignore_lists(self.config)
            logging.info(f"Loaded {len(self.ignore_list)} MACs, {len(self.probe_ignore_list)} SSIDs to ignore")

            # Find latest Kismet DB
            db_path_pattern = self.config['paths']['kismet_logs']
            if os.path.isdir(db_path_pattern):
                db_path_pattern = os.path.join(db_path_pattern, "*.kismet")

            list_of_files = glob.glob(db_path_pattern)
            if not list_of_files:
                if os.path.exists("test_capture.kismet"):
                    logging.warning("No live Kismet DB found. Using test_capture.kismet")
                    self.latest_kismet_db = "test_capture.kismet"
                else:
                    logging.critical(f"No Kismet database files found at: {db_path_pattern}")
                    return False
            else:
                self.latest_kismet_db = max(list_of_files, key=os.path.getctime)
            logging.info(f"Using Kismet database: {self.latest_kismet_db}")

            # AlertManager
            if ALERT_MANAGER_AVAILABLE:
                try:
                    self.alert_manager_instance = AlertManager()
                    logging.info("AlertManager initialized")
                except Exception as e:
                    logging.warning(f"Could not init AlertManager: {e}")

            # Create TUIMonitor (subclass of SecureCYTMonitor)
            self.monitor = TUIMonitor(
                self.config,
                self.ignore_list,
                self.probe_ignore_list,
                self.log_file_handle,
                self.alert_lines,
                alert_manager=self.alert_manager_instance
            )

            # History database
            try:
                history_manager.initialize_history_database()
                logging.info("History database initialized")
            except Exception as e:
                logging.warning(f"Could not initialize history database: {e}")

            # Health monitor
            health_config = self.config.get('kismet_health', {})
            if health_config.get('enabled', False) and HEALTH_MONITOR_AVAILABLE:
                try:
                    self.health_monitor = KismetHealthMonitor(
                        db_path_pattern=self.config['paths']['kismet_logs'],
                        startup_script=health_config.get('startup_script', './start_kismet_clean.sh'),
                        max_restart_attempts=health_config.get('max_restart_attempts', 3),
                        data_freshness_threshold_minutes=health_config.get('data_freshness_threshold_minutes', 5),
                        auto_restart=health_config.get('auto_restart', False)
                    )
                    logging.info("Kismet health monitor initialized")
                except Exception as e:
                    logging.error(f"Failed to init health monitor: {e}")

            # Context engine
            context_config = self.config.get('context_engine', {})
            if context_config.get('enabled', False) and CONTEXT_ENGINE_AVAILABLE:
                try:
                    self.context_engine = ContextEngine(
                        config=self.config,
                        db_path=context_config.get('database', 'context_data.db')
                    )
                    logging.info("Context Engine initialized")
                except Exception as e:
                    logging.error(f"Failed to init Context Engine: {e}")

            # Validate DB and initialize tracking lists
            logging.info("Validating database and initializing tracking lists...")
            with SecureKismetDB(self.latest_kismet_db) as db:
                if not db.validate_connection():
                    logging.critical("Database validation failed")
                    return False
                self.monitor.initialize_tracking_lists(db)

            logging.info("TUI initialization complete")
            return True

        except Exception as e:
            logging.critical(f"Fatal error during TUI init: {e}", exc_info=True)
            return False

    # -------------------------------------------------------------------
    # Main curses entry point
    # -------------------------------------------------------------------
    def run(self, stdscr) -> None:
        """Main curses loop called via curses.wrapper."""
        # Curses setup
        curses.curs_set(0)
        curses.use_default_colors()
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_RED, -1)      # drone
            curses.init_pair(2, curses.COLOR_YELLOW, -1)    # warning/persistent
            curses.init_pair(3, curses.COLOR_GREEN, -1)     # healthy/normal
            curses.init_pair(4, curses.COLOR_CYAN, -1)      # header highlight
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # status bar
            curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_CYAN)  # tab active
            curses.init_pair(7, curses.COLOR_WHITE, -1)     # tab inactive

        # Redirect stdout to capture stray print() calls
        original_stdout = sys.stdout
        sys.stdout = TUIOutputCapture(original_stdout, self.log_lines)

        check_interval = self.config.get('timing', {}).get('check_interval', 60)
        list_update_interval = self.config.get('timing', {}).get('list_update_interval', 5)
        health_check_interval = self.config.get('kismet_health', {}).get('check_interval_cycles', 5)
        kismet_interface = self.config.get('kismet_health', {}).get('interface', 'wlan0mon')
        context_check_interval = self.config.get('context_engine', {}).get('poll_interval_seconds', 30)
        context_cycles = max(1, context_check_interval // check_interval)

        try:
            while self.running:
                # --- Process one monitoring cycle ---
                self._process_cycle(list_update_interval, health_check_interval,
                                    kismet_interface, context_cycles)

                # --- Redraw screen ---
                self._draw(stdscr)

                # --- Wait for next cycle with keyboard polling ---
                self._poll_keyboard(stdscr, check_interval)

        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout = original_stdout
            logging.info("TUI session ended")
            if self.log_file_handle:
                self.log_file_handle.close()

    # -------------------------------------------------------------------
    # Monitoring cycle (one iteration of what CYTMonitorApp.run does)
    # -------------------------------------------------------------------
    def _process_cycle(self, list_update_interval: int,
                       health_check_interval: int,
                       kismet_interface: str,
                       context_cycles: int) -> None:
        """Execute one monitoring cycle."""
        self.cycle_count += 1
        try:
            with SecureKismetDB(self.latest_kismet_db) as db:
                self.monitor.process_current_activity(db)

                if self.cycle_count % list_update_interval == 0:
                    logging.info(f"Rotating tracking lists (cycle {self.cycle_count})")
                    self.monitor.rotate_tracking_lists(db)

                # Refresh device list for display
                self.device_rows = self._fetch_device_list(db)

            # Health check
            if (self.health_monitor and
                    self.cycle_count % health_check_interval == 0):
                health_status = self.health_monitor.monitor_and_recover(
                    interface=kismet_interface)
                if not health_status['healthy']:
                    issues = ", ".join(health_status['issues'])
                    logging.error(f"Kismet health FAILED: {issues}")

            # Context engine
            if (self.context_engine and
                    self.cycle_count % context_cycles == 0):
                try:
                    snapshot = self.context_engine.get_context()
                    if snapshot.surveillance_score > 0:
                        logging.info(f"Context: {snapshot.threat_level}")
                except Exception as e:
                    logging.debug(f"Context update skipped: {e}")

            # Archive detections
            detections = self.monitor.get_and_clear_detections()
            if detections:
                try:
                    history_manager.archive_appearances(detections)
                except Exception as e:
                    logging.error(f"Failed to archive detections: {e}")

        except Exception as e:
            logging.error(f"Error in monitoring cycle: {e}", exc_info=True)

    # -------------------------------------------------------------------
    # Device list extraction
    # -------------------------------------------------------------------
    def _fetch_device_list(self, db: SecureKismetDB) -> List[DeviceRow]:
        """Query the DB for current devices and flatten for display."""
        boundaries = self.monitor.time_manager.get_time_boundaries()
        devices = db.get_devices_by_time_range(boundaries['current_time'])
        rows = []
        for dev in devices:
            mac = dev.get('mac', '')
            if not mac or mac.upper() in self.monitor.ignore_list:
                continue

            device_data = dev.get('device_data') or {}
            signal_data = device_data.get('kismet.device.base.signal', {})
            signal_val = -100
            if isinstance(signal_data, dict):
                signal_val = signal_data.get(
                    'kismet.common.signal.last_signal', -100)

            channel = str(device_data.get('kismet.device.base.channel', ''))
            manuf = device_data.get('kismet.device.base.manuf', '')
            dev_type = device_data.get('kismet.device.base.type', dev.get('type', ''))

            last_time = dev.get('last_time', 0)
            try:
                last_seen = datetime.fromtimestamp(last_time).strftime('%H:%M:%S')
            except (OSError, ValueError):
                last_seen = ''

            threat = self._get_threat_level(mac, device_data)

            rows.append(DeviceRow(
                mac=mac,
                signal=signal_val if isinstance(signal_val, int) else -100,
                channel=channel,
                dev_type=dev_type,
                manufacturer=manuf[:20] if manuf else '',
                last_seen=last_seen,
                threat=threat
            ))

        # Sort: threats first, then by signal strength (strongest first)
        threat_order = {'drone': 0, 'behavioral': 1, 'persistent': 2, '': 3}
        rows.sort(key=lambda r: (threat_order.get(r.threat, 3), r.signal))
        return rows

    def _get_threat_level(self, mac: str, device_data: dict) -> str:
        """Determine threat coloring for a device."""
        # Drone OUI match
        if self.monitor.check_drone_threat(mac):
            return "drone"

        # Persistence check across tracking buckets
        score = 0
        if mac in self.monitor.five_ten_min_ago_macs:
            score += 2
        if mac in self.monitor.ten_fifteen_min_ago_macs:
            score += 3
        if mac in self.monitor.fifteen_twenty_min_ago_macs:
            score += 5
        if score >= 6:
            return "persistent"

        return ""

    # -------------------------------------------------------------------
    # Keyboard polling during sleep interval
    # -------------------------------------------------------------------
    def _poll_keyboard(self, stdscr, seconds: int) -> None:
        """Poll for keyboard input over `seconds`, redrawing each second."""
        curses.halfdelay(10)  # 1-second timeout (10 tenths of a second)
        for remaining in range(seconds, 0, -1):
            self._countdown = remaining
            self._draw(stdscr)
            try:
                key = stdscr.getch()
            except curses.error:
                key = -1

            if key == -1:
                continue
            elif key == ord('q') or key == ord('Q'):
                self.running = False
                return
            elif key == ord('1'):
                self.current_view = 1
                self.scroll_offset = 0
            elif key == ord('2'):
                self.current_view = 2
                self.scroll_offset = 0
            elif key == ord('\t'):
                self.current_view = 2 if self.current_view == 1 else 1
                self.scroll_offset = 0
            elif key == curses.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif key == curses.KEY_DOWN:
                self.scroll_offset += 1
            elif key == curses.KEY_PPAGE:  # Page Up
                self.scroll_offset = max(0, self.scroll_offset - 10)
            elif key == curses.KEY_NPAGE:  # Page Down
                self.scroll_offset += 10

    # -------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------
    def _draw(self, stdscr) -> None:
        """Master draw routine - header, content, status bar."""
        try:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            if max_y < MIN_ROWS or max_x < MIN_COLS:
                stdscr.addstr(0, 0, f"Terminal too small ({max_x}x{max_y}). Need {MIN_COLS}x{MIN_ROWS}.")
                stdscr.refresh()
                return

            self._draw_header(stdscr, max_y, max_x)

            # Content area: rows 2 through max_y-2
            content_top = 2
            content_bottom = max_y - 2
            content_height = content_bottom - content_top

            if self.current_view == 1:
                self._draw_live_feed(stdscr, content_top, content_height, max_x)
            else:
                self._draw_dashboard(stdscr, content_top, content_height, max_x)

            self._draw_status_bar(stdscr, max_y, max_x)
            stdscr.refresh()
        except curses.error:
            pass  # Terminal resize or write-past-end; ignore

    def _draw_header(self, stdscr, max_y: int, max_x: int) -> None:
        """Draw the header row with tabs and clock."""
        # Top border
        try:
            stdscr.addstr(0, 0, " CYT-NG TUI ", curses.color_pair(5) | curses.A_BOLD)

            # Tab labels
            tab1_attr = curses.color_pair(6) | curses.A_BOLD if self.current_view == 1 else curses.color_pair(7)
            tab2_attr = curses.color_pair(6) | curses.A_BOLD if self.current_view == 2 else curses.color_pair(7)

            col = 14
            stdscr.addstr(0, col, " [1] Live Feed ", tab1_attr)
            col += 16
            stdscr.addstr(0, col, " [2] Dashboard ", tab2_attr)

            # Clock
            clock = datetime.now().strftime('%H:%M:%S')
            if max_x > 50:
                stdscr.addstr(0, max_x - len(clock) - 1, clock, curses.color_pair(4))

            # Separator line
            stdscr.addstr(1, 0, "\u2500" * min(max_x - 1, max_x), curses.color_pair(4))
        except curses.error:
            pass

    def _draw_status_bar(self, stdscr, max_y: int, max_x: int) -> None:
        """Draw status bar at the bottom."""
        try:
            countdown = getattr(self, '_countdown', 0)
            view_name = "Live Feed" if self.current_view == 1 else "Dashboard"
            uptime_secs = int(time.time() - self.start_time)
            uptime_m, uptime_s = divmod(uptime_secs, 60)
            uptime_h, uptime_m = divmod(uptime_m, 60)

            bar = (f" View: {view_name} | "
                   f"Cycle: {self.cycle_count} | "
                   f"Devices: {len(self.device_rows)} | "
                   f"Up: {uptime_h}h{uptime_m:02d}m | "
                   f"Next: {countdown}s ")

            # Pad to full width
            bar = bar.ljust(max_x - 1)[:max_x - 1]
            stdscr.addstr(max_y - 1, 0, bar, curses.color_pair(5))
        except curses.error:
            pass

    # -------------------------------------------------------------------
    # View 1: Live Feed
    # -------------------------------------------------------------------
    def _draw_live_feed(self, stdscr, top: int, height: int, max_x: int) -> None:
        """Draw the scrolling device table."""
        # Column header
        hdr = f" {'MAC':<20}{'Sig':>5} {'Ch':>4}  {'Type':<16}{'Manufacturer':<20}{'Last Seen':>9}"
        try:
            stdscr.addstr(top, 0, hdr[:max_x - 1], curses.A_BOLD | curses.color_pair(4))
            stdscr.addstr(top + 1, 0, "\u2500" * min(max_x - 1, max_x), curses.color_pair(4))
        except curses.error:
            pass

        data_top = top + 2
        data_height = height - 2
        if data_height <= 0:
            return

        # Clamp scroll offset
        max_scroll = max(0, len(self.device_rows) - data_height)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        visible = self.device_rows[self.scroll_offset:self.scroll_offset + data_height]

        for i, row in enumerate(visible):
            y = data_top + i
            if y >= top + height:
                break

            line = (f" {row.mac:<20}{row.signal:>5} {row.channel:>4}  "
                    f"{row.dev_type:<16}{row.manufacturer:<20}{row.last_seen:>9}")
            line = line[:max_x - 1]

            attr = curses.A_NORMAL
            if row.threat == "drone":
                attr = curses.color_pair(1) | curses.A_BOLD
            elif row.threat == "behavioral":
                attr = curses.color_pair(2) | curses.A_BOLD
            elif row.threat == "persistent":
                attr = curses.color_pair(2)

            try:
                stdscr.addstr(y, 0, line, attr)
            except curses.error:
                pass

        # Scroll indicator
        if len(self.device_rows) > data_height:
            indicator = f" [{self.scroll_offset + 1}-{min(self.scroll_offset + data_height, len(self.device_rows))}/{len(self.device_rows)}]"
            try:
                stdscr.addstr(top + height - 1, max_x - len(indicator) - 1,
                              indicator, curses.color_pair(4))
            except curses.error:
                pass

    # -------------------------------------------------------------------
    # View 2: Dashboard
    # -------------------------------------------------------------------
    def _draw_dashboard(self, stdscr, top: int, height: int, max_x: int) -> None:
        """Draw system status overview."""
        y = top
        half_x = max_x // 2

        # --- Left column: Tracking Buckets ---
        try:
            stdscr.addstr(y, 1, "=== TRACKING BUCKETS ===", curses.A_BOLD | curses.color_pair(3))
        except curses.error:
            pass
        y += 1

        buckets = [
            ("Current (0-5 min)", len(self.monitor.past_five_mins_macs) if self.monitor else 0),
            ("5-10 min ago", len(self.monitor.five_ten_min_ago_macs) if self.monitor else 0),
            ("10-15 min ago", len(self.monitor.ten_fifteen_min_ago_macs) if self.monitor else 0),
            ("15-20 min ago", len(self.monitor.fifteen_twenty_min_ago_macs) if self.monitor else 0),
        ]
        for label, count in buckets:
            if y >= top + height:
                break
            line = f" {label:<22}{count:>5} MACs"
            try:
                stdscr.addstr(y, 1, line[:half_x - 2], curses.color_pair(3))
            except curses.error:
                pass
            y += 1

        y += 1
        try:
            stdscr.addstr(y, 1, "=== SSID TRACKING ===", curses.A_BOLD | curses.color_pair(3))
        except curses.error:
            pass
        y += 1

        ssid_buckets = [
            ("Current", len(self.monitor.past_five_mins_ssids) if self.monitor else 0),
            ("5-10 min", len(self.monitor.five_ten_min_ago_ssids) if self.monitor else 0),
            ("10-15 min", len(self.monitor.ten_fifteen_min_ago_ssids) if self.monitor else 0),
            ("15-20 min", len(self.monitor.fifteen_twenty_min_ago_ssids) if self.monitor else 0),
        ]
        for label, count in ssid_buckets:
            if y >= top + height:
                break
            line = f" {label:<22}{count:>5} SSIDs"
            try:
                stdscr.addstr(y, 1, line[:half_x - 2])
            except curses.error:
                pass
            y += 1

        # --- System status below SSIDs ---
        y += 1
        if y < top + height:
            try:
                stdscr.addstr(y, 1, "=== SYSTEM STATUS ===", curses.A_BOLD | curses.color_pair(3))
            except curses.error:
                pass
            y += 1

        uptime_secs = int(time.time() - self.start_time)
        uptime_m, uptime_s = divmod(uptime_secs, 60)
        uptime_h, uptime_m = divmod(uptime_m, 60)

        status_lines = [
            f" Uptime:   {uptime_h}h {uptime_m:02d}m {uptime_s:02d}s",
            f" Cycles:   {self.cycle_count}",
            f" DB:       {os.path.basename(self.latest_kismet_db) if self.latest_kismet_db else 'N/A'}",
            f" Log:      {os.path.basename(str(self.log_file_path)) if self.log_file_path else 'N/A'}",
            f" Health:   {'ACTIVE' if self.health_monitor else 'DISABLED'}",
            f" Context:  {'ACTIVE' if self.context_engine else 'DISABLED'}",
        ]
        for line in status_lines:
            if y >= top + height:
                break
            try:
                stdscr.addstr(y, 1, line[:half_x - 2])
            except curses.error:
                pass
            y += 1

        # --- Right column: Recent Alerts ---
        ry = top
        try:
            stdscr.addstr(ry, half_x + 1, "=== RECENT ALERTS ===",
                          curses.A_BOLD | curses.color_pair(2))
        except curses.error:
            pass
        ry += 1

        alert_list = list(self.alert_lines)
        # Show most recent alerts (bottom of deque = newest)
        max_alerts = height - 2
        recent = alert_list[-max_alerts:] if len(alert_list) > max_alerts else alert_list

        if not recent:
            try:
                stdscr.addstr(ry, half_x + 2, "(no alerts yet)",
                              curses.color_pair(7))
            except curses.error:
                pass
        else:
            for alert_line in recent:
                if ry >= top + height:
                    break
                # Truncate to fit right column
                display = alert_line[:max_x - half_x - 3]
                attr = curses.A_NORMAL
                if "CRIT:" in alert_line:
                    attr = curses.color_pair(1) | curses.A_BOLD
                elif "WARN:" in alert_line:
                    attr = curses.color_pair(2)
                try:
                    stdscr.addstr(ry, half_x + 2, display, attr)
                except curses.error:
                    pass
                ry += 1

    # -------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------
    def shutdown(self) -> None:
        """Clean shutdown."""
        self.running = False
        if self.log_file_handle:
            try:
                self.log_file_handle.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """Entry point with graceful fallback."""
    # Check if we have a real terminal
    if not sys.stdout.isatty():
        print("TUI: Not a terminal - falling back to standard CLI mode.")
        _run_fallback()
        return

    # Check terminal size
    try:
        cols, rows = os.get_terminal_size()
        if cols < MIN_COLS or rows < MIN_ROWS:
            print(f"TUI: Terminal too small ({cols}x{rows}). Need {MIN_COLS}x{MIN_ROWS}.")
            print("Falling back to standard CLI mode.")
            _run_fallback()
            return
    except OSError:
        pass  # If we can't determine size, let curses handle it

    tui = CYTTerminalUI()

    print("Initializing CYT-NG TUI...")
    if not tui.initialize():
        print("TUI initialization failed. Falling back to standard CLI mode.")
        _run_fallback()
        return

    try:
        curses.wrapper(tui.run)
    except curses.error as e:
        print(f"TUI: Curses error: {e}. Falling back to standard CLI mode.")
        tui.shutdown()
        _run_fallback()
    except Exception as e:
        tui.shutdown()
        print(f"TUI: Unexpected error: {e}")
        raise


def _run_fallback():
    """Fall back to the standard CYT CLI."""
    from chasing_your_tail import CYTMonitorApp
    app = CYTMonitorApp()
    if app.initialize():
        app.run()
    else:
        logging.critical("Application failed to initialize. Exiting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
