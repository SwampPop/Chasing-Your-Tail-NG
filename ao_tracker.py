#!/usr/bin/env python3
"""
AO Tracker - Area of Operation Device Tracking Module

Tracks device arrivals, departures, and patterns in the monitored area.
Provides analysis of device presence patterns over time.
"""

import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from vendor_lookup import lookup_vendor  # Shared vendor lookup utility

# Configure logging
logger = logging.getLogger(__name__)

# ============ Configuration Constants ============

# Detection thresholds
DEPARTURE_THRESHOLD_SECONDS = 300  # 5 minutes without seeing = departed
ARRIVAL_WINDOW_SECONDS = 60  # Consider device "just arrived" if seen within 60s
PATTERN_WINDOW_SECONDS = 3600  # 1 hour window for pattern analysis

# Pattern classification thresholds (appearances per hour)
PATTERN_CONSTANT_THRESHOLD = 10  # Seen almost every scan
PATTERN_FREQUENT_THRESHOLD = 5
PATTERN_OCCASIONAL_THRESHOLD = 1

# Query limits
MIN_APPEARANCES_FOR_REGULAR = 5
MAX_REGULARS_DISPLAYED = 50
MAX_RECENT_RESULTS = 20


@dataclass
class DeviceEvent:
    """Represents an arrival or departure event."""
    mac: str
    event_type: str  # 'arrival' or 'departure'
    timestamp: float
    signal_strength: int
    vendor: str
    time_in_ao: Optional[float] = None  # seconds, for departures


@dataclass
class AORegular:
    """Represents a device that regularly appears in the AO."""
    mac: str
    vendor: str
    total_appearances: int
    first_seen: float
    last_seen: float
    avg_signal: int
    typical_duration: float  # average time spent in AO per visit
    visits: int  # number of distinct visits
    pattern: str  # 'constant', 'frequent', 'occasional', 'rare'


class AOTracker:
    """Tracks device activity in the Area of Operation."""

    def __init__(self, kismet_db_path: str, history_db_path: str):
        """Initialize the AO Tracker.

        Args:
            kismet_db_path: Path to Kismet SQLite database
            history_db_path: Path to CYT history SQLite database
        """
        self.kismet_db_path = kismet_db_path
        self.history_db_path = history_db_path
        self._device_cache: Dict[str, Dict[str, Any]] = {}
        self._last_scan_time: float = 0
        self._known_devices: Dict[str, float] = {}  # mac -> last_seen timestamp

    @contextmanager
    def _get_kismet_connection(self):
        """Get read-only connection to Kismet database with context manager."""
        conn = None
        try:
            conn = sqlite3.connect(f"file:{self.kismet_db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Kismet database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def _get_history_connection(self):
        """Get connection to CYT history database with context manager."""
        conn = None
        try:
            conn = sqlite3.connect(self.history_db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"History database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_current_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get all devices currently visible (seen within departure threshold)."""
        current_time = time.time()
        cutoff_time = current_time - DEPARTURE_THRESHOLD_SECONDS

        try:
            with self._get_kismet_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT devmac, first_time, last_time, strongest_signal, type
                    FROM devices
                    WHERE last_time > ?
                    ORDER BY last_time DESC
                """, (cutoff_time,))

                devices: Dict[str, Dict[str, Any]] = {}
                for row in cursor.fetchall():
                    mac = row['devmac']
                    devices[mac] = {
                        'mac': mac,
                        'first_time': row['first_time'],
                        'last_time': row['last_time'],
                        'signal': row['strongest_signal'],
                        'type': row['type'],
                        'vendor': lookup_vendor(mac)
                    }

                return devices

        except sqlite3.Error as e:
            logger.error(f"Database error getting current devices: {e}")
            return {}
        except (OSError, IOError) as e:
            logger.error(f"I/O error getting current devices: {e}")
            return {}

    def detect_arrivals_departures(self) -> Tuple[List[DeviceEvent], List[DeviceEvent]]:
        """Detect recent arrivals and departures.

        Returns:
            Tuple of (arrivals, departures) DeviceEvent lists
        """
        current_time = time.time()
        current_devices = self.get_current_devices()

        arrivals: List[DeviceEvent] = []
        departures: List[DeviceEvent] = []

        # Detect arrivals (devices in current scan not in previous known devices)
        for mac, device in current_devices.items():
            if mac not in self._known_devices:
                # New device - arrival
                arrivals.append(DeviceEvent(
                    mac=mac,
                    event_type='arrival',
                    timestamp=device['last_time'],
                    signal_strength=device['signal'],
                    vendor=device['vendor']
                ))
            self._known_devices[mac] = device['last_time']

        # Detect departures (devices in known list not seen recently)
        departed_macs: List[str] = []
        for mac, last_seen in self._known_devices.items():
            if mac not in current_devices:
                time_since_seen = current_time - last_seen
                if time_since_seen > DEPARTURE_THRESHOLD_SECONDS:
                    # Device departed
                    departures.append(DeviceEvent(
                        mac=mac,
                        event_type='departure',
                        timestamp=last_seen,
                        signal_strength=0,
                        vendor=lookup_vendor(mac),
                        time_in_ao=time_since_seen
                    ))
                    departed_macs.append(mac)

        # Remove departed devices from known list
        for mac in departed_macs:
            del self._known_devices[mac]

        self._last_scan_time = current_time
        return arrivals, departures

    def get_recent_activity(self, minutes: int = 30) -> Dict[str, Any]:
        """Get recent arrival/departure activity.

        Args:
            minutes: Time window in minutes to look back

        Returns:
            Dictionary with arrivals, departures, active devices, and summary
        """
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)

        try:
            with self._get_kismet_connection() as conn:
                cursor = conn.cursor()

                # Get devices that appeared in the time window
                cursor.execute("""
                    SELECT devmac, first_time, last_time, strongest_signal, type
                    FROM devices
                    WHERE first_time > ? OR last_time > ?
                    ORDER BY last_time DESC
                """, (cutoff_time, cutoff_time))

                recent_arrivals: List[Dict[str, Any]] = []
                recent_departures: List[Dict[str, Any]] = []
                active_devices: List[Dict[str, Any]] = []

                for row in cursor.fetchall():
                    mac = row['devmac']
                    device: Dict[str, Any] = {
                        'mac': mac,
                        'first_time': row['first_time'],
                        'last_time': row['last_time'],
                        'signal': row['strongest_signal'],
                        'type': row['type'],
                        'vendor': lookup_vendor(mac),
                        'first_time_readable': datetime.fromtimestamp(row['first_time']).strftime('%H:%M:%S'),
                        'last_time_readable': datetime.fromtimestamp(row['last_time']).strftime('%H:%M:%S')
                    }

                    # Categorize based on timing
                    if row['first_time'] > cutoff_time:
                        recent_arrivals.append(device)

                    time_since_seen = current_time - row['last_time']
                    if time_since_seen > DEPARTURE_THRESHOLD_SECONDS:
                        device['time_ago'] = f"{int(time_since_seen / 60)}m ago"
                        recent_departures.append(device)
                    else:
                        device['time_ago'] = f"{int(time_since_seen)}s ago"
                        active_devices.append(device)

                return {
                    'arrivals': recent_arrivals[:MAX_RECENT_RESULTS],
                    'departures': recent_departures[:MAX_RECENT_RESULTS],
                    'active': active_devices,
                    'summary': {
                        'total_arrivals': len(recent_arrivals),
                        'total_departures': len(recent_departures),
                        'currently_active': len(active_devices),
                        'window_minutes': minutes
                    }
                }

        except sqlite3.Error as e:
            logger.error(f"Database error getting recent activity: {e}")
            return {'error': str(e)}
        except (OSError, IOError) as e:
            logger.error(f"I/O error getting recent activity: {e}")
            return {'error': str(e)}

    def get_ao_regulars(self) -> List[Dict[str, Any]]:
        """Get devices that regularly appear in the AO.

        Returns:
            List of regular device dictionaries with appearance patterns
        """
        try:
            with self._get_history_connection() as conn:
                cursor = conn.cursor()

                # Ensure index exists for performance (P2 fix)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_appearances_mac
                    ON appearances(mac)
                """)

                # Get appearance patterns for each device
                cursor.execute(f"""
                    SELECT
                        mac,
                        COUNT(*) as appearance_count,
                        MIN(timestamp) as first_seen,
                        MAX(timestamp) as last_seen
                    FROM appearances
                    GROUP BY mac
                    HAVING appearance_count >= {MIN_APPEARANCES_FOR_REGULAR}
                    ORDER BY appearance_count DESC
                    LIMIT {MAX_REGULARS_DISPLAYED}
                """)

                regulars: List[Dict[str, Any]] = []
                for row in cursor.fetchall():
                    mac = row['mac']
                    appearances = row['appearance_count']
                    first_seen = row['first_seen']
                    last_seen = row['last_seen']

                    # Calculate pattern type
                    total_time = last_seen - first_seen if last_seen > first_seen else 1
                    appearances_per_hour = (appearances / total_time) * 3600

                    pattern = _classify_appearance_pattern(appearances_per_hour)

                    regulars.append({
                        'mac': mac,
                        'vendor': lookup_vendor(mac),
                        'appearances': appearances,
                        'first_seen': datetime.fromtimestamp(first_seen).strftime('%Y-%m-%d %H:%M'),
                        'last_seen': datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M'),
                        'pattern': pattern,
                        'hours_tracked': round(total_time / 3600, 1)
                    })

                return regulars

        except sqlite3.Error as e:
            logger.error(f"Database error getting AO regulars: {e}")
            return []
        except (OSError, IOError) as e:
            logger.error(f"I/O error getting AO regulars: {e}")
            return []


    def get_ao_summary(self) -> Dict[str, Any]:
        """Get a summary of AO activity.

        Returns:
            Dictionary with current device counts and categorization
        """
        current_devices = self.get_current_devices()
        regulars = self.get_ao_regulars()
        recent = self.get_recent_activity(minutes=60)

        # Categorize current devices
        new_devices: List[Dict[str, Any]] = []
        known_devices: List[Dict[str, Any]] = []
        regular_macs = {r['mac'] for r in regulars}

        for mac, device in current_devices.items():
            if mac in regular_macs:
                known_devices.append(device)
            else:
                new_devices.append(device)

        return {
            'timestamp': datetime.now().isoformat(),
            'current_count': len(current_devices),
            'new_devices': sorted(new_devices, key=lambda x: x['signal'], reverse=True)[:10],
            'known_devices': len(known_devices),
            'regulars_count': len(regulars),
            'recent_arrivals': recent.get('summary', {}).get('total_arrivals', 0),
            'recent_departures': recent.get('summary', {}).get('total_departures', 0)
        }


def _classify_appearance_pattern(apps_per_hour: float) -> str:
    """Classify device appearance pattern based on frequency.

    Args:
        apps_per_hour: Number of appearances per hour

    Returns:
        Pattern classification string ('constant', 'frequent', 'occasional', 'rare')
    """
    if apps_per_hour > PATTERN_CONSTANT_THRESHOLD:
        return 'constant'
    elif apps_per_hour > PATTERN_FREQUENT_THRESHOLD:
        return 'frequent'
    elif apps_per_hour > PATTERN_OCCASIONAL_THRESHOLD:
        return 'occasional'
    else:
        return 'rare'


def main():
    """Test the AO tracker."""
    import glob

    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Find Kismet database
    kismet_dbs = glob.glob('/home/parallels/CYT/logs/kismet/*.kismet')
    if not kismet_dbs:
        logger.error("No Kismet database found")
        return

    kismet_db = max(kismet_dbs, key=lambda x: x)  # Most recent
    history_db = '/home/parallels/CYT/cyt_history.db'

    logger.info(f"Using Kismet DB: {kismet_db}")
    logger.info(f"Using History DB: {history_db}")

    tracker = AOTracker(kismet_db, history_db)

    # Get summary
    logger.info("=== AO Summary ===")
    summary = tracker.get_ao_summary()
    logger.info(f"Currently visible: {summary['current_count']} devices")
    logger.info(f"Known regulars: {summary['regulars_count']}")
    logger.info(f"New/unknown devices: {len(summary['new_devices'])}")

    # Get regulars
    logger.info("=== AO Regulars (Top 10) ===")
    regulars = tracker.get_ao_regulars()[:10]
    for r in regulars:
        vendor_short = r['vendor'][:20] if r['vendor'] else 'Unknown'
        logger.info(f"  {r['mac']} ({vendor_short}) - {r['appearances']} appearances, pattern: {r['pattern']}")

    # Get recent activity
    logger.info("=== Recent Activity (30 min) ===")
    recent = tracker.get_recent_activity(minutes=30)
    if 'summary' in recent:
        logger.info(f"Arrivals: {recent['summary']['total_arrivals']}")
        logger.info(f"Departures: {recent['summary']['total_departures']}")
        logger.info(f"Currently active: {recent['summary']['currently_active']}")
    else:
        logger.error(f"Error getting recent activity: {recent.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main()
