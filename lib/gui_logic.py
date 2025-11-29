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
