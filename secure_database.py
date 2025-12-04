"""
Secure database operations - prevents SQL injection
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional, Any, Set, Tuple
from cyt_constants import SystemConstants

logger = logging.getLogger(__name__)


class SecureKismetDB:
    """Secure wrapper for Kismet database operations"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self) -> None:
        """Establish secure, read-only database connection"""
        try:
            # CHANGED: Enforce read-only connection for safety
            uri_path = f"file:{self.db_path}?mode=ro"
            self._connection = sqlite3.connect(
                uri_path, uri=True, timeout=SystemConstants.DB_CONNECTION_TIMEOUT)
            self._connection.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database {self.db_path}: {e}")
            raise

    def close(self) -> None:
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def execute_safe_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute parameterized query safely"""
        if not self._connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(
                f"Database query failed: {query}, params: {params}, error: {e}")
            raise

    # Helper method to consolidate JSON parsing logic
    def _parse_device_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Safely parses the JSON from a device row."""
        try:
            device_data = None
            if row['device']:
                device_data = json.loads(row['device'])

            parsed = {
                'mac': row['devmac'],
                'type': row['type'],
                'device_data': device_data,
                'last_time': row['last_time']
            }

            # Add GPS coordinates if available
            if 'min_lat' in row.keys():
                parsed['lat'] = row['min_lat']
            if 'min_lon' in row.keys():
                parsed['lon'] = row['min_lon']

            return parsed
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                f"Failed to parse device JSON for {row['devmac']}: {e}")
            return None

    def get_devices_by_time_range(
            self, start_time: float,
            end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get devices within time range with proper parameterization.
        UPDATED: Now fetches GPS coordinates.
        """
        if end_time is not None:
            query = ("SELECT devmac, type, device, last_time, min_lat, min_lon FROM devices "
                     "WHERE last_time >= ? AND last_time <= ?")
            params = (start_time, end_time)
        else:
            query = ("SELECT devmac, type, device, last_time, min_lat, min_lon FROM devices "
                     "WHERE last_time >= ?")
            params = (start_time,)

        rows = self.execute_safe_query(query, params)

        # Using the helper method for cleaner code
        devices = [self._parse_device_row(row) for row in rows]
        return [d for d in devices if d is not None]

    def get_mac_addresses_by_time_range(
            self, start_time: float,
            end_time: Optional[float] = None) -> List[str]:
        """Get just MAC addresses for a time range"""
        devices = self.get_devices_by_time_range(start_time, end_time)
        return [device['mac'] for device in devices if device['mac']]

    def get_probe_requests_by_time_range(
            self, start_time: float,
            end_time: Optional[float] = None) -> List[Dict[str, str]]:
        """
        Get probe requests with SSIDs for time range
        """
        devices = self.get_devices_by_time_range(start_time, end_time)

        probes = []
        for device in devices:
            mac = device['mac']
            device_data = device['device_data']

            if not device_data:
                continue

            # Extract probe request SSID safely
            try:
                dot11_device = device_data.get('dot11.device', {})
                if not isinstance(dot11_device, dict):
                    continue

                probe_record = dot11_device.get(
                    'dot11.device.last_probed_ssid_record', {})
                if not isinstance(probe_record, dict):
                    continue

                ssid = probe_record.get('dot11.probedssid.ssid', '')
                if ssid and isinstance(ssid, str):
                    probes.append({
                        'mac': mac,
                        'ssid': ssid,
                        'timestamp': device['last_time']
                    })
            except (KeyError, TypeError, AttributeError) as e:
                logger.debug(f"No probe data for device {mac}: {e}")
                continue

        return probes

    def validate_connection(self) -> bool:
        """Validate database connection and basic structure"""
        try:
            result = self.execute_safe_query(
                "SELECT COUNT(*) as count FROM devices LIMIT 1")
            count = result[0]['count'] if result else 0
            logger.info(f"Database contains {count} devices")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database validation failed: {e}")
            return False

    def get_chase_targets_secure(
            self, time_window: int,
            locations_threshold: int) -> List[sqlite3.Row]:
        """Securely get chase targets from the Kismet database."""
        end_time = int(time.time())
        start_time = end_time - time_window
        query = """
        SELECT
            p.sourcemac as devmac,
            COUNT(DISTINCT p.datasource) as locations,
            MAX(p.ts_sec) as last_seen,
            d.type as device_type
        FROM packets p
        JOIN devices d ON p.sourcemac = d.devmac
        WHERE p.sourcemac IS NOT NULL AND
              p.sourcemac != '00:00:00:00:00:00' AND
              p.ts_sec > ?
        GROUP BY p.sourcemac
        HAVING locations >= ?
        ORDER BY last_seen DESC
        """
        params = (start_time, locations_threshold)
        return self.execute_safe_query(query, params)

    def check_watchlist_macs_secure(
            self, mac_list: List[str],
            time_window_seconds: int) -> List[str]:
        """Securely check for watchlist MACs seen recently."""
        if not mac_list:
            return []

        placeholders = ','.join('?' for _ in mac_list)
        query = (f"SELECT devmac FROM devices WHERE devmac IN ({placeholders}) "
                 f"AND last_time > ?")

        time_threshold = int(time.time()) - time_window_seconds
        params = mac_list + [time_threshold]

        results = self.execute_safe_query(query, tuple(params))
        return [row['devmac'] for row in results]

    def check_for_drones_secure(self, time_window_seconds: int) -> List[sqlite3.Row]:
        """Securely check for drones (UAVs) seen recently."""
        query = "SELECT devmac, type FROM devices WHERE type = 'UAV' AND last_time > ?"
        time_threshold = int(time.time()) - time_window_seconds
        params = (time_threshold,)
        return self.execute_safe_query(query, params)


class SecureTimeWindows:
    """Secure time window management for device tracking"""

    def __init__(self, config: Optional[Dict[str, Any]]):
        self.config = config
        self.time_windows = config.get('timing', {}).get('time_windows', {
            'recent': 5,
            'medium': 10,
            'old': 15,
            'oldest': 20
        })

    def get_time_boundaries(self) -> Dict[str, float]:
        """Calculate secure time boundaries"""
        now = datetime.now()

        boundaries = {}
        for window_name, minutes in self.time_windows.items():
            boundary_time = now - timedelta(minutes=minutes)
            boundaries[f'{window_name}_time'] = time.mktime(
                boundary_time.timetuple())

        # Add current time boundary (2 minutes ago for active scanning)
        current_boundary = now - timedelta(minutes=2)
        boundaries['current_time'] = time.mktime(current_boundary.timetuple())

        return boundaries

    def filter_devices_by_ignore_list(self, devices: List[str], ignore_list: List[str]) -> List[str]:
        """Safely filter devices against ignore list"""
        if not ignore_list:
            return devices

        ignore_set = set(mac.upper() for mac in ignore_list)

        filtered = []
        for device in devices:
            if isinstance(device, str) and device.upper() not in ignore_set:
                filtered.append(device)

        return filtered

    def filter_ssids_by_ignore_list(self, ssids: List[str], ignore_list: List[str]) -> List[str]:
        """Safely filter SSIDs against ignore list"""
        if not ignore_list:
            return ssids

        ignore_set = set(ignore_list)

        filtered = []
        for ssid in ssids:
            if isinstance(ssid, str) and ssid not in ignore_set:
                filtered.append(ssid)

        return filtered


def create_secure_db_connection(db_path: str) -> SecureKismetDB:
    """Factory function to create secure database connection"""
    return SecureKismetDB(db_path)
