"""
Business logic for the CYT GUI.
"""
import os
import time
import sqlite3
import logging
from secure_database import SecureKismetDB
from lib import watchlist_manager
from lib.watchlist_manager import DatabaseQueryError


class DatabaseNotFound(Exception):
    pass


def get_chase_targets(db_path, time_window, locations_threshold):
    if not os.path.exists(db_path) or db_path == "NOT_FOUND":
        raise DatabaseNotFound(
            f"Error: The database file could not be found at '{db_path}'")
    try:
        with SecureKismetDB(db_path) as db:
            return db.get_chase_targets_secure(time_window, locations_threshold)
    except (sqlite3.Error, RuntimeError) as e:
        logging.error(f"A database error occurred in get_chase_targets: {e}")
        raise DatabaseQueryError(
            f"A database error occurred in get_chase_targets: {e}")


def find_confirmed_threats(follower_results, watchlist_macs):
    """
    Cross-references follower results with the watchlist to find confirmed threats.
    """
    if not follower_results or not watchlist_macs:
        return None

    follower_macs = {row[0] for row in follower_results}
    confirmed_threats = follower_macs.intersection(watchlist_macs)

    if confirmed_threats:
        return list(confirmed_threats)[0]
    return None


def run_drone_check(db_path, time_window):
    """
    Checks for drones seen recently.
    """
    try:
        return watchlist_manager.check_for_drones_seen_recently(db_path, time_window)
    except DatabaseQueryError as e:
        logging.warning(f"Could not check for drones: {e}")
        return None


def run_watchlist_check(db_path, watchlist_macs, time_window):
    """
    Checks for watchlist MACs seen recently.
    """
    try:
        return watchlist_manager.check_watchlist_macs_seen_recently(db_path, watchlist_macs, time_window)
    except DatabaseQueryError as e:
        logging.warning(f"Could not check watchlist: {e}")
        return None


# ------------------------------------------------------------------
# Dashboard queries
# ------------------------------------------------------------------

def get_dashboard_stats(db_path):
    """Gather statistics for the GUI dashboard.

    Returns a dict with db_status, device_count, last_seen_time,
    watchlist_count, and db_file.
    """
    stats = {
        'db_status': 'DISCONNECTED',
        'device_count': 0,
        'last_seen_time': 'N/A',
        'watchlist_count': 0,
        'db_file': os.path.basename(db_path) if db_path else 'None',
    }

    # Watchlist count (independent of Kismet DB)
    try:
        stats['watchlist_count'] = len(watchlist_manager.get_watchlist_macs())
    except Exception:
        pass

    if not db_path or db_path == "NOT_FOUND" or not os.path.exists(db_path):
        return stats

    try:
        with SecureKismetDB(db_path) as db:
            # Total device count
            rows = db.execute_safe_query(
                "SELECT COUNT(*) as cnt FROM devices")
            stats['device_count'] = rows[0]['cnt'] if rows else 0

            # Most recent device timestamp
            rows = db.execute_safe_query(
                "SELECT MAX(last_time) as latest FROM devices")
            if rows and rows[0]['latest']:
                ts = rows[0]['latest']
                stats['last_seen_time'] = time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime(ts))

            stats['db_status'] = 'CONNECTED'
    except Exception as e:
        logging.error(f"Dashboard stats query failed: {e}")
        stats['db_status'] = f'ERROR: {e}'

    return stats
