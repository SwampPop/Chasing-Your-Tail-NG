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

# --- CORE LOGIC FUNCTION ---
def get_chase_targets(db_path, time_window, locations_threshold):
    """Queries the Kismet DB for devices meeting follower criteria using the modern schema."""
    if not os.path.exists(db_path) or db_path == "NOT_FOUND":
        raise DatabaseNotFound(f"Error: The database file could not be found at '{db_path}'")
    try:
        with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            end_time = int(time.time())
            start_time = end_time - time_window
            
            # This new query uses the 'packets' table and looks at the datasource as the "location".
            query = """
            SELECT sourcemac as devmac, COUNT(DISTINCT datasource) as locations, MAX(ts_sec) as last_seen
            FROM packets
            WHERE sourcemac IS NOT NULL AND sourcemac != '00:00:00:00:00:00' AND ts_sec > ?
            GROUP BY sourcemac
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
    device_mac = StringProperty('')
    device_type = StringProperty('')
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
    device_mac = StringProperty('')
    device_alias = StringProperty('')
    locations_seen = StringProperty('')
    last_seen = StringProperty('')
    main_app = ObjectProperty(None)
    display_name = StringProperty('')
    
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
        
        if self.device_alias:
            self.display_name = f"'{self.device_alias}'"
        else:
            self.display_name = self.device_mac

    def show_alias_popup(self):
        popup = AliasPopup(device_mac=self.device_mac, device_type="Unknown", main_app=self.main_app)
        popup.open()

class CYTApp(App):
    theme_colors = {
        "background": (0.1, 0.1, 0.1, 1),
        "text_primary": (0.9, 0.9, 0.9, 1),
        "accent_red": (1, 0, 0, 1),
        "accent_green": (0, 1, 0, 1),
        "accent_orange": (1, 0.5, 0, 1)
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
            if "*" in kismet_log_path_pattern:
                list_of_files = glob.glob(os.path.expanduser(kismet_log_path_pattern))
                if not list_of_files:
                    raise FileNotFoundError(f"No Kismet files found matching pattern: {kismet_log_path_pattern}")
                self.DB_PATH = max(list_of_files, key=os.path.getctime)
                logging.info(f"Using latest Kismet DB: {self.DB_PATH}")
            else:
                self.DB_PATH = os.path.expanduser(kismet_log_path_pattern)
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
            self.INTERVAL_FOLLOWERS = 60; self.INTERVAL_WATCHLIST = 60;
            self.INTERVAL_DRONES = 60; self.TIME_WINDOW = 300; self.LOCATIONS_THRESHOLD = 3;
            self.DRONE_ALERT_WINDOW = 300; self.WATCHLIST_ALERT_WINDOW = 300

    def start_follower_query(self, dt):
        self.root.ids.follower_list.clear_widgets()
        loading_label = Label(text="Querying for followers...", font_size='20sp')
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
        follower_list = self.root.ids.follower_list; follower_list.clear_widgets()
        if isinstance(results, Exception):
            follower_list.add_widget(Label(text=str(results), font_size='20sp', color=self.theme_colors['accent_red']))
        elif not results:
            follower_list.add_widget(Label(text="No followers detected.", font_size='20sp'))
        else:
            for device in results:
                item = DeviceListItem(device_data=device, main_app=self)
                follower_list.add_widget(item)

    def reset_alert_bar(self):
        self.root.ids.alert_bar.text = STATUS_MONITORING; self.root.ids.alert_bar.color = self.theme_colors['accent_green']

    def check_for_drones(self, dt):
        alert_bar = self.root.ids.alert_bar
        if ALERT_TYPE_WATCHLIST in alert_bar.text: return
        try:
            drones = watchlist_manager.check_for_drones_seen_recently(self.DB_PATH, self.DRONE_ALERT_WINDOW)
            if drones:
                drone_mac, drone_name = drones[0]
                display_name = drone_name if drone_name else drone_mac
                alert_bar.text = f"!!! {ALERT_TYPE_DRONE} DETECTED: {display_name} !!!"
                alert_bar.color = self.theme_colors['accent_orange']
            elif ALERT_TYPE_DRONE in alert_bar.text:
                self.reset_alert_bar()
        except DatabaseQueryError as e:
            logging.warning(f"Could not check for drones: {e}")

    def check_watchlist(self, dt):
        alert_bar = self.root.ids.alert_bar
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