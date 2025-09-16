import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.config import Config
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
import time
import sqlite3
import os
import configparser ### CHANGED ### - Import the config parser library

# Import our custom intelligence manager
from lib import watchlist_manager

### CHANGED ### - Constants for UI strings to prevent typos
ALERT_TYPE_DRONE = "DRONE"
ALERT_TYPE_WATCHLIST = "ALERT"
STATUS_MONITORING = "STATUS: MONITORING"

# --- CORE LOGIC FUNCTIONS ---
def get_chase_targets(db_path, time_window, locations_threshold):
    """
    Queries the Kismet DB to find devices seen at multiple locations within a time window.
    """
    if not os.path.exists(db_path):
        return "DB_NOT_FOUND"
    
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
    try:
        cursor.execute(query, (start_time, locations_threshold))
        results = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error in get_chase_targets: {e}")
        return "DB_ERROR"
    finally:
        conn.close()
    return results

# --- KIVY UI CLASSES ---

class AliasPopup(ModalView):
    """The pop-up window for naming/aliasing a device."""
    def __init__(self, device_mac, device_type, main_app, **kwargs):
        super(AliasPopup, self).__init__(**kwargs)
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = False
        self.device_mac = device_mac
        self.device_type = device_type
        self.main_app = main_app
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=f"Add to Watchlist\nMAC: {self.device_mac}", font_size='18sp'))
        
        self.alias_input = TextInput(hint_text='Enter Alias (e.g., "Gray Honda Civic")', multiline=False)
        layout.add_widget(self.alias_input)
        
        self.notes_input = TextInput(hint_text='Enter notes (optional)')
        layout.add_widget(self.notes_input)

        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        save_button = Button(text="Save")
        save_button.bind(on_press=self.save)
        cancel_button = Button(text="Cancel")
        cancel_button.bind(on_press=self.dismiss)
        
        button_layout.add_widget(save_button)
        button_layout.add_widget(cancel_button)
        layout.add_widget(button_layout)
        
        self.add_widget(layout)

    def save(self, instance):
        alias = self.alias_input.text.strip()
        if alias:
            notes = self.notes_input.text.strip()
            watchlist_manager.add_or_update_device(self.device_mac, alias, self.device_type, notes)
            self.main_app.refresh_follower_list()
            self.dismiss()

class DeviceListItem(BoxLayout):
    """The widget that displays information for a single detected follower."""
    def __init__(self, device_data, main_app, **kwargs):
        super(DeviceListItem, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 10, 10, 10]
        self.spacing = 5
        self.size_hint_y = None
        self.height = 150
        
        self.device_data = device_data
        self.main_app = main_app
        
        mac = device_data[0]
        alias = watchlist_manager.get_device_alias(mac)
        display_name = f"'{alias}'" if alias else mac
        
        self.add_widget(Label(text=f"Device: {display_name}", font_size='16sp'))
        self.add_widget(Label(text=f"Locations Seen: {device_data[1]}"))
        self.add_widget(Label(text=f"Last Seen: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(device_data[2]))}"))

        alias_button = Button(text="Name this Device", size_hint_y=None, height=40)
        alias_button.bind(on_press=self.show_alias_popup)
        self.add_widget(alias_button)

    def show_alias_popup(self, instance):
        mac = self.device_data[0]
        popup = AliasPopup(device_mac=mac, device_type="Unknown", main_app=self.main_app)
        popup.open()

class CYTApp(App):
    """The main application class that runs everything."""
    def build(self):
        ### CHANGED ### - Load settings from the config file
        self.load_settings()
        
        # --- Kivy Window Setup ---
        Config.set('graphics', 'width', '800')
        Config.set('graphics', 'height', '480')
        
        # --- Main Layout Construction ---
        self.main_layout = BoxLayout(orientation='vertical')
        
        self.alert_bar = Label(text=STATUS_MONITORING, size_hint_y=0.1, color=(0, 1, 0, 1))
        self.alert_bar.font_size = '20sp'
        with self.alert_bar.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.alert_rect = Rectangle(size=self.alert_bar.size, pos=self.alert_bar.pos)
        self.alert_bar.bind(size=self._update_rect, pos=self._update_rect)
        self.main_layout.add_widget(self.alert_bar)
        
        self.scroll_view = ScrollView()
        self.follower_list = BoxLayout(orientation='vertical', size_hint_y=None)
        self.follower_list.bind(minimum_height=self.follower_list.setter('height'))
        self.scroll_view.add_widget(self.follower_list)
        self.main_layout.add_widget(self.scroll_view)
        
        # --- Initialize and Schedule Background Tasks ---
        watchlist_manager.initialize_database()
        
        ### CHANGED ### - Use settings from config file for scheduling
        Clock.schedule_interval(self.update_followers, self.INTERVAL_FOLLOWERS)
        Clock.schedule_interval(self.check_watchlist, self.INTERVAL_WATCHLIST)
        Clock.schedule_interval(self.check_for_drones, self.INTERVAL_DRONES)
        
        return self.main_layout

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

    def update_followers(self, dt):
        """Periodically checks for and displays any new followers."""
        # Note: For very long lists, clearing and re-adding all widgets can
        # cause a flicker. A more advanced method would be to compare the
        # new list to the old one and only change the widgets that are new or removed.
        followers = get_chase_targets(self.DB_PATH, self.TIME_WINDOW, self.LOCATIONS_THRESHOLD)
        
        self.follower_list.clear_widgets()
        
        if isinstance(followers, str):
            self.follower_list.add_widget(Label(text=f"ERROR: {followers}", font_size='20sp', color=(1,0,0,1)))
        elif not followers:
            self.follower_list.add_widget(Label(text="No followers detected.", font_size='20sp'))
        else:
            for device in followers:
                self.follower_list.add_widget(DeviceListItem(device_data=device, main_app=self))

    def _update_rect(self, instance, value):
        """Helper function to keep the alert bar background sized correctly."""
        self.alert_rect.pos = instance.pos
        self.alert_rect.size = instance.size

    ### CHANGED ### - New method to handle resetting the alert bar
    def reset_alert_bar(self):
        """Resets the alert bar to the default monitoring status."""
        self.alert_bar.text = STATUS_MONITORING
        self.alert_bar.color = (0, 1, 0, 1)

    def check_for_drones(self, dt):
        """High-priority check for any device Kismet has identified as a UAV."""
        # Don't override a watchlist alert unless it's a drone
        if ALERT_TYPE_WATCHLIST in self.alert_bar.text:
            return
        
        drones = watchlist_manager.check_for_drones_seen_recently(self.DB_PATH)
        if drones:
            drone_mac, drone_name = drones[0]
            display_name = drone_name if drone_name else drone_mac
            self.alert_bar.text = f"!!! {ALERT_TYPE_DRONE} DETECTED: {display_name} !!!"
            self.alert_bar.color = (1, 0.5, 0, 1) # Orange
        else:
            # Only reset if the current alert is a DRONE alert
            if ALERT_TYPE_DRONE in self.alert_bar.text:
                self.reset_alert_bar() ### CHANGED ### - Call the new refactored method

    def check_watchlist(self, dt):
        """Standard check for any device on our manually-created watchlist."""
        # Drone alert always takes priority
        if ALERT_TYPE_DRONE in self.alert_bar.text:
            return
        
        watchlist = watchlist_manager.get_watchlist_macs()
        if not watchlist:
            if ALERT_TYPE_WATCHLIST in self.alert_bar.text:
                self.reset_alert_bar() ### CHANGED ###
            return
        
        seen_macs = watchlist_manager.check_watchlist_macs_seen_recently(self.DB_PATH, watchlist)
        if seen_macs:
            alias = watchlist_manager.get_device_alias(seen_macs[0])
            self.alert_bar.text = f"!!! {ALERT_TYPE_WATCHLIST}: '{alias}' DETECTED NEARBY !!!"
            self.alert_bar.color = (1, 0, 0, 1) # Red
        else:
            # Only reset if the current alert is a WATCHLIST alert
            if ALERT_TYPE_WATCHLIST in self.alert_bar.text:
                self.reset_alert_bar() ### CHANGED ###

    def refresh_follower_list(self):
        """A helper to manually trigger a refresh of the follower list."""
        self.update_followers(0)

if __name__ == '__main__':
    CYTApp().run()