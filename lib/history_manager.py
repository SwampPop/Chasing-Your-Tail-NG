import sqlite3
import os
import logging
from typing import List, Dict, Any

# --- DATABASE SETUP ---
db_path = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'cyt_history.db')


def initialize_history_database():
    """
    Creates the cyt_history.db file and its tables if they don't exist.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    mac TEXT PRIMARY KEY,
                    first_seen REAL,
                    last_seen REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appearances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac TEXT,
                    timestamp REAL,
                    location_id TEXT,
                    FOREIGN KEY (mac) REFERENCES devices (mac)
                )
            ''')
            conn.commit()
            logging.info("History database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize history database: {e}")
        raise


def archive_appearances(appearance_data: List[Dict[str, Any]]):
    """
    Takes a list of device appearance data and writes it to the history database.
    """
    if not appearance_data:
        return

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            for appearance in appearance_data:
                mac = appearance['mac']
                timestamp = appearance['timestamp']
                location_id = appearance['location_id']

                # CHANGED: Corrected 'IGIGNORE' to 'IGNORE'
                cursor.execute('''
                    INSERT OR IGNORE INTO devices (mac, first_seen, last_seen)
                    VALUES (?, ?, ?)
                ''', (mac, timestamp, timestamp))

                cursor.execute('''
                    UPDATE devices SET last_seen = MAX(last_seen, ?) WHERE mac = ?
                ''', (timestamp, mac))

                cursor.execute('''
                    INSERT INTO appearances (mac, timestamp, location_id)
                    VALUES (?, ?, ?)
                ''', (mac, timestamp, location_id))

            conn.commit()
            logging.info(
                f"Successfully archived {len(appearance_data)} appearances to the history database.")

    except sqlite3.Error as e:
        logging.error(f"Failed to archive appearances: {e}")
