#!/usr/bin/env python3
"""
OSINT Correlator - Correlate device appearances to identify patterns
"""

import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

class OSINTCorrelator:
    def __init__(self, kismet_dir="/home/parallels/CYT/logs/kismet"):
        self.kismet_dir = Path(kismet_dir)
    
    def get_all_databases(self):
        """Get all Kismet databases sorted by time"""
        return sorted(self.kismet_dir.glob("*.kismet"), key=os.path.getmtime)
    
    def find_device_across_sessions(self, target_mac):
        """Track a device across all capture sessions"""
        target_mac = target_mac.upper()
        sightings = []
        
        for db_path in self.get_all_databases():
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cursor = conn.execute("""
                    SELECT first_time, last_time, strongest_signal
                    FROM devices WHERE UPPER(devmac) = ?
                """, (target_mac,))
                row = cursor.fetchone()
                if row:
                    sightings.append({
                        'database': db_path.name,
                        'first_seen': datetime.fromtimestamp(row[0]),
                        'last_seen': datetime.fromtimestamp(row[1]),
                        'signal': row[2]
                    })
                conn.close()
            except Exception as e:
                pass
        
        return sightings
    
    def find_correlated_devices(self, target_mac, time_window_seconds=120):
        """Find devices that appeared around the same time as target"""
        target_mac = target_mac.upper()
        correlated = defaultdict(list)
        
        for db_path in self.get_all_databases():
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                
                # Get target device times
                cursor = conn.execute("""
                    SELECT first_time, last_time FROM devices WHERE UPPER(devmac) = ?
                """, (target_mac,))
                target_row = cursor.fetchone()
                
                if target_row:
                    target_first = target_row[0]
                    target_last = target_row[1]
                    
                    # Find other devices appearing in same time window
                    cursor = conn.execute("""
                        SELECT devmac, first_time, last_time, 
                               json_extract(device, '$.kismet.device.base.manuf') as manuf,
                               type
                        FROM devices 
                        WHERE UPPER(devmac) != ?
                          AND (
                              (first_time BETWEEN ? AND ?) OR
                              (last_time BETWEEN ? AND ?)
                          )
                        ORDER BY ABS(first_time - ?)
                    """, (target_mac, 
                          target_first - time_window_seconds, target_last + time_window_seconds,
                          target_first - time_window_seconds, target_last + time_window_seconds,
                          target_first))
                    
                    for row in cursor.fetchall():
                        mac, first_t, last_t, manuf, dev_type = row
                        time_diff = abs(first_t - target_first)
                        correlated[mac].append({
                            'database': db_path.name,
                            'time_diff_seconds': time_diff,
                            'manufacturer': manuf,
                            'type': dev_type,
                            'first_seen': datetime.fromtimestamp(first_t).strftime('%H:%M:%S'),
                        })
                
                conn.close()
            except Exception as e:
                pass
        
        # Sort by frequency of correlation
        return dict(sorted(correlated.items(), key=lambda x: len(x[1]), reverse=True))
    
    def find_network_clients(self, bssid):
        """Find all devices that connected to a specific network"""
        bssid = bssid.upper()
        clients = []
        
        for db_path in self.get_all_databases():
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cursor = conn.execute("""
                    SELECT devmac, 
                           json_extract(device, '$.dot11.device.last_bssid') as connected_to,
                           json_extract(device, '$.kismet.device.base.manuf') as manuf,
                           first_time, last_time
                    FROM devices
                    WHERE json_extract(device, '$.dot11.device.last_bssid') = ?
                """, (bssid,))
                
                for row in cursor.fetchall():
                    clients.append({
                        'mac': row[0],
                        'manufacturer': row[2],
                        'first_seen': datetime.fromtimestamp(row[3]).strftime('%Y-%m-%d %H:%M:%S'),
                        'last_seen': datetime.fromtimestamp(row[4]).strftime('%Y-%m-%d %H:%M:%S'),
                        'database': db_path.name
                    })
                conn.close()
            except Exception:
                pass
        
        return clients


def main():
    import sys
    correlator = OSINTCorrelator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 osint_correlator.py track <MAC>        - Track device across sessions")
        print("  python3 osint_correlator.py correlate <MAC>    - Find correlated devices")
        print("  python3 osint_correlator.py clients <BSSID>    - Find network clients")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "track" and len(sys.argv) > 2:
        mac = sys.argv[2]
        print(f"\n=== Tracking {mac} across all sessions ===\n")
        sightings = correlator.find_device_across_sessions(mac)
        for s in sightings:
            print(f"  {s['database']}: {s['first_seen']} - {s['last_seen']} ({s['signal']} dBm)")
        print(f"\nTotal sightings: {len(sightings)}")
    
    elif cmd == "correlate" and len(sys.argv) > 2:
        mac = sys.argv[2]
        print(f"\n=== Devices correlated with {mac} ===\n")
        correlated = correlator.find_correlated_devices(mac)
        for mac, appearances in list(correlated.items())[:15]:
            print(f"  {mac}: appeared {len(appearances)}x near target")
            for a in appearances[:2]:
                print(f"    - {a['first_seen']} ({a['time_diff_seconds']}s diff) - {a['type']} {a['manufacturer'] or ''}")
    
    elif cmd == "clients" and len(sys.argv) > 2:
        bssid = sys.argv[2]
        print(f"\n=== Clients of network {bssid} ===\n")
        clients = correlator.find_network_clients(bssid)
        for c in clients:
            print(f"  {c['mac']}: {c['manufacturer'] or 'Unknown'}")
            print(f"    Seen: {c['first_seen']} - {c['last_seen']}")


if __name__ == "__main__":
    main()
