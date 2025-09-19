import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
import time
import sqlite3
import os
import json
import threading
import logging
import glob

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Custom Exception ---
class DatabaseNotFound(Exception):
    pass

# --- Import from custom modules ---
from lib import watchlist_manager
from lib.watchlist_manager import DatabaseQueryError

# --- Constants ---
ALERT_TYPE_DRONE = "DRONE"
ALERT_TYPE_WATCHLIST = "ALERT"
STATUS_MONITORING = "STATUS: MONITORING"
ALERT_TYPE_CONFIRMED = "CONFIRMED THREAT"

# --- CORE LOGIC FUNCTION ---
def get_chase_targets(db_path, time_window, locations_threshold):
    if not os.path.exists(db_path) or db_path == "NOT_FOUND":
        raise DatabaseNotFound(f"Error: The database file could not be found at '{db_path}'")
    try:
        with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            end_time = int(time.time())
            start_time = end_time - time_window
            query = """
            SELECT
                p.sourcemac as devmac,
                COUNT(DISTINCT p.datasource) as locations,
                MAX(p.ts_sec) as last_seen,
                d.type as device_type
            FROM packets p
            JOIN devices d ON p.sourcemac = d.devmac
            WHERE p.sourcemac IS NOT NULL AND p.sourcemac != '00:00:00:00:00:00' AND p.ts_sec > ?
            GROUP BY p.sourcemac
            HAVING locations >= ?
            ORDER BY last_seen DESC
            """
            cursor.execute(query, (start_time, locations_threshold))
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"A database error occurred in get_chase_targets: {e}")
        raise DatabaseQueryError(f"A database error occurred in get_chase_targets: {e}")

# --- KIVY UI CLASSES ---
class AliasPopup(ModalView):
    device_mac = StringProperty(''); device_type = StringProperty('')
    main_app = ObjectProperty(None)
    def save(self, alias, notes):
        alias = alias.strip()
        if alias:
            notes = notes.strip()
            try:
                watchlist_manager.add_or_update_device(self.device_mac, alias, self.device_type, notes)
                self.main_app.refresh_follower_list()
            except DatabaseQueryError as e:
                logging.error(f"Could not save alias: {e}")
            self.dismiss()

class DeviceListItem(BoxLayout):
    device_mac = StringProperty(''); device_alias = StringProperty('')
    locations_seen = StringProperty(''); last_seen = StringProperty('')
    main_app = ObjectProperty(None); display_name = StringProperty('')
    device_type = StringProperty('')
    def __init__(self, device_data, **kwargs):
        super().__init__(**kwargs)
        self.main_app = kwargs.get('main_app')
        self.device_mac = device_data[0]
        try:
            self.device_alias = watchlist_manager.get_device_alias(self.device_mac) or ''
        except DatabaseQueryError as e:
            self.device_alias = ''
            logging.error(f"Could not get device alias: {e}")
        self.locations_seen = str(device_data[1])
        self.last_seen = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(device_data[2]))
        self.device_type = device_data[3] if device_data[3] else "Unknown"
        if self.device_alias:
            self.display_name = f"'{self.device_alias}'"
        else:
            self.display_name = self.device_mac
    def show_alias_popup(self):
        popup = AliasPopup(device_mac=self.device_mac, device_type=self.device_type, main_app=self.main_app)
        popup.open()

class CYTApp(App):
    theme_colors = {
        "background": (0.05, 0.05, 0.1, 1),
        "text_primary": (0.7, 0.85, 1.0, 1),
        "accent_red": (1, 0.2, 0.2, 1),
        "accent_green": (0.2, 1.0, 0.2, 1),
        "accent_amber": (1, 0.7, 0, 1),
        "accent_purple": (0.8, 0.4, 1.0, 1)
    }

    def build(self):
        self.load_settings()
        try:
            watchlist_manager.initialize_database()
        except DatabaseQueryError as e:
            logging.critical(f"CRITICAL: Could not initialize watchlist DB. Alerts will fail. Error: {e}")
        Clock.schedule_interval(self.start_follower_query, self.INTERVAL_FOLLOWERS)
        Clock.schedule_interval(self.check_watchlist, self.INTERVAL_WATCHLIST)
        Clock.schedule_interval(self.check_for_drones, self.INTERVAL_DRONES)
    
    def load_settings(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            kismet_log_path_pattern = config['paths']['kismet_logs']
            expanded_path = os.path.expanduser(kismet_log_path_pattern)
            if "*" in expanded_path:
                list_of_files = glob.glob(expanded_path)
                if not list_of_files:
                    raise FileNotFoundError(f"No Kismet files found matching pattern: {kismet_log_path_pattern}")
                self.DB_PATH = max(list_of_files, key=os.path.getctime)
                logging.info(f"Using latest Kismet DB: {self.DB_PATH}")
            else:
                self.DB_PATH = expanded_path
                logging.info(f"Using direct Kismet DB path: {self.DB_PATH}")
            self.TIME_WINDOW = config['timing']['time_windows']['recent'] * 60
            check_interval = config['timing']['check_interval']
            self.INTERVAL_FOLLOWERS = check_interval
            self.INTERVAL_WATCHLIST = check_interval
            self.INTERVAL_DRONES = check_interval
            self.LOCATIONS_THRESHOLD = 3
            alert_settings = config.get('alert_settings', {})
            self.DRONE_ALERT_WINDOW = alert_settings.get('drone_time_window_seconds', 300)
            self.WATCHLIST_ALERT_WINDOW = alert_settings.get('watchlist_time_window_seconds', 300)
        except (IOError, KeyError, FileNotFoundError) as e:
            logging.critical(f"Failed to load settings from config.json: {e}")
            self.DB_PATH = "NOT_FOUND"
            self.INTERVAL_FOLLOWERS = 60; self.INTERVAL_WATCHLIST = 60; self.INTERVAL_DRONES = 60
            self.TIME_WINDOW = 300; self.LOCATIONS_THRESHOLD = 3
            self.DRONE_ALERT_WINDOW = 300; self.WATCHLIST_ALERT_WINDOW = 300

    def start_follower_query(self, dt):
        self.root.ids.follower_list.clear_widgets()
        loading_label = Label(text="Querying for followers...", font_size='20sp', color=self.theme_colors['text_primary'])
        self.root.ids.follower_list.add_widget(loading_label)
        anim = Animation(opacity=0.5, duration=0.7) + Animation(opacity=1, duration=0.7); anim.repeat = True; anim.start(loading_label)
        threading.Thread(target=self.run_follower_query_in_background, daemon=True).start()

    def run_follower_query_in_background(self):
        try:
            followers = get_chase_targets(self.DB_PATH, self.TIME_WINDOW, self.LOCATIONS_THRESHOLD)
            Clock.schedule_once(lambda dt: self.update_ui_with_results(followers))
        except (DatabaseNotFound, DatabaseQueryError) as e:
            logging.error(f"Follower query failed: {e}")
            Clock.schedule_once(lambda dt, exception=e: self.update_ui_with_results(exception))

    def update_ui_with_results(self, results):
        follower_list = self.root.ids.follower_list
        if isinstance(results, list) and results:
            try:
                watchlist_macs = watchlist_manager.get_watchlist_macs()
                if watchlist_macs:
                    follower_macs = {row[0] for row in results}
                    confirmed_threats = follower_macs.intersection(watchlist_macs)
                    if confirmed_threats:
                        threat_mac = list(confirmed_threats)[0]
                        alias = watchlist_manager.get_device_alias(threat_mac)
                        self.trigger_confirmed_threat_alert(threat_mac, alias)
            except DatabaseQueryError as e:
                logging.warning(f"Could not cross-reference watchlist for confirmed threats: {e}")
        
        follower_list.clear_widgets()
        if isinstance(results, Exception):
            follower_list.add_widget(Label(text=str(results), font_size='20sp', color=self.theme_colors['accent_red']))
        elif not results:
            follower_list.add_widget(Label(text="No followers detected.", font_size='20sp', color=self.theme_colors['text_primary']))
        else:
            for device in results:
                item = DeviceListItem(device_data=device, main_app=self)
                follower_list.add_widget(item)

    def trigger_confirmed_threat_alert(self, mac, alias):
        alert_bar = self.root.ids.alert_bar
        display_name = f"'{alias}'" if alias else mac
        alert_bar.text = f"!!! {ALERT_TYPE_CONFIRMED}: {display_name} IS FOLLOWING !!!"
        Animation.cancel_all(alert_bar)
        anim = Animation(color=(0.1, 0.1, 0.1, 1), duration=0.5) + \
               Animation(color=self.theme_colors['accent_purple'], duration=0.5)
        anim.repeat = True
        anim.start(alert_bar)

    def reset_alert_bar(self):
        alert_bar = self.root.ids.alert_bar
        Animation.cancel_all(alert_bar)
        alert_bar.text = STATUS_MONITORING
        alert_bar.color = self.theme_colors['accent_green']

    def clear_follower_list(self):
        follower_list = self.root.ids.follower_list
        follower_list.clear_widgets()
        follower_list.add_widget(Label(text="Follower list cleared.", font_size='20sp', color=self.theme_colors['text_primary']))
        logging.info("Follower list cleared by user.")

    def check_for_drones(self, dt):
        alert_bar = self.root.ids.alert_bar
        if ALERT_TYPE_CONFIRMED in alert_bar.text: return
        if ALERT_TYPE_WATCHLIST in alert_bar.text: return
        try:
            drones = watchlist_manager.check_for_drones_seen_recently(self.DB_PATH, self.DRONE_ALERT_WINDOW)
            if drones:
                drone_mac, drone_name = drones[0]
                display_name = drone_name if drone_name else drone_mac
                alert_bar.text = f"!!! {ALERT_TYPE_DRONE} DETECTED: {display_name} !!!"
                alert_bar.color = self.theme_colors['accent_amber']
            elif ALERT_TYPE_DRONE in alert_bar.text:
                self.reset_alert_bar()
        except DatabaseQueryError as e:
            logging.warning(f"Could not check for drones: {e}")

    def check_watchlist(self, dt):
        alert_bar = self.root.ids.alert_bar
        if ALERT_TYPE_CONFIRMED in alert_bar.text: return
        if ALERT_TYPE_DRONE in alert_bar.text: return
        try:
            watchlist = watchlist_manager.get_watchlist_macs()
            if not watchlist:
                if ALERT_TYPE_WATCHLIST in alert_bar.text: self.reset_alert_bar()
                return
            seen_macs = watchlist_manager.check_watchlist_macs_seen_recently(self.DB_PATH, watchlist, self.WATCHLIST_ALERT_WINDOW)
            if seen_macs:
                alias = watchlist_manager.get_device_alias(seen_macs[0])
                alert_bar.text = f"!!! {ALERT_TYPE_WATCHLIST}: '{alias}' DETECTED NEARBY !!!"
                alert_bar.color = self.theme_colors['accent_red']
            elif ALERT_TYPE_WATCHLIST in alert_bar.text:
                self.reset_alert_bar()
        except DatabaseQueryError as e:
            logging.warning(f"Could not check watchlist: {e}")

    def refresh_follower_list(self):
        self.start_follower_query(0)

if __name__ == '__main__':
    CYTApp().run()