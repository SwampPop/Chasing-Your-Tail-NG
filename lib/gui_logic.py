"""
Business logic for the CYT GUI.
"""
import os
import platform
import time
import sqlite3
import logging
import glob
from secure_database import SecureKismetDB
from lib import watchlist_manager
from lib.watchlist_manager import DatabaseQueryError


class DatabaseNotFound(Exception):
    pass


def get_kismet_logs_path(config):
    """Return the correct Kismet logs path for the current platform.

    Uses 'kismet_logs_vm' on Linux (Kali VM), 'kismet_logs' on macOS.
    """
    paths = config.get('paths', {})
    if platform.system() == 'Linux':
        return paths.get('kismet_logs_vm') or paths.get('kismet_logs', '')
    return paths.get('kismet_logs', '')


def resolve_db_glob(path_pattern):
    expanded_path = os.path.expanduser(path_pattern)
    if os.path.isdir(expanded_path):
        expanded_path = os.path.join(expanded_path, "*.kismet")
    return expanded_path


def find_latest_db_path(path_pattern, fallback_path=None):
    """
    Resolve the latest Kismet DB path from a file or glob pattern.

    Returns a tuple of:
      (db_path_or_NOT_FOUND, resolved_glob_pattern)
    """
    resolved_glob = resolve_db_glob(path_pattern)
    list_of_files = glob.glob(resolved_glob)
    if list_of_files:
        return max(list_of_files, key=os.path.getmtime), resolved_glob

    if fallback_path and os.path.exists(fallback_path):
        return fallback_path, resolved_glob

    return "NOT_FOUND", resolved_glob


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


def get_live_device_feed(db_path, time_window=120):
    """
    Fetches all recently seen devices for the live dashboard feed.
    """
    if not os.path.exists(db_path) or db_path == "NOT_FOUND":
        return []

    try:
        with SecureKismetDB(db_path) as db:
            return db.get_live_devices(time_window)
    except Exception as e:
        logging.error(f"Error fetching live device feed: {e}")
        return []


# ------------------------------------------------------------------
# Dashboard queries
# ------------------------------------------------------------------

def get_dashboard_stats(db_path, freshness_minutes=5):
    """Gather statistics for the GUI dashboard.

    Returns a dict with db_status, device_count, last_seen_time,
    watchlist_count, db_file, db_age_minutes, and db_freshness.
    """
    stats = {
        'db_status': 'DISCONNECTED',
        'device_count': 0,
        'last_seen_time': 'N/A',
        'watchlist_count': 0,
        'db_file': os.path.basename(db_path) if db_path else 'None',
        'db_age_minutes': None,
        'db_freshness': 'UNKNOWN',
    }

    # Watchlist count (independent of Kismet DB)
    try:
        stats['watchlist_count'] = len(watchlist_manager.get_watchlist_macs())
    except Exception:
        pass

    if not db_path or db_path == "NOT_FOUND" or not os.path.exists(db_path):
        return stats

    try:
        try:
            age_seconds = time.time() - os.path.getmtime(db_path)
            stats['db_age_minutes'] = int(age_seconds // 60)
            stats['db_freshness'] = (
                'ACTIVE' if stats['db_age_minutes'] <= freshness_minutes
                else 'STALE'
            )
        except OSError:
            stats['db_freshness'] = 'UNKNOWN'

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
        stats['db_freshness'] = 'ERROR'

    return stats


def get_dashboard_health_tone(stats):
    """Return a normalized health tone for dashboard presentation."""
    status = stats.get('db_status', 'DISCONNECTED')
    freshness = stats.get('db_freshness', 'UNKNOWN')

    if status == 'CONNECTED' and freshness == 'ACTIVE':
        return 'healthy'
    if status == 'CONNECTED' and freshness in ('STALE', 'UNKNOWN'):
        return 'warning'
    return 'error'


def get_dashboard_health_summary(stats):
    """Return a concise operator-facing health summary."""
    tone = get_dashboard_health_tone(stats)
    status = stats.get('db_status', 'DISCONNECTED')

    if tone == 'healthy':
        return 'Telemetry Healthy'
    if tone == 'warning':
        return 'Telemetry Stale'
    if isinstance(status, str) and 'ERROR' in status:
        return 'Database Error'
    return 'Telemetry Offline'


def get_dashboard_health_detail(stats):
    """Return detailed operator-facing health context."""
    status = stats.get('db_status', 'DISCONNECTED')
    freshness = stats.get('db_freshness', 'UNKNOWN')
    age = stats.get('db_age_minutes')
    db_file = stats.get('db_file', 'None')
    summary = get_dashboard_health_summary(stats)

    if summary == 'Telemetry Healthy':
        if age is None:
            return f"{db_file} is connected and feeding live telemetry."
        return f"{db_file} is connected and updated {age} min ago."

    if summary == 'Telemetry Stale':
        if age is None or freshness == 'UNKNOWN':
            return f"{db_file} is connected, but freshness could not be confirmed."
        return f"{db_file} is connected, but telemetry is {age} min old."

    if summary == 'Database Error':
        if isinstance(status, str) and len(status) > 90:
            return f"{status[:87]}..."
        return str(status)

    return "No active Kismet database is available for live telemetry."


def get_dashboard_health_label(stats):
    """Return a short uppercase status label for compact dashboards."""
    tone = get_dashboard_health_tone(stats)
    status = stats.get('db_status', 'DISCONNECTED')

    if tone == 'healthy':
        return 'HEALTHY'
    if tone == 'warning':
        return 'STALE'
    if isinstance(status, str) and 'ERROR' in status:
        return 'ERROR'
    return 'OFFLINE'
