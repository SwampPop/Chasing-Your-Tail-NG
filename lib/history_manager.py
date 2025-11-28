import sqlite3
import os
import logging
from typing import List, Dict, Any
from lib.database_utils import HISTORY_SCHEMA, safe_db_connection

# --- DATABASE SETUP ---
db_path = HISTORY_SCHEMA.db_path


def initialize_history_database() -> None:
    """
    Creates the cyt_history.db file and its tables if they don't exist.
    Uses centralized schema definition from database_utils.
    """
    HISTORY_SCHEMA.initialize()


def archive_appearances(appearance_data: List[Dict[str, Any]]) -> None:
    """
    Takes a list of device appearance data and writes it to the history database.
    Uses safe database connection from database_utils.
    """
    if not appearance_data:
        return

    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()

            for appearance in appearance_data:
                mac = appearance['mac']
                timestamp = appearance['timestamp']
                location_id = appearance['location_id']

                # Insert device if not exists
                cursor.execute('''
                    INSERT OR IGNORE INTO devices (mac, first_seen, last_seen)
                    VALUES (?, ?, ?)
                ''', (mac, timestamp, timestamp))

                # Update last_seen time
                cursor.execute('''
                    UPDATE devices SET last_seen = MAX(last_seen, ?) WHERE mac = ?
                ''', (timestamp, mac))

                # Record appearance
                cursor.execute('''
                    INSERT INTO appearances (mac, timestamp, location_id)
                    VALUES (?, ?, ?)
                ''', (mac, timestamp, location_id))

            logging.info(
                f"Successfully archived {len(appearance_data)} appearances to the history database.")

    except sqlite3.Error as e:
        logging.error(f"Failed to archive appearances: {e}")
        raise
