import sqlite3
import os
import time
import logging

# NEW: Define the custom exception that this module can raise.
class DatabaseQueryError(Exception):
    pass

# --- DATABASE SETUP ---
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'watchlist.db')

# --- V2.0 WATCHLIST & ALIASING PROCEDURES ---

def initialize_database():
    """PROCEDURE: Prepare a new intelligence file."""
    try:
        with sqlite3.connect(db_path) as conn:
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
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize watchlist database: {e}")
        raise DatabaseQueryError(f"Failed to initialize watchlist DB: {e}")

# ... (the rest of this file's content is unchanged) ...
# (add_or_update_device, get_watchlist_macs, etc. all remain the same)