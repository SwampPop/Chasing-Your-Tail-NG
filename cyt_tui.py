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
from secure_database import SecureKismetDB
from secure_ignore_loader import load_ignore_lists
from secure_main_logic import SecureCYTMonitor
from lib import history_manager
from lib.gui_logic import (
    find_latest_db_path,
    get_dashboard_health_label,
    get_dashboard_health_tone,
    get_dashboard_stats,
    get_kismet_logs_path,
)

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
        self.db_glob_pattern: Optional[str] = None
        self.monitor: Optional[TUIMonitor] = None
        self.health_monitor = None
        self.alert_manager_instance = None
        self.context_engine = None
        self.log_file_handle = None
        self.log_file_path: Optional[pathlib.Path] = None
        self.behavioral_threats: Dict[str, float] = {}
        self.show_help = False
        self.filter_mode = "all"
        self.sort_mode = "threat"
        self.top_n_limit = 50
        self.live_feed_window_seconds = 120
        self.db_freshness_minutes = 5
        self.dashboard_stats: Dict[str, Any] = {}

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
            from secure_credentials import secure_config_loader
            self.config, self.credential_manager = secure_config_loader('config.json')

            logging.info("Loading ignore lists...")
            self.ignore_list, self.probe_ignore_list = load_ignore_lists(self.config)
            logging.info(f"Loaded {len(self.ignore_list)} MACs, {len(self.probe_ignore_list)} SSIDs to ignore")

            # Find latest Kismet DB
            db_path_pattern = get_kismet_logs_path(self.config)
            self.latest_kismet_db, self.db_glob_pattern = find_latest_db_path(
                db_path_pattern, fallback_path="test_capture.kismet")
            if self.latest_kismet_db == "NOT_FOUND":
                logging.critical(f"No Kismet database files found at: {self.db_glob_pattern}")
                return False
            logging.info(f"Using Kismet database: {self.latest_kismet_db}")
            self.db_freshness_minutes = self.config.get(
                'kismet_health', {}).get('data_freshness_threshold_minutes', 5)
            self.live_feed_window_seconds = self.config.get(
                'ui_settings', {}).get('live_feed_window_seconds', 120)

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
                        db_path_pattern=self.db_glob_pattern or get_kismet_logs_path(self.config),
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

    def _refresh_latest_kismet_db(self) -> None:
        if not self.db_glob_pattern:
            return
        latest, _ = find_latest_db_path(self.db_glob_pattern, fallback_path="test_capture.kismet")
        if latest == "NOT_FOUND":
            return
        if latest != self.latest_kismet_db:
            self.latest_kismet_db = latest
            logging.info(f"Switched to latest Kismet DB: {latest}")

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
        db_refresh_interval = self.config.get('timing', {}).get('db_refresh_interval_cycles', 5)
        health_check_interval = self.config.get('kismet_health', {}).get('check_interval_cycles', 5)
        kismet_interface = self.config.get('kismet_health', {}).get('interface', 'wlan0mon')
        context_check_interval = self.config.get('context_engine', {}).get('poll_interval_seconds', 30)
        context_cycles = max(1, context_check_interval // check_interval)
        self.top_n_limit = self.config.get('ui_settings', {}).get('tui_top_n', 50)

        try:
            while self.running:
                # --- Process one monitoring cycle ---
                self._process_cycle(list_update_interval, db_refresh_interval,
                                    health_check_interval,
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
                       db_refresh_interval: int,
                       health_check_interval: int,
                       kismet_interface: str,
                       context_cycles: int) -> None:
        """Execute one monitoring cycle."""
        self.cycle_count += 1
        try:
            if db_refresh_interval and self.cycle_count % db_refresh_interval == 0:
                self._refresh_latest_kismet_db()
            with SecureKismetDB(self.latest_kismet_db) as db:
                self.monitor.process_current_activity(db)
                self.dashboard_stats = get_dashboard_stats(
                    self.latest_kismet_db, self.db_freshness_minutes)

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
        devices = db.get_live_devices(self.live_feed_window_seconds)
        self.behavioral_threats = {}
        behavior_threshold = self.config.get(
            'behavioral_drone_detection', {}).get('confidence_threshold', 0.60)
        rows = []
        for dev in devices:
            mac = dev.get('mac', '')
            if not mac or mac.upper() in self.monitor.ignore_list:
                continue

            device_data = dev.get('device_data') or {}
            signal_val = dev.get('signal', -100)
            channel = str(dev.get('channel', ''))
            manuf = dev.get('manufacturer', '')
            dev_type = dev.get('type', 'Unknown')

            last_time = dev.get('last_time', 0)
            try:
                last_seen = datetime.fromtimestamp(last_time).strftime('%H:%M:%S')
            except (OSError, ValueError):
                last_seen = ''

            behavioral_confidence = None
            if self.monitor.behavioral_detector:
                behavioral_confidence, _ = self.monitor.behavioral_detector.analyze_device(mac)
                if behavioral_confidence >= behavior_threshold:
                    self.behavioral_threats[mac] = behavioral_confidence
            threat = self._get_threat_level(mac, device_data, behavioral_confidence, behavior_threshold)

            rows.append(DeviceRow(
                mac=mac,
                signal=signal_val if isinstance(signal_val, int) else -100,
                channel=channel,
                dev_type=dev_type,
                manufacturer=manuf[:20] if manuf else '',
                last_seen=last_seen,
                threat=threat
            ))

        return self._apply_filters(rows)

    def _get_threat_level(self, mac: str, device_data: dict,
                          behavioral_confidence: Optional[float],
                          behavior_threshold: float) -> str:
        """Determine threat coloring for a device."""
        # Drone OUI match
        if self.monitor.check_drone_threat(mac):
            return "drone"

        if (behavioral_confidence is not None and
                behavioral_confidence >= behavior_threshold):
            return "behavioral"

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

    def _apply_filters(self, rows: List[DeviceRow]) -> List[DeviceRow]:
        if self.filter_mode == "threats":
            rows = [r for r in rows if r.threat]
        elif self.filter_mode == "signal_top":
            rows.sort(key=lambda r: -r.signal)
            return rows[:self.top_n_limit]
        elif self.filter_mode == "ap":
            rows = [r for r in rows if self._device_type_category(r.dev_type) == "ap"]
        elif self.filter_mode == "client":
            rows = [r for r in rows if self._device_type_category(r.dev_type) == "client"]

        if self.sort_mode == "signal":
            rows.sort(key=lambda r: -r.signal)
        else:
            threat_order = {'drone': 0, 'behavioral': 1, 'persistent': 2, '': 3}
            rows.sort(key=lambda r: (threat_order.get(r.threat, 3), -r.signal))
        return rows

    @staticmethod
    def _device_type_category(dev_type: str) -> str:
        dt = (dev_type or "").lower()
        if "ap" in dt or "access" in dt:
            return "ap"
        if "client" in dt or "station" in dt:
            return "client"
        return "other"

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
            elif key in (ord('h'), ord('H'), ord('?')):
                self.show_help = not self.show_help
            elif key in (ord('f'), ord('F')):
                self._cycle_filter_mode()
                self.scroll_offset = 0
            elif key in (ord('s'), ord('S')):
                self.sort_mode = "signal" if self.sort_mode == "threat" else "threat"
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
            if self.show_help:
                self._draw_help(stdscr, max_y, max_x)
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

            # Legend (only if there's room)
            legend = "f=filter s=sort h=help"
            legend_x = max_x - len(clock) - len(legend) - 3
            if legend_x > col + 2:
                stdscr.addstr(0, legend_x, legend, curses.color_pair(7))

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
                   f"Filter: {self._filter_label()} | "
                   f"Sort: {self.sort_mode} | "
                   f"Next: {countdown}s | "
                   f"Keys: 1/2 Tab Up/Down PgUp PgDn f s h q")

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
        hdr = f" {'T':<2}{'MAC':<18}{'Sig':>5} {'Ch':>4}  {'Type':<14}{'Manufacturer':<20}{'Last Seen':>9}"
        try:
            stdscr.addstr(top, 0, hdr[:max_x - 1], curses.A_BOLD | curses.color_pair(4))
            stdscr.addstr(top + 1, 0, "\u2500" * min(max_x - 1, max_x), curses.color_pair(4))
            legend = "Legend: D=Drone B=Behavioral P=Persistent | f=filter s=sort h=help"
            stdscr.addstr(top + 2, 0, legend[:max_x - 1], curses.color_pair(7))
        except curses.error:
            pass

        data_top = top + 3
        data_height = height - 3
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

            threat_code = {
                "drone": "D",
                "behavioral": "B",
                "persistent": "P",
                "": ""
            }.get(row.threat, "")
            line = (f" {threat_code:<2}{row.mac:<18}{row.signal:>5} {row.channel:>4}  "
                    f"{row.dev_type:<14}{row.manufacturer:<20}{row.last_seen:>9}")
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

        db_status = self.dashboard_stats.get('db_status', 'DISCONNECTED')
        db_freshness = self.dashboard_stats.get('db_freshness', 'UNKNOWN')
        db_health_line = (
            f" Telemetry:{get_dashboard_health_label(self.dashboard_stats):>11}"
            f" | {self._format_db_freshness()}"
        )
        try:
            stdscr.addstr(
                y, 1, db_health_line[:half_x - 2],
                self._db_status_attr(db_status, db_freshness)
            )
        except curses.error:
            pass
        y += 1

        # --- Right column: Recent Alerts ---
        ry = top
        header_text = self._alerts_header_text()
        header_attr = self._alerts_header_attr()
        try:
            stdscr.addstr(ry, half_x + 1, header_text[:max_x - half_x - 2],
                          header_attr)
        except curses.error:
            pass
        ry += 1

        alert_counts = self._count_alert_levels()
        summary = (f" CRIT: {alert_counts['CRIT']}  "
                   f"WARN: {alert_counts['WARN']}  "
                   f"INFO: {alert_counts['INFO']}")
        try:
            stdscr.addstr(ry, half_x + 2, summary[:max_x - half_x - 3],
                          curses.color_pair(7))
        except curses.error:
            pass
        ry += 1

        alert_list = list(self.alert_lines)
        # Show most recent alerts (bottom of deque = newest)
        max_alerts = max(0, height - 3)
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

    def _count_alert_levels(self) -> Dict[str, int]:
        counts = {"CRIT": 0, "WARN": 0, "INFO": 0}
        for line in self.alert_lines:
            if "CRIT:" in line:
                counts["CRIT"] += 1
            elif "WARN:" in line:
                counts["WARN"] += 1
            else:
                counts["INFO"] += 1
        return counts

    def _format_db_freshness(self) -> str:
        freshness = self.dashboard_stats.get('db_freshness', 'UNKNOWN')
        age = self.dashboard_stats.get('db_age_minutes')
        if age is None:
            return str(freshness)
        return f"{freshness} ({age} min)"

    def _db_status_style(self, db_status: str, freshness: str) -> str:
        if db_status == 'CONNECTED' and freshness == 'ACTIVE':
            return "healthy"
        if db_status == 'CONNECTED' and freshness in ('STALE', 'UNKNOWN'):
            return "warning"
        return "error"

    def _alerts_header_text(self) -> str:
        label = get_dashboard_health_label(self.dashboard_stats)
        if label == "HEALTHY":
            return "=== RECENT ALERTS ==="
        return f"=== RECENT ALERTS | TELEMETRY {label} ==="

    def _alerts_header_attr(self):
        tone = get_dashboard_health_tone(self.dashboard_stats)
        if tone == "healthy":
            return curses.A_BOLD | curses.color_pair(2)
        if tone == "warning":
            return curses.A_BOLD | curses.color_pair(2)
        return curses.A_BOLD | curses.color_pair(1)

    def _db_status_attr(self, db_status: str, freshness: str):
        style = self._db_status_style(db_status, freshness)
        if style == "healthy":
            return curses.color_pair(3) | curses.A_BOLD
        if style == "warning":
            return curses.color_pair(2) | curses.A_BOLD
        return curses.color_pair(1) | curses.A_BOLD

    def _filter_label(self) -> str:
        labels = {
            "all": "all",
            "threats": "threats",
            "signal_top": f"top{self.top_n_limit}",
            "ap": "ap",
            "client": "client"
        }
        return labels.get(self.filter_mode, self.filter_mode)

    def _cycle_filter_mode(self) -> None:
        modes = ["all", "threats", "signal_top", "ap", "client"]
        idx = modes.index(self.filter_mode) if self.filter_mode in modes else 0
        self.filter_mode = modes[(idx + 1) % len(modes)]

    def _draw_help(self, stdscr, max_y: int, max_x: int) -> None:
        help_lines = [
            "CYT-NG TUI HELP",
            "",
            "Views:     1 = Live Feed, 2 = Dashboard, Tab = toggle",
            "Scroll:    Up/Down, PgUp/PgDn",
            "Filters:   f = cycle (all, threats, top-N, ap, client)",
            "Sorting:   s = toggle (threat | signal)",
            "Help:      h or ?",
            "Quit:      q",
            "",
            "Threats:   D=Drone  B=Behavioral  P=Persistent",
        ]
        box_width = min(max_x - 4, 64)
        box_height = len(help_lines) + 2
        start_y = max(2, (max_y - box_height) // 2)
        start_x = max(2, (max_x - box_width) // 2)
        try:
            for i in range(box_height):
                stdscr.addstr(start_y + i, start_x, " " * box_width, curses.color_pair(5))
            for i, line in enumerate(help_lines):
                truncated = line[:box_width - 4]
                stdscr.addstr(start_y + 1 + i, start_x + 2, truncated, curses.A_BOLD)
        except curses.error:
            pass
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
        # Check log file for the actual error
        if tui.log_file_path and os.path.exists(tui.log_file_path):
            with open(tui.log_file_path) as f:
                for line in f:
                    if 'CRITICAL' in line or 'Fatal' in line:
                        print(f"  Error: {line.strip()}")
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
