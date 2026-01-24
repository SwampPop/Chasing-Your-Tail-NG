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


# --- CRUD READ Operations ---


def get_all_devices() -> List[Dict[str, Any]]:
    """Get all devices from the history database with their first/last seen times."""
    if not os.path.exists(db_path):
        return []

    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT mac, first_seen, last_seen
                FROM devices
                ORDER BY last_seen DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all devices: {e}")
        raise


def get_device_details(mac: str) -> Dict[str, Any] | None:
    """Get full details for a specific device including appearance count."""
    if not os.path.exists(db_path):
        return None

    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get device info
            cursor.execute('''
                SELECT mac, first_seen, last_seen
                FROM devices WHERE mac = ?
            ''', (mac,))
            device = cursor.fetchone()

            if not device:
                return None

            result = dict(device)

            # Get appearance count
            cursor.execute('''
                SELECT COUNT(*) as appearance_count
                FROM appearances WHERE mac = ?
            ''', (mac,))
            result['appearance_count'] = cursor.fetchone()[0]

            # Get unique locations
            cursor.execute('''
                SELECT COUNT(DISTINCT location_id) as location_count
                FROM appearances WHERE mac = ?
            ''', (mac,))
            result['location_count'] = cursor.fetchone()[0]

            return result
    except sqlite3.Error as e:
        logging.error(f"Failed to get device details for {mac}: {e}")
        raise


def get_device_appearances(mac: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get appearance history for a specific device."""
    if not os.path.exists(db_path):
        return []

    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT mac, timestamp, location_id
                FROM appearances
                WHERE mac = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (mac, limit))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get appearances for {mac}: {e}")
        raise


def get_recent_appearances(limit: int = 50) -> List[Dict[str, Any]]:
    """Get the most recent appearances across all devices."""
    if not os.path.exists(db_path):
        return []

    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT mac, timestamp, location_id
                FROM appearances
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get recent appearances: {e}")
        raise


def get_appearances_by_location(location_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all appearances at a specific location."""
    if not os.path.exists(db_path):
        return []

    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT mac, timestamp, location_id
                FROM appearances
                WHERE location_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (location_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get appearances for location {location_id}: {e}")
        raise


def get_history_stats() -> Dict[str, Any]:
    """Get overall statistics from the history database."""
    if not os.path.exists(db_path):
        return {'device_count': 0, 'appearance_count': 0, 'location_count': 0}

    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM devices")
            device_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM appearances")
            appearance_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT location_id) FROM appearances")
            location_count = cursor.fetchone()[0]

            return {
                'device_count': device_count,
                'appearance_count': appearance_count,
                'location_count': location_count
            }
    except sqlite3.Error as e:
        logging.error(f"Failed to get history stats: {e}")
        raise
