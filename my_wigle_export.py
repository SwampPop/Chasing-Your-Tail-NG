#!/usr/bin/env python3
"""
Personal WiGLE Export - Excludes your networks before upload
"""

import sqlite3
import json
import csv
import os
import glob
from datetime import datetime

# === YOUR NETWORKS TO EXCLUDE ===
EXCLUDE_SSIDS = [
    "404th technical application gr",
    "scif access node",
]

EXCLUDE_MACS = [
    "18:A5:FF:B4:DB:FF",  # Your router (2.4GHz)
    "18:A5:D0:BB:DB:FF",  # Your router (5GHz)
    "6C:55:E8:7A:29:7C",  # Strong signal device
    "6C:55:E8:7A:29:80",  # Strong signal device
]
# ================================

def export_filtered():
    # Find latest Kismet DB
    dbs = sorted(glob.glob("logs/kismet/*.kismet"), key=os.path.getmtime, reverse=True)
    if not dbs:
        print("ERROR: No Kismet database found")
        return
    
    db_path = dbs[0]
    print(f"Source: {db_path}")
    print(f"Excluding SSIDs: {EXCLUDE_SSIDS}")
    print(f"Excluding MACs: {len(EXCLUDE_MACS)} addresses")
    
    exclude_macs_upper = set(m.upper() for m in EXCLUDE_MACS)
    exclude_ssids_lower = set(s.lower() for s in EXCLUDE_SSIDS)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT devmac, device, first_time, strongest_signal
        FROM devices
        WHERE type LIKE '%AP%'
    """)
    
    output_file = f"wigle_upload_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    exported = 0
    excluded = 0
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['WigleWifi-1.4', 'appRelease=CYT', 'model=Kismet', 
                        'release=1.0', 'device=CYT', 'display=none', 
                        'board=none', 'brand=CYT'])
        writer.writerow(['MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 
                        'RSSI', 'CurrentLatitude', 'CurrentLongitude', 
                        'AltitudeMeters', 'AccuracyMeters', 'Type'])
        
        for mac, device_json, first_time, signal in cursor:
            mac_upper = mac.upper()
            
            # Skip excluded MACs
            if mac_upper in exclude_macs_upper:
                excluded += 1
                continue
            
            # Parse SSID
            ssid = ""
            channel = "0"
            crypt = "Unknown"
            try:
                d = json.loads(device_json) if device_json else {}
                ssid_map = d.get("dot11.device", {}).get("advertised_ssid_map", {})
                for v in ssid_map.values():
                    ssid = v.get("dot11.advertisedssid.ssid", "")
                    if ssid:
                        break
                channel = str(d.get("kismet.device.base.channel", "0"))
                crypt = d.get("kismet.device.base.crypt", "Unknown")
            except:
                pass
            
            # Skip excluded SSIDs
            if ssid and ssid.lower() in exclude_ssids_lower:
                excluded += 1
                continue
            
            first_seen = datetime.fromtimestamp(first_time).strftime('%Y-%m-%d %H:%M:%S')
            
            writer.writerow([
                mac_upper, ssid, crypt, first_seen, channel,
                signal or -100, 0.0, 0.0, 0, 0, 'WIFI'
            ])
            exported += 1
    
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"EXPORT COMPLETE")
    print(f"{'='*50}")
    print(f"Exported: {exported} networks")
    print(f"Excluded: {excluded} networks (yours)")
    print(f"Output:   {output_file}")
    print(f"\nUpload to: https://wigle.net/uploads")

if __name__ == "__main__":
    export_filtered()
