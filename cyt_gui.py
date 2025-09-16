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
import configparser
import threading
import logging

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import our custom intelligence manager
from lib import watchlist_manager

# --- Constants & Exceptions ---
ALERT_TYPE_DRONE = "DRONE"
ALERT_TYPE_WATCHLIST = "ALERT"
STATUS_MONITORING = "STATUS: MONITORING"

class DatabaseNotFound(Exception):
    pass

class DatabaseQueryError(Exception):
    pass

# --- CORE LOGIC FUNCTION ---
def get_chase_targets(db_path, time_window, locations_threshold):
    """
    Queries the Kismet DB to find devices seen at multiple locations within a time window.
    Raises custom exceptions on failure.
    """
    if not os.path.exists(db_path):
        raise DatabaseNotFound(f"Error: The database file could not be found at '{db_path}'")
    
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        end_time = int(time.time())
        start_time = end_time - time_window
        
        query = """
        SELECT devmac, COUNT(DISTINCT location_uuid) as locations, MAX(last_time) as last_seen
        FROM device_locations
        WHERE last_time > ?
        GROUP BY devmac
        HAVING locations >= ?
        ORDER BY last_seen DESC
        """
        cursor.execute(query, (start_time, locations_threshold))
        results = cursor.fetchall()
        return results
    except sqlite3.Error as e:
        # Log the detailed error before raising the custom exception
        logging.error(f"A database error occurred: {e}")
        raise DatabaseQueryError(f"A database error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# --- KIVY UI CLASSES ---

class AliasPopup(ModalView):
    device_mac = StringProperty('')
    device_type = StringProperty('')
    main_app = ObjectProperty(None)

    def save(self, alias, notes):
        alias = alias.strip()
        if alias:
            notes = notes.strip()
            watchlist_manager.add_or_update_device(self.device_mac, alias, self.device_type, notes)
            self.main_app.refresh_follower_list()
            self.dismiss()

class DeviceListItem(BoxLayout):
    # Kivy properties that are automatically linked to the .kv file
    device_mac = StringProperty('')
    device_alias = StringProperty('')
    locations_seen = StringProperty('')
    last_seen = StringProperty('')
    main_app = ObjectProperty(None)
    
    def __init__(self, device_data, **kwargs):
        super().__init__(**kwargs)
        # Populate the properties from the device data upon creation
        self.device_mac = device_data[0]
        self.device_alias = watchlist_manager.get_device_alias(self.device_mac) or ''
        self.locations_seen = str(device_data[1])
        self.last_seen = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(device_data[2]))

    def show_alias_popup(self):
        popup = AliasPopup(device_mac=self.device_mac, device_type="Unknown", main_app=self.main_app)
        popup.open()

class CYTApp(App):
    # Centralized theme colors for easy UI modification
    theme_colors = {
        "background": (0.1, 0.1, 0.1, 1),
        "text_primary": (0.9, 0.9, 0.9, 1),
        "accent_red": (1, 0, 0, 1),
        "accent_green": (0, 1, 0, 1),
        "accent_orange": (1, 0.5, 0, 1)
    }

    def build(self):
        # The .kv file is loaded automatically, so build() is now tiny!
        self.load_settings()
        watchlist_manager.initialize_database()
        
        Clock.schedule_interval(self.start_follower_query, self.INTERVAL_FOLLOWERS)
        Clock.schedule_interval(self.check_watchlist, self.INTERVAL_WATCHLIST)
        Clock.schedule_interval(self.check_for_drones, self.INTERVAL_DRONES)
        
        # Kivy automatically returns the root widget from the .kv file
    
    def start_follower_query(self, dt):
        """Kicks off the follower query process with an animated loading indicator."""
        self.root.ids.follower_list.clear_widgets()
        
        # Create the label that we will animate
        loading_label = Label(text="Querying for followers...", font_size='20sp')
        self.root.ids.follower_list.add_widget(loading_label)
        
        # Define an animation that fades the label's opacity to half, then back to full
        anim = Animation(opacity=0.5, duration=0.7) + Animation(opacity=1, duration=0.7)
        
        # Make the animation loop indefinitely
        anim.repeat = True
        
        # Start the animation on our label
        anim.start(loading_label)
    
        # Start the background thread as before
        threading.Thread(target=self.run_follower_query_in_background, daemon=True).start()

    def run_follower_query_in_background(self):
        """
        This method runs in a separate thread.
        It performs the database query and schedules the UI update on the main thread.
        """
        try:
            followers = get_chase_targets(self.DB_PATH, self.TIME_WINDOW, self.LOCATIONS_THRESHOLD)
            Clock.schedule_once(lambda dt: self.update_ui_with_results(followers))
        except (DatabaseNotFound, DatabaseQueryError) as e:
            logging.error(f"Follower query failed: {e}")
            Clock.schedule_once(lambda dt: self.update_ui_with_results(e))

    def update_ui_with_results(self, results):
        """This method runs on the main thread to safely update the UI."""
        follower_list = self.root.ids.follower_list
        follower_list.clear_widgets()
        
        if isinstance(results, Exception):
            follower_list.add_widget(Label(text=str(results), font_size='20sp', color=self.theme_colors['accent_red']))
        elif not results:
            follower_list.add_widget(Label(text="No followers detected.", font_size='20sp'))
        else:
            for device in results:
                item = DeviceListItem(device_data=device, main_app=self)
                follower_list.add_widget(item)

    def load_settings(self):
        """Loads settings from config.ini into instance variables."""
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.DB_PATH = config.get('Database', 'path')
        self.TIME_WINDOW = config.getint('Analysis', 'time_window')
        self.LOCATIONS_THRESHOLD = config.getint('Analysis', 'locations_threshold')
        self.INTERVAL_FOLLOWERS = config.getint('Intervals', 'followers_check')
        self.INTERVAL_WATCHLIST = config.getint('Intervals', 'watchlist_check')
        self.INTERVAL_DRONES = config.getint('Intervals', 'drone_check')

    def reset_alert_bar(self):
        """Resets the alert bar to the default monitoring status."""
        self.root.ids.alert_bar.text = STATUS_MONITORING
        self.root.ids.alert_bar.color = self.theme_colors['accent_green']

    def check_for_drones(self, dt):
        """High-priority check for any device Kismet has identified as a UAV."""
        alert_bar = self.root.ids.alert_bar
        if ALERT_TYPE_WATCHLIST in alert_bar.text: return
        
        drones = watchlist_manager.check_for_drones_seen_recently(self.DB_PATH)
        if drones:
            drone_mac, drone_name = drones[0]
            display_name = drone_name if drone_name else drone_mac
            alert_bar.text = f"!!! {ALERT_TYPE_DRONE} DETECTED: {display_name} !!!"
            alert_bar.color = self.theme_colors['accent_orange']
        elif ALERT_TYPE_DRONE in alert_bar.text:
            self.reset_alert_bar()

    def check_watchlist(self, dt):
        """Standard check for any device on our manually-created watchlist."""
        alert_bar = self.root.ids.alert_bar
        if ALERT_TYPE_DRONE in alert_bar.text: return
        
        watchlist = watchlist_manager.get_watchlist_macs()
        if not watchlist:
            if ALERT_TYPE_WATCHLIST in alert_bar.text: self.reset_alert_bar()
            return
        
        seen_macs = watchlist_manager.check_watchlist_macs_seen_recently(self.DB_PATH, watchlist)
        if seen_macs:
            alias = watchlist_manager.get_device_alias(seen_macs[0])
            alert_bar.text = f"!!! {ALERT_TYPE_WATCHLIST}: '{alias}' DETECTED NEARBY !!!"
            alert_bar.color = self.theme_colors['accent_red']
        elif ALERT_TYPE_WATCHLIST in alert_bar.text:
            self.reset_alert_bar()

    def refresh_follower_list(self):
        """A helper to manually trigger a refresh of the follower list."""
        self.start_follower_query(0)

if __name__ == '__main__':
    CYTApp().run()