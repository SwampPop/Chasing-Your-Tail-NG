#!/usr/bin/env python3
"""
AO Tracker - Area of Operation Device Tracking Module

Tracks device arrivals, departures, and patterns in the monitored area.
Provides analysis of device presence patterns over time.
"""

import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict


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

    # Thresholds for detection
    DEPARTURE_THRESHOLD = 300  # 5 minutes without seeing = departed
    ARRIVAL_WINDOW = 60  # Consider device "just arrived" if seen within 60s
    PATTERN_WINDOW = 3600  # 1 hour window for pattern analysis

    def __init__(self, kismet_db_path: str, history_db_path: str):
        self.kismet_db_path = kismet_db_path
        self.history_db_path = history_db_path
        self._device_cache: Dict[str, dict] = {}
        self._last_scan_time = 0
        self._known_devices: Dict[str, float] = {}  # mac -> last_seen timestamp

    def _get_kismet_connection(self) -> sqlite3.Connection:
        """Get read-only connection to Kismet database."""
        conn = sqlite3.connect(f"file:{self.kismet_db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_history_connection(self) -> sqlite3.Connection:
        """Get connection to CYT history database."""
        conn = sqlite3.connect(self.history_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _lookup_vendor(self, mac: str) -> str:
        """Look up vendor from MAC address OUI."""
        try:
            from mac_vendor_lookup import MacLookup
            return MacLookup().lookup(mac)
        except:
            # Check if randomized MAC (local bit set)
            try:
                second_char = mac[1].upper()
                if second_char in ['2', '6', 'A', 'E']:
                    return "Randomized MAC"
            except:
                pass
            return "Unknown"

    def get_current_devices(self) -> Dict[str, dict]:
        """Get all devices currently visible (seen in last 5 minutes)."""
        current_time = time.time()
        cutoff_time = current_time - self.DEPARTURE_THRESHOLD

        try:
            conn = self._get_kismet_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT devmac, first_time, last_time, strongest_signal, type
                FROM devices
                WHERE last_time > ?
                ORDER BY last_time DESC
            """, (cutoff_time,))

            devices = {}
            for row in cursor.fetchall():
                mac = row['devmac']
                devices[mac] = {
                    'mac': mac,
                    'first_time': row['first_time'],
                    'last_time': row['last_time'],
                    'signal': row['strongest_signal'],
                    'type': row['type'],
                    'vendor': self._lookup_vendor(mac)
                }

            conn.close()
            return devices

        except Exception as e:
            print(f"Error getting current devices: {e}")
            return {}

    def detect_arrivals_departures(self) -> Tuple[List[DeviceEvent], List[DeviceEvent]]:
        """Detect recent arrivals and departures."""
        current_time = time.time()
        current_devices = self.get_current_devices()

        arrivals = []
        departures = []

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
        departed_macs = []
        for mac, last_seen in self._known_devices.items():
            if mac not in current_devices:
                time_since_seen = current_time - last_seen
                if time_since_seen > self.DEPARTURE_THRESHOLD:
                    # Device departed
                    departures.append(DeviceEvent(
                        mac=mac,
                        event_type='departure',
                        timestamp=last_seen,
                        signal_strength=0,
                        vendor=self._lookup_vendor(mac),
                        time_in_ao=time_since_seen
                    ))
                    departed_macs.append(mac)

        # Remove departed devices from known list
        for mac in departed_macs:
            del self._known_devices[mac]

        self._last_scan_time = current_time
        return arrivals, departures

    def get_recent_activity(self, minutes: int = 30) -> dict:
        """Get recent arrival/departure activity."""
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)

        try:
            conn = self._get_kismet_connection()
            cursor = conn.cursor()

            # Get devices that appeared in the time window
            cursor.execute("""
                SELECT devmac, first_time, last_time, strongest_signal, type
                FROM devices
                WHERE first_time > ? OR last_time > ?
                ORDER BY last_time DESC
            """, (cutoff_time, cutoff_time))

            recent_arrivals = []
            recent_departures = []
            active_devices = []

            for row in cursor.fetchall():
                mac = row['devmac']
                device = {
                    'mac': mac,
                    'first_time': row['first_time'],
                    'last_time': row['last_time'],
                    'signal': row['strongest_signal'],
                    'type': row['type'],
                    'vendor': self._lookup_vendor(mac),
                    'first_time_readable': datetime.fromtimestamp(row['first_time']).strftime('%H:%M:%S'),
                    'last_time_readable': datetime.fromtimestamp(row['last_time']).strftime('%H:%M:%S')
                }

                # Categorize based on timing
                if row['first_time'] > cutoff_time:
                    recent_arrivals.append(device)

                time_since_seen = current_time - row['last_time']
                if time_since_seen > self.DEPARTURE_THRESHOLD:
                    device['time_ago'] = f"{int(time_since_seen / 60)}m ago"
                    recent_departures.append(device)
                else:
                    device['time_ago'] = f"{int(time_since_seen)}s ago"
                    active_devices.append(device)

            conn.close()

            return {
                'arrivals': recent_arrivals[:20],  # Most recent 20
                'departures': recent_departures[:20],
                'active': active_devices,
                'summary': {
                    'total_arrivals': len(recent_arrivals),
                    'total_departures': len(recent_departures),
                    'currently_active': len(active_devices),
                    'window_minutes': minutes
                }
            }

        except Exception as e:
            print(f"Error getting recent activity: {e}")
            return {'error': str(e)}

    def get_ao_regulars(self) -> List[dict]:
        """Get devices that regularly appear in the AO."""
        try:
            conn = self._get_history_connection()
            cursor = conn.cursor()

            # Get appearance patterns for each device
            cursor.execute("""
                SELECT
                    mac,
                    COUNT(*) as appearance_count,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM appearances
                GROUP BY mac
                HAVING appearance_count >= 5
                ORDER BY appearance_count DESC
                LIMIT 50
            """)

            regulars = []
            for row in cursor.fetchall():
                mac = row['mac']
                appearances = row['appearance_count']
                first_seen = row['first_seen']
                last_seen = row['last_seen']

                # Calculate pattern type
                total_time = last_seen - first_seen if last_seen > first_seen else 1
                appearances_per_hour = (appearances / total_time) * 3600

                if appearances_per_hour > 10:
                    pattern = 'constant'  # Seen almost every scan
                elif appearances_per_hour > 5:
                    pattern = 'frequent'
                elif appearances_per_hour > 1:
                    pattern = 'occasional'
                else:
                    pattern = 'rare'

                regulars.append({
                    'mac': mac,
                    'vendor': self._lookup_vendor(mac),
                    'appearances': appearances,
                    'first_seen': datetime.fromtimestamp(first_seen).strftime('%Y-%m-%d %H:%M'),
                    'last_seen': datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M'),
                    'pattern': pattern,
                    'hours_tracked': round(total_time / 3600, 1)
                })

            conn.close()
            return regulars

        except Exception as e:
            print(f"Error getting AO regulars: {e}")
            return []

    def get_ao_summary(self) -> dict:
        """Get a summary of AO activity."""
        current_devices = self.get_current_devices()
        regulars = self.get_ao_regulars()
        recent = self.get_recent_activity(minutes=60)

        # Categorize current devices
        new_devices = []
        known_devices = []
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


def main():
    """Test the AO tracker."""
    import glob

    # Find Kismet database
    kismet_dbs = glob.glob('/home/parallels/CYT/logs/kismet/*.kismet')
    if not kismet_dbs:
        print("No Kismet database found")
        return

    kismet_db = max(kismet_dbs, key=lambda x: x)  # Most recent
    history_db = '/home/parallels/CYT/cyt_history.db'

    print(f"Using Kismet DB: {kismet_db}")
    print(f"Using History DB: {history_db}")

    tracker = AOTracker(kismet_db, history_db)

    # Get summary
    print("\n=== AO Summary ===")
    summary = tracker.get_ao_summary()
    print(f"Currently visible: {summary['current_count']} devices")
    print(f"Known regulars: {summary['regulars_count']}")
    print(f"New/unknown devices: {len(summary['new_devices'])}")

    # Get regulars
    print("\n=== AO Regulars (Top 10) ===")
    regulars = tracker.get_ao_regulars()[:10]
    for r in regulars:
        print(f"  {r['mac']} ({r['vendor'][:20]}) - {r['appearances']} appearances, pattern: {r['pattern']}")

    # Get recent activity
    print("\n=== Recent Activity (30 min) ===")
    recent = tracker.get_recent_activity(minutes=30)
    print(f"Arrivals: {recent['summary']['total_arrivals']}")
    print(f"Departures: {recent['summary']['total_departures']}")
    print(f"Currently active: {recent['summary']['currently_active']}")


if __name__ == '__main__':
    main()
