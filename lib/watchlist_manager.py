import sqlite3
import os
import time
import logging
from typing import List, Optional
from secure_database import SecureKismetDB
from lib.database_utils import WATCHLIST_SCHEMA, safe_db_connection


class DatabaseQueryError(Exception):
    pass


db_path = WATCHLIST_SCHEMA.db_path


def initialize_database() -> None:
    """
    Initialize the watchlist database with required schema.
    Uses centralized schema definition from database_utils.
    """
    try:
        WATCHLIST_SCHEMA.initialize()
    except Exception as e:
        logging.error(f"Failed to initialize watchlist database: {e}")
        raise DatabaseQueryError(f"Failed to initialize watchlist DB: {e}") from e


def add_or_update_device(mac: str, alias: str, device_type: str, notes: str = "") -> None:
    """Add or update a device in the watchlist with alias and notes."""
    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO devices (mac, alias, device_type, notes) VALUES (?, ?, ?, ?)''',
                           (mac, alias, device_type, notes))
        logging.info(f"Watchlist Updated: {mac} as '{alias}'")
    except sqlite3.Error as e:
        logging.error(f"Failed to update device {mac} in watchlist: {e}")
        raise DatabaseQueryError(f"Failed to update watchlist: {e}") from e


def get_watchlist_macs() -> List[str]:
    """Get all MAC addresses from the watchlist."""
    if not os.path.exists(db_path):
        return []
    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mac FROM devices")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get watchlist MACs: {e}")
        raise DatabaseQueryError(f"Failed to read watchlist: {e}") from e


def get_device_alias(mac: str) -> Optional[str]:
    """Get the alias for a specific MAC address, or None if not found."""
    if not os.path.exists(db_path):
        return None
    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT alias FROM devices WHERE mac = ?", (mac,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get alias for {mac}: {e}")
        raise DatabaseQueryError(f"Failed to read alias: {e}") from e

# --- CHANGED: This function now accepts a time_window_seconds parameter ---


def check_watchlist_macs_seen_recently(
        kismet_db_path: str,
        mac_list: List[str],
        time_window_seconds: int) -> List[str]:
    """Check which watchlist MACs have been seen recently in Kismet database."""
    if not mac_list or not os.path.exists(kismet_db_path) or kismet_db_path == "NOT_FOUND":
        return []

    try:
        with SecureKismetDB(kismet_db_path) as db:
            return db.check_watchlist_macs_secure(mac_list, time_window_seconds)
    except (sqlite3.Error, RuntimeError) as e:
        logging.error(f"Database error checking watchlist in Kismet DB: {e}")
        raise DatabaseQueryError(f"Failed to check watchlist: {e}") from e


def check_for_drones_seen_recently(
        kismet_db_path: str,
        time_window_seconds: int) -> List[sqlite3.Row]:
    """Check for drone devices (UAVs) seen recently in Kismet database."""
    if not os.path.exists(kismet_db_path) or kismet_db_path == "NOT_FOUND":
        return []

    try:
        with SecureKismetDB(kismet_db_path) as db:
            return db.check_for_drones_secure(time_window_seconds)
    except (sqlite3.Error, RuntimeError) as e:
        logging.error(f"Database error checking for drones in Kismet DB: {e}")
        raise DatabaseQueryError(f"Failed to check for drones: {e}") from e


# --- CRUD DELETE Operations ---


def remove_device(mac: str) -> bool:
    """Remove a device from the watchlist by MAC address.

    Returns True if device was removed, False if device was not found.
    """
    if not os.path.exists(db_path):
        return False
    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM devices WHERE mac = ?", (mac,))
            removed = cursor.rowcount > 0
        if removed:
            logging.info(f"Watchlist: Removed device {mac}")
        else:
            logging.warning(f"Watchlist: Device {mac} not found for removal")
        return removed
    except sqlite3.Error as e:
        logging.error(f"Failed to remove device {mac} from watchlist: {e}")
        raise DatabaseQueryError(f"Failed to remove device: {e}") from e


def remove_all_devices() -> int:
    """Remove all devices from the watchlist.

    Returns the number of devices removed.
    """
    if not os.path.exists(db_path):
        return 0
    try:
        with safe_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM devices")
            count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM devices")
        logging.info(f"Watchlist: Cleared all {count} devices")
        return count
    except sqlite3.Error as e:
        logging.error(f"Failed to clear watchlist: {e}")
        raise DatabaseQueryError(f"Failed to clear watchlist: {e}") from e


# --- CRUD READ Operations (Full Details) ---


def get_all_devices() -> List[dict]:
    """Get all devices from the watchlist with full details.

    Returns list of dicts with keys: mac, alias, device_type, notes
    """
    if not os.path.exists(db_path):
        return []
    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT mac, alias, device_type, notes FROM devices")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all devices from watchlist: {e}")
        raise DatabaseQueryError(f"Failed to read watchlist: {e}") from e


def get_device_details(mac: str) -> Optional[dict]:
    """Get full details for a specific device by MAC address.

    Returns dict with keys: mac, alias, device_type, notes, or None if not found.
    """
    if not os.path.exists(db_path):
        return None
    try:
        with safe_db_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mac, alias, device_type, notes FROM devices WHERE mac = ?",
                (mac,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get device details for {mac}: {e}")
        raise DatabaseQueryError(f"Failed to read device details: {e}") from e
