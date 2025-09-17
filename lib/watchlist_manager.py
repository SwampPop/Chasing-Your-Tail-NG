import sqlite3
import os
import time
import logging

class DatabaseQueryError(Exception):
    pass

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'watchlist.db')

def initialize_database():
    # ... (this function is unchanged)
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS devices (mac TEXT PRIMARY KEY, alias TEXT NOT NULL, device_type TEXT, notes TEXT)''')
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize watchlist database: {e}")
        raise DatabaseQueryError(f"Failed to initialize watchlist DB: {e}")

def add_or_update_device(mac, alias, device_type, notes=""):
    # ... (this function is unchanged)
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO devices (mac, alias, device_type, notes) VALUES (?, ?, ?, ?)''', (mac, alias, device_type, notes))
            conn.commit()
        logging.info(f"Watchlist Updated: {mac} as '{alias}'")
    except sqlite3.Error as e:
        logging.error(f"Failed to update device {mac} in watchlist: {e}")
        raise DatabaseQueryError(f"Failed to update watchlist: {e}")

def get_watchlist_macs():
    # ... (this function is unchanged)
    if not os.path.exists(db_path): return []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mac FROM devices")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get watchlist MACs: {e}")
        raise DatabaseQueryError(f"Failed to read watchlist: {e}")

def get_device_alias(mac):
    # ... (this function is unchanged)
    if not os.path.exists(db_path): return None
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT alias FROM devices WHERE mac = ?", (mac,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get alias for {mac}: {e}")
        raise DatabaseQueryError(f"Failed to read alias: {e}")

# --- CHANGED: This function now accepts a time_window_seconds parameter ---
def check_watchlist_macs_seen_recently(kismet_db_path, mac_list, time_window_seconds):
    if not mac_list or not os.path.exists(kismet_db_path) or kismet_db_path == "NOT_FOUND":
        return []
    
    placeholders = ','.join('?' for _ in mac_list)
    query = f"SELECT devmac FROM devices WHERE devmac IN ({placeholders}) AND last_time > ?"
    
    try:
        with sqlite3.connect(f'file:{kismet_db_path}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            time_threshold = int(time.time()) - time_window_seconds
            cursor.execute(query, mac_list + [time_threshold])
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error checking watchlist in Kismet DB: {e}")
        raise DatabaseQueryError(f"Failed to check watchlist: {e}")

# --- CHANGED: This function now accepts a time_window_seconds parameter ---
def check_for_drones_seen_recently(kismet_db_path, time_window_seconds):
    if not os.path.exists(kismet_db_path) or kismet_db_path == "NOT_FOUND":
        return []
    
    query = "SELECT devmac, devmac FROM devices WHERE type = 'UAV' AND last_time > ?"
    
    try:
        with sqlite3.connect(f'file:{kismet_db_path}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            time_threshold = int(time.time()) - time_window_seconds
            cursor.execute(query, [time_threshold])
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Database error checking for drones in Kismet DB: {e}")
        raise DatabaseQueryError(f"Failed to check for drones: {e}")