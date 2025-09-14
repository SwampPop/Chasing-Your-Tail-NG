import sqlite3
import os
import time

# This file acts as the dedicated "Intelligence Officer" for the project.
# Its only job is to manage the watchlist database and perform specific queries
# against the live Kismet database.

# --- DATABASE SETUP ---
# Define the path for our intelligence database. This places it in the project's root folder.
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'watchlist.db')


# --- V2.0 WATCHLIST & ALIASING PROCEDURES ---

def initialize_database():
    """PROCEDURE: Prepare a new intelligence file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            alias TEXT NOT NULL,
            device_type TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_or_update_device(mac, alias, device_type, notes=""):
    """PROCEDURE: Make a new entry in the intelligence file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO devices (mac, alias, device_type, notes)
        VALUES (?, ?, ?, ?)
    ''', (mac, alias, device_type, notes))
    conn.commit()
    conn.close()
    print(f"Watchlist Updated: {mac} as '{alias}'")

def get_watchlist_macs():
    """PROCEDURE: Get the BOLO list of all suspect IDs."""
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT mac FROM devices")
    macs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return macs

def get_device_alias(mac):
    """PROCEDURE: Get the alias for a specific ID."""
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT alias FROM devices WHERE mac = ?", (mac,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def check_watchlist_macs_seen_recently(kismet_db_path, mac_list, time_window_seconds=30):
    """PROCEDURE: Cross-reference the BOLO list with the live feed."""
    if not mac_list or not os.path.exists(kismet_db_path):
        return []
    conn = sqlite3.connect(f'file:{kismet_db_path}?mode=ro', uri=True)
    cursor = conn.cursor()
    current_timestamp = int(time.time())
    time_threshold = current_timestamp - time_window_seconds
    placeholders = ','.join('?' for _ in mac_list)
    query = f"SELECT devmac FROM devices WHERE devmac IN ({placeholders}) AND last_time > ?"
    try:
        cursor.execute(query, mac_list + [time_threshold])
        seen_macs = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error checking watchlist: {e}")
        seen_macs = []
    finally:
        conn.close()
    return seen_macs


# --- V2.2 DRONE DETECTION PROCEDURE ---

def check_for_drones_seen_recently(kismet_db_path, time_window_seconds=10):
    """PROCEDURE: Code Red - Scan the live feed for any confirmed drones."""
    if not os.path.exists(kismet_db_path):
        return []
    conn = sqlite3.connect(f'file:{kismet_db_path}?mode=ro', uri=True)
    cursor = conn.cursor()
    current_timestamp = int(time.time())
    time_threshold = current_timestamp - time_window_seconds
    # This query looks for the specific device type that Kismet assigns to drones.
    query = "SELECT devmac, commonname FROM devices WHERE type = 'UAV' AND last_time > ?"
    try:
        cursor.execute(query, [time_threshold])
        drones_found = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error in check_for_drones: {e}")
        drones_found = []
    finally:
        conn.close()
    return drones_found

