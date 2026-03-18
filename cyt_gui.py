from lib.gui_logic import (
    DatabaseNotFound,
    find_latest_db_path,
    get_dashboard_health_detail,
    get_dashboard_health_label,
    get_dashboard_health_summary,
    get_dashboard_health_tone,
    get_dashboard_stats,
)
from lib.watchlist_manager import DatabaseQueryError
from lib.database_utils import DatabaseInitError
from lib import gui_logic
from lib import history_manager
from lib import watchlist_manager
from cyt_constants import AlertType
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivy.clock import Clock
from kivy.animation import Animation
import time
import os
import json
import threading
import logging
import sqlite3
from collections import deque

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- KIVY UI CLASSES ---


class AliasPopup(ModalView):
    device_mac = StringProperty('')
    device_type = StringProperty('')
    main_app = ObjectProperty(None)

    def save(self, alias, notes):
        alias = alias.strip()
        if alias:
            notes = notes.strip()
            try:
                watchlist_manager.add_or_update_device(
                    self.device_mac, alias, self.device_type, notes)
                if self.main_app:
                    self.main_app.refresh_follower_list()
                    self.main_app.load_watchlist()
            except DatabaseQueryError as e:
                logging.error(f"Could not save alias: {e}")
            self.dismiss()


class WatchlistItem(BoxLayout):
    device_mac = StringProperty('')
    device_alias = StringProperty('')
    device_type = StringProperty('')
    main_app = ObjectProperty(None)

    def remove_from_watchlist(self):
        try:
            watchlist_manager.remove_device(self.device_mac)
            if self.main_app:
                self.main_app.load_watchlist()
        except DatabaseQueryError as e:
            logging.error(f"Could not remove device from watchlist: {e}")


class DeviceListItem(BoxLayout):
    device_mac = StringProperty('')
    device_alias = StringProperty('')
    locations_seen = StringProperty('')
    last_seen = StringProperty('')
    main_app = ObjectProperty(None)
    display_name = StringProperty('')
    device_type = StringProperty('')
    card_color = ListProperty([0.1, 0.1, 0.18, 1])

    def __init__(self, device_data, **kwargs):
        super().__init__(**kwargs)
        self.main_app = kwargs.get('main_app')
        self.device_mac = device_data[0]
        try:
            self.device_alias = watchlist_manager.get_device_alias(
                self.device_mac) or ''
        except DatabaseQueryError:
            self.device_alias = ''

        loc_count = device_data[1]
        self.locations_seen = str(loc_count)
        self.last_seen = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(device_data[2]))
        self.device_type = device_data[3] if device_data[3] else "Unknown"

        if self.device_alias:
            self.display_name = f"'{self.device_alias}'"
        else:
            self.display_name = self.device_mac

        # Color-code by locations seen count
        if loc_count >= 6:
            self.card_color = [0.3, 0.05, 0.05, 1]   # Red - high threat
        elif loc_count >= 3:
            self.card_color = [0.3, 0.2, 0.0, 1]     # Amber - medium
        else:
            self.card_color = [0.1, 0.1, 0.18, 1]    # Default dark

    def show_alias_popup(self):
        popup = AliasPopup(device_mac=self.device_mac,
                           device_type=self.device_type,
                           main_app=self.main_app)
        popup.open()

    def add_to_watchlist(self):
        try:
            alias = self.device_alias or self.device_mac
            watchlist_manager.add_or_update_device(
                self.device_mac, alias, self.device_type)
            logging.info(f"Added {self.device_mac} to watchlist")
            if self.main_app:
                self.main_app.load_watchlist()
        except DatabaseQueryError as e:
            logging.error(f"Could not add to watchlist: {e}")


class LiveDeviceItem(BoxLayout):
    device_mac = StringProperty('')
    signal = StringProperty('')
    channel = StringProperty('')
    device_type = StringProperty('')
    manufacturer = StringProperty('')
    last_seen = StringProperty('')
    signal_color = ListProperty([1, 1, 1, 1])

    def __init__(self, device_data, **kwargs):
        super().__init__(**kwargs)
        self.device_mac = device_data.get('mac', '')
        sig = device_data.get('signal', -100)
        self.signal = f"{sig} dBm"
        self.channel = str(device_data.get('channel', ''))
        self.device_type = device_data.get('type', 'Unknown')
        self.manufacturer = device_data.get('manufacturer', '')
        self.last_seen = time.strftime(
            '%H:%M:%S', time.localtime(device_data.get('last_seen', 0)))

        # Color-code signal strength
        if sig > -50:
            self.signal_color = [0.2, 1.0, 0.2, 1]  # Strong - Green
        elif sig > -70:
            self.signal_color = [1.0, 0.7, 0, 1]    # Medium - Amber
        else:
            self.signal_color = [1.0, 0.2, 0.2, 1]  # Weak - Red


# --- MAIN APPLICATION ---


class CYTApp(App):
    theme_colors = {
        "background": (0.05, 0.05, 0.1, 1),
        "text_primary": (0.7, 0.85, 1.0, 1),
        "accent_red": (1, 0.2, 0.2, 1),
        "accent_green": (0.2, 1.0, 0.2, 1),
        "accent_amber": (1, 0.7, 0, 1),
        "accent_purple": (0.8, 0.4, 1.0, 1)
    }
    dashboard_banner_bg = ListProperty([0.1, 0.14, 0.22, 1])
    dashboard_banner_border = ListProperty([1, 0.7, 0, 1])
    dashboard_last_refresh = StringProperty("Awaiting first refresh")
    live_feed_banner_bg = ListProperty([0.1, 0.14, 0.22, 1])
    live_feed_banner_border = ListProperty([1, 0.7, 0, 1])
    live_feed_status = StringProperty("Feed waiting for telemetry")
    live_feed_detail = StringProperty("Refresh the feed to load recent devices from Kismet.")
    telemetry_alert_text = StringProperty(AlertType.STATUS_MONITORING.value)

    def build(self):
        self.appearance_archive_queue = deque()
        self.appearance_archive_lock = threading.Lock()
        self.load_settings()

        try:
            history_manager.initialize_history_database()
        except DatabaseInitError as e:
            logging.critical(
                f"CRITICAL: Could not initialize HISTORY DB: {e}")
        except sqlite3.Error as e:
            logging.critical(
                f"CRITICAL: Database error initializing HISTORY DB: {e}")

        try:
            watchlist_manager.initialize_database()
        except DatabaseQueryError as e:
            logging.critical(
                f"CRITICAL: Could not initialize watchlist DB: {e}")

        # Schedule periodic tasks
        Clock.schedule_interval(
            self.start_follower_query, self.INTERVAL_FOLLOWERS)
        Clock.schedule_interval(self.check_watchlist, self.INTERVAL_WATCHLIST)
        Clock.schedule_interval(self.check_for_drones, self.INTERVAL_DRONES)
        Clock.schedule_interval(self.archive_data_task, self.ARCHIVE_INTERVAL)
        Clock.schedule_interval(self.refresh_live_feed, 5)  # Live feed every 5s

        # Load dashboard and watchlist after UI builds
        Clock.schedule_once(lambda dt: self.refresh_dashboard(), 0.5)
        Clock.schedule_once(lambda dt: self.load_watchlist(), 0.5)
        Clock.schedule_once(lambda dt: self.refresh_live_feed(0), 1.0)

    def load_settings(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            self._config = config
            kismet_log_path_pattern = config['paths']['kismet_logs']
            self.DB_PATH, self._db_glob_pattern = find_latest_db_path(
                kismet_log_path_pattern)
            if self.DB_PATH == "NOT_FOUND":
                raise FileNotFoundError(
                    f"No Kismet files found matching: "
                    f"{kismet_log_path_pattern}")
            logging.info(f"Using latest Kismet DB: {self.DB_PATH}")
            self.TIME_WINDOW = config['timing']['time_windows']['recent'] * 60
            check_interval = config['timing']['check_interval']
            self.INTERVAL_FOLLOWERS = check_interval
            self.INTERVAL_WATCHLIST = check_interval
            self.INTERVAL_DRONES = check_interval
            self.DB_FRESHNESS_MINUTES = config.get('kismet_health', {}).get(
                'data_freshness_threshold_minutes', 5)

            alert_settings = config.get('alert_settings', {})
            self.LOCATIONS_THRESHOLD = alert_settings.get(
                'locations_threshold', 3)
            self.DRONE_ALERT_WINDOW = alert_settings.get(
                'drone_time_window_seconds', 300)
            self.WATCHLIST_ALERT_WINDOW = alert_settings.get(
                'watchlist_time_window_seconds', 300)

            ui_settings = config.get('ui_settings', {})
            self.ANIMATION_DURATION = ui_settings.get(
                'animation_duration', 0.7)
            self.ARCHIVE_INTERVAL = ui_settings.get(
                'archive_interval_seconds', 300)
            self.LIVE_FEED_WINDOW = ui_settings.get(
                'live_feed_window_seconds', 120)
        except (IOError, KeyError, FileNotFoundError) as e:
            logging.critical(
                f"Failed to load settings from config.json: {e}")
            self._config = {}
            self.DB_PATH = "NOT_FOUND"
            self.INTERVAL_FOLLOWERS = 60
            self.INTERVAL_WATCHLIST = 60
            self.INTERVAL_DRONES = 60
            self.TIME_WINDOW = 300
            self.LOCATIONS_THRESHOLD = 3
            self.DRONE_ALERT_WINDOW = 300
            self.WATCHLIST_ALERT_WINDOW = 300
            self.ANIMATION_DURATION = 0.7
            self.ARCHIVE_INTERVAL = 300
            self.DB_FRESHNESS_MINUTES = 5
            self.LIVE_FEED_WINDOW = 120

    def _maybe_refresh_db_path(self):
        pattern = getattr(self, "_db_glob_pattern", None)
        if not pattern:
            return
        latest, _ = find_latest_db_path(pattern)
        if latest == "NOT_FOUND":
            if self.DB_PATH != "NOT_FOUND":
                logging.warning("No Kismet files found. Waiting for data...")
                self.DB_PATH = "NOT_FOUND"
            return
        if self.DB_PATH != latest:
            logging.info(f"Switching to latest Kismet DB: {latest}")
            self.DB_PATH = latest

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def refresh_dashboard(self):
        """Refresh dashboard statistics from database."""
        threading.Thread(
            target=self._refresh_dashboard_bg, daemon=True).start()

    def _refresh_dashboard_bg(self):
        self._maybe_refresh_db_path()
        stats = get_dashboard_stats(self.DB_PATH, self.DB_FRESHNESS_MINUTES)
        Clock.schedule_once(lambda dt: self._update_dashboard_ui(stats))

    def _update_dashboard_ui(self, stats):
        ids = self.root.ids
        ids.dash_db_file.text = stats.get('db_file', 'None')
        ids.dash_db_status.text = stats.get('db_status', 'DISCONNECTED')
        ids.dash_device_count.text = str(stats.get('device_count', 0))
        ids.dash_watchlist_count.text = str(stats.get('watchlist_count', 0))
        ids.dash_last_seen.text = stats.get('last_seen_time', 'N/A')
        ids.dash_db_age.text = (
            f"{stats['db_age_minutes']} min"
            if stats.get('db_age_minutes') is not None else "N/A")
        ids.dash_db_freshness.text = stats.get('db_freshness', 'UNKNOWN')

        tone = get_dashboard_health_tone(stats)
        tone_color = self._dashboard_health_color(tone)
        summary = get_dashboard_health_summary(stats)
        detail = get_dashboard_health_detail(stats)
        chip = get_dashboard_health_label(stats)
        status = stats.get('db_status', '')

        ids.dash_health_chip.text = f"[ {chip} ]"
        ids.dash_health_chip.color = tone_color
        ids.dash_health_summary.text = summary
        ids.dash_health_summary.color = tone_color
        ids.dash_health_detail.text = detail
        self.dashboard_banner_border = list(tone_color)
        self.dashboard_banner_bg = self._dashboard_banner_bg(tone)
        self.dashboard_last_refresh = time.strftime(
            "Last refresh: %Y-%m-%d %H:%M:%S", time.localtime()
        )

        ids.dash_db_status.color = tone_color
        ids.dash_db_freshness.color = tone_color
        ids.dash_db_age.color = (
            tone_color
            if stats.get('db_age_minutes') is not None
            else self.theme_colors['text_primary']
        )
        ids.dash_db_file.color = (
            self.theme_colors['text_primary']
            if status == 'CONNECTED'
            else tone_color
        )
        self._update_telemetry_alert(stats)

    def _dashboard_health_color(self, tone):
        if tone == 'healthy':
            return self.theme_colors['accent_green']
        if tone == 'warning':
            return self.theme_colors['accent_amber']
        return self.theme_colors['accent_red']

    def _dashboard_banner_bg(self, tone):
        if tone == 'healthy':
            return [0.08, 0.16, 0.12, 1]
        if tone == 'warning':
            return [0.18, 0.14, 0.06, 1]
        return [0.18, 0.08, 0.08, 1]

    def run_deep_analysis(self):
        """Launch surveillance analysis in a background thread."""
        threading.Thread(
            target=self._run_deep_analysis_bg, daemon=True).start()

    def _run_deep_analysis_bg(self):
        Clock.schedule_once(
            lambda dt: self._set_alert_text("Running deep analysis..."))
        try:
            from surveillance_analyzer import SurveillanceAnalyzer
            config = getattr(self, '_config', {})
            analyzer = SurveillanceAnalyzer(config)
            analyzer.analyze_kismet_data(self.DB_PATH)
            results = analyzer.run_full_analysis()
            report_paths = analyzer.generate_reports()
            summary = analyzer.get_summary()

            msg = (f"Analysis complete: {summary['suspicious_devices']} "
                   f"suspicious devices found")
            Clock.schedule_once(lambda dt: self._set_alert_text(msg))
            logging.info(f"Deep analysis done. Reports: {report_paths}")
        except Exception as e:
            logging.error(f"Deep analysis failed: {e}")
            Clock.schedule_once(
                lambda dt: self._set_alert_text(f"Analysis failed: {e}"))

    def _set_alert_text(self, text):
        self.root.ids.alert_bar.text = text

    # ------------------------------------------------------------------
    # Watchlist management
    # ------------------------------------------------------------------

    def add_to_watchlist(self, mac, alias):
        """Add a device from the Watchlist tab input fields."""
        mac = mac.strip()
        alias = alias.strip()
        if not mac:
            return
        if not alias:
            alias = mac
        try:
            watchlist_manager.add_or_update_device(mac, alias, 'Unknown')
            logging.info(f"Added {mac} ('{alias}') to watchlist")
            self.load_watchlist()
            self.root.ids.wl_mac_input.text = ''
            self.root.ids.wl_alias_input.text = ''
        except DatabaseQueryError as e:
            logging.error(f"Could not add to watchlist: {e}")

    def load_watchlist(self):
        """Populate the Watchlist tab with all watchlisted devices."""
        watchlist_view = self.root.ids.watchlist_view
        watchlist_view.clear_widgets()
        try:
            devices = watchlist_manager.get_all_devices()
            if not devices:
                watchlist_view.add_widget(Label(
                    text="Watchlist is empty.",
                    font_size='16sp',
                    color=self.theme_colors['text_primary'],
                    size_hint_y=None, height=40))
                return
            for dev in devices:
                item = WatchlistItem()
                item.device_mac = dev.get('mac', '')
                item.device_alias = dev.get('alias', '')
                item.device_type = dev.get('device_type', 'Unknown')
                item.main_app = self
                watchlist_view.add_widget(item)
        except DatabaseQueryError as e:
            logging.error(f"Could not load watchlist: {e}")
            watchlist_view.add_widget(Label(
                text=f"Error: {e}", font_size='14sp',
                color=self.theme_colors['accent_red'],
                size_hint_y=None, height=40))

    # ------------------------------------------------------------------
    # Monitor tab (follower detection)
    # ------------------------------------------------------------------

    def start_follower_query(self, dt):
        follower_list = self.root.ids.follower_list
        follower_list.clear_widgets()
        loading_label = Label(
            text="Querying for followers...", font_size='20sp',
            color=self.theme_colors['text_primary'])
        follower_list.add_widget(loading_label)
        anim = Animation(
            opacity=0.5, duration=self.ANIMATION_DURATION) + \
            Animation(opacity=1, duration=self.ANIMATION_DURATION)
        anim.repeat = True
        anim.start(loading_label)
        threading.Thread(
            target=self.run_follower_query_in_background, daemon=True).start()

    def run_follower_query_in_background(self):
        try:
            self._maybe_refresh_db_path()
            followers = gui_logic.get_chase_targets(
                self.DB_PATH, self.TIME_WINDOW, self.LOCATIONS_THRESHOLD)
            Clock.schedule_once(
                lambda dt: self.update_ui_with_results(followers))
        except (DatabaseNotFound, DatabaseQueryError) as e:
            logging.error(f"Follower query failed: {e}")
            Clock.schedule_once(
                lambda dt, exc=e: self.update_ui_with_results(exc))

    def update_ui_with_results(self, results):
        follower_list = self.root.ids.follower_list

        if isinstance(results, list) and results:
            try:
                watchlist_macs = watchlist_manager.get_watchlist_macs()
                threat_mac = gui_logic.find_confirmed_threats(
                    results, watchlist_macs)
                if threat_mac:
                    alias = watchlist_manager.get_device_alias(threat_mac)
                    self.trigger_watchlist_alert(threat_mac, alias)
            except DatabaseQueryError as e:
                logging.warning(
                    f"Could not cross-reference watchlist: {e}")

            for device_row in results:
                appearance = {
                    "mac": device_row[0], "timestamp": device_row[2],
                    "location_id": "follower_detection"}
                with self.appearance_archive_lock:
                    self.appearance_archive_queue.append(appearance)

        follower_list.clear_widgets()
        if isinstance(results, Exception):
            follower_list.add_widget(Label(
                text=str(results), font_size='20sp',
                color=self.theme_colors['accent_red']))
        elif not results:
            follower_list.add_widget(Label(
                text="No followers detected.", font_size='20sp',
                color=self.theme_colors['text_primary']))
        else:
            for device in results:
                item = DeviceListItem(device_data=device, main_app=self)
                follower_list.add_widget(item)

    # ------------------------------------------------------------------
    # Alert bar
    # ------------------------------------------------------------------

    def trigger_watchlist_alert(self, mac, alias):
        """Alert that a watchlisted device was detected in the current scan.

        This is an informational alert - it means a device you are tracking
        is present in the Kismet data.  It does NOT mean you are being
        followed.  The deep analysis (SurveillanceAnalyzer) is what
        determines actual following / surveillance behaviour.
        """
        alert_bar = self.root.ids.alert_bar
        display_name = f"'{alias}'" if alias else mac
        alert_bar.text = (f"{AlertType.WATCHLIST.value}: "
                          f"Watchlist device {display_name} detected nearby")
        Animation.cancel_all(alert_bar)
        alert_bar.color = self.theme_colors['accent_amber']

    def reset_alert_bar(self):
        alert_bar = self.root.ids.alert_bar
        Animation.cancel_all(alert_bar)
        alert_bar.text = self.telemetry_alert_text
        alert_bar.color = self._telemetry_alert_color()

    # ------------------------------------------------------------------
    # Periodic checks
    # ------------------------------------------------------------------

    def check_for_drones(self, dt):
        alert_bar = self.root.ids.alert_bar
        # Drone alerts take priority over watchlist, but not analysis results
        if AlertType.WATCHLIST.value in alert_bar.text:
            return

        drones = gui_logic.run_drone_check(
            self.DB_PATH, self.DRONE_ALERT_WINDOW)
        if drones:
            drone_mac, drone_name = drones[0]
            display_name = drone_name if drone_name else drone_mac
            alert_bar.text = (f"{AlertType.DRONE.value} DETECTED: "
                              f"{display_name}")
            alert_bar.color = self.theme_colors['accent_red']
        elif AlertType.DRONE.value in alert_bar.text:
            self.reset_alert_bar()

    def check_watchlist(self, dt):
        alert_bar = self.root.ids.alert_bar
        # Don't override drone alerts
        if AlertType.DRONE.value in alert_bar.text:
            return

        try:
            watchlist = watchlist_manager.get_watchlist_macs()
            if not watchlist:
                if AlertType.WATCHLIST.value in alert_bar.text:
                    self.reset_alert_bar()
                return

            seen_macs = gui_logic.run_watchlist_check(
                self.DB_PATH, watchlist, self.WATCHLIST_ALERT_WINDOW)
            if seen_macs:
                alias = watchlist_manager.get_device_alias(seen_macs[0])
                display_name = f"'{alias}'" if alias else seen_macs[0]
                alert_bar.text = (f"{AlertType.WATCHLIST.value}: "
                                  f"Watchlist device {display_name} detected nearby")
                alert_bar.color = self.theme_colors['accent_amber']
            elif AlertType.WATCHLIST.value in alert_bar.text:
                self.reset_alert_bar()
        except DatabaseQueryError as e:
            logging.warning(f"Could not check watchlist: {e}")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def clear_follower_list(self):
        follower_list = self.root.ids.follower_list
        follower_list.clear_widgets()
        follower_list.add_widget(Label(
            text="Follower list cleared.", font_size='20sp',
            color=self.theme_colors['text_primary']))
        logging.info("Follower list cleared by user.")

    def refresh_follower_list(self):
        self.start_follower_query(0)

    def refresh_live_feed(self, dt):
        """Refresh the live device feed tab."""
        threading.Thread(
            target=self._refresh_live_feed_bg, daemon=True).start()

    def _refresh_live_feed_bg(self):
        try:
            self._maybe_refresh_db_path()
            stats = get_dashboard_stats(self.DB_PATH, self.DB_FRESHNESS_MINUTES)
            live_devices = gui_logic.get_live_device_feed(
                self.DB_PATH, self.LIVE_FEED_WINDOW)
            Clock.schedule_once(
                lambda dt: self._update_live_feed_ui(live_devices, stats))
        except Exception as e:
            logging.error(f"Failed to refresh live feed: {e}")

    def _update_live_feed_ui(self, devices, stats):
        live_list = self.root.ids.live_device_list
        live_list.clear_widgets()
        tone = get_dashboard_health_tone(stats)
        self.live_feed_banner_border = list(self._dashboard_health_color(tone))
        self.live_feed_banner_bg = self._dashboard_banner_bg(tone)

        if not devices:
            self.live_feed_status, self.live_feed_detail = self._live_feed_empty_copy(stats)
            live_list.add_widget(Label(
                text=self.live_feed_detail,
                font_size='16sp', color=self.theme_colors['text_primary'],
                size_hint_y=None, height=40))
            return

        self.live_feed_status = (
            f"{len(devices)} active devices in last {self.LIVE_FEED_WINDOW // 60} min"
        )
        self.live_feed_detail = (
            f"{get_dashboard_health_summary(stats)} | "
            f"Last seen: {stats.get('last_seen_time', 'N/A')}"
        )
        for dev in devices[:50]:  # Limit to top 50 for performance
            item = LiveDeviceItem(device_data=dev)
            live_list.add_widget(item)

    def _live_feed_empty_copy(self, stats):
        summary = get_dashboard_health_summary(stats)
        detail = get_dashboard_health_detail(stats)
        if summary == "Telemetry Healthy":
            return (
                "Feed quiet, telemetry healthy",
                f"No devices seen in the last {self.LIVE_FEED_WINDOW // 60} min.",
            )
        if summary == "Telemetry Stale":
            return ("Feed stale", detail)
        if summary == "Database Error":
            return ("Feed unavailable", detail)
        return ("Feed offline", detail)

    def _update_telemetry_alert(self, stats):
        summary = get_dashboard_health_summary(stats)
        if summary == "Telemetry Healthy":
            self.telemetry_alert_text = AlertType.STATUS_MONITORING.value
        else:
            self.telemetry_alert_text = (
                f"{AlertType.STATUS_MONITORING.value} | {summary.upper()}"
            )

        alert_bar = self.root.ids.alert_bar
        if self._alert_bar_locked():
            return

        alert_bar.text = self.telemetry_alert_text
        alert_bar.color = self._telemetry_alert_color()

    def _telemetry_alert_color(self):
        if "STALE" in self.telemetry_alert_text:
            return self.theme_colors['accent_amber']
        if "OFFLINE" in self.telemetry_alert_text or "ERROR" in self.telemetry_alert_text:
            return self.theme_colors['accent_red']
        return self.theme_colors['accent_green']

    def _alert_bar_locked(self):
        alert_text = self.root.ids.alert_bar.text
        return (
            AlertType.DRONE.value in alert_text
            or AlertType.WATCHLIST.value in alert_text
        )

    def archive_data_task(self, dt):
        """Takes pending appearances from the queue and archives them."""
        with self.appearance_archive_lock:
            if not self.appearance_archive_queue:
                return
            items_to_archive = list(self.appearance_archive_queue)
            self.appearance_archive_queue.clear()

        logging.info(
            f"Archiving {len(items_to_archive)} device appearances...")
        threading.Thread(target=history_manager.archive_appearances, args=(
            items_to_archive,), daemon=True).start()


if __name__ == '__main__':
    CYTApp().run()
