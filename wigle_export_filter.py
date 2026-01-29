#!/usr/bin/env python3
"""
WiGLE Export Filter - Create filtered Kismet export excluding your networks
Removes specified MACs/SSIDs before uploading to WiGLE
"""

import sqlite3
import json
import csv
import os
from datetime import datetime
from pathlib import Path

class WiGLEExportFilter:
    def __init__(self, kismet_dir="/home/parallels/CYT/logs/kismet"):
        self.kismet_dir = Path(kismet_dir)
    
    def get_latest_db(self):
        dbs = sorted(self.kismet_dir.glob("*.kismet"), key=os.path.getmtime, reverse=True)
        return dbs[0] if dbs else None
    
    def export_filtered_csv(self, output_file, exclude_macs=None, exclude_ssids=None):
        """
        Export Kismet data to WiGLE-compatible CSV, excluding specified networks
        
        WiGLE CSV format:
        MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,CurrentLatitude,CurrentLongitude,Type
        """
        exclude_macs = set(m.upper() for m in (exclude_macs or []))
        exclude_ssids = set(exclude_ssids or [])
        
        db_path = self.get_latest_db()
        if not db_path:
            print("No Kismet database found")
            return 0
        
        print(f"Reading from: {db_path}")
        print(f"Excluding {len(exclude_macs)} MACs, {len(exclude_ssids)} SSIDs")
        
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.execute("""
            SELECT devmac, device, first_time, last_time, strongest_signal
            FROM devices
            WHERE type LIKE '%AP%'
        """)
        
        exported = 0
        excluded = 0
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # WiGLE header
            writer.writerow(['WigleWifi-1.4', 'appRelease=CYT', 'model=Kismet', 
                           'release=1.0', 'device=CYT', 'display=none', 
                           'board=none', 'brand=CYT'])
            writer.writerow(['MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 
                           'RSSI', 'CurrentLatitude', 'CurrentLongitude', 
                           'AltitudeMeters', 'AccuracyMeters', 'Type'])
            
            for row in cursor:
                mac, device_json, first_time, last_time, signal = row
                mac_upper = mac.upper()
                
                # Parse device JSON for SSID
                try:
                    device = json.loads(device_json) if device_json else {}
                    ssid = device.get('dot11.device', {}).get(
                        'dot11.device.last_beaconed_ssid_record', {}).get(
                        'dot11.advertisedssid', {}).get('ssid', '')
                except:
                    ssid = ''
                
                # Check exclusions
                if mac_upper in exclude_macs:
                    excluded += 1
                    continue
                if ssid and ssid in exclude_ssids:
                    excluded += 1
                    continue
                
                # Format for WiGLE
                first_seen = datetime.fromtimestamp(first_time).strftime('%Y-%m-%d %H:%M:%S')
                
                # Get channel and auth from device data
                try:
                    channel = device.get('kismet.device.base.channel', '0')
                    crypt = device.get('kismet.device.base.crypt', 'Unknown')
                except:
                    channel = '0'
                    crypt = 'Unknown'
                
                # WiGLE row (no GPS data - WiGLE will skip these but still increases contribution count)
                writer.writerow([
                    mac_upper, ssid or '', crypt, first_seen, channel,
                    signal or -100, 0.0, 0.0, 0, 0, 'WIFI'
                ])
                exported += 1
        
        conn.close()
        print(f"\nExported: {exported} networks")
        print(f"Excluded: {excluded} networks")
        print(f"Output: {output_file}")
        
        return exported


def main():
    import sys
    
    print("=" * 60)
    print("  WiGLE Export Filter")
    print("  Exports Kismet data EXCLUDING your personal networks")
    print("=" * 60)
    
    # Default exclusions - ADD YOUR NETWORKS HERE
    exclude_macs = [
        # Add your router MACs here:
        # "AA:BB:CC:DD:EE:FF",
    ]
    
    exclude_ssids = [
        # Add your SSIDs here:
        # "MyHomeNetwork",
        # "MyNetwork_5G",
    ]
    
    print("\nCurrent exclusions:")
    print(f"  MACs: {exclude_macs or 'None configured'}")
    print(f"  SSIDs: {exclude_ssids or 'None configured'}")
    print("\nEdit this script to add your networks to exclude_macs/exclude_ssids")
    
    output = "wigle_export_filtered.csv"
    
    exporter = WiGLEExportFilter()
    exporter.export_filtered_csv(output, exclude_macs, exclude_ssids)
    
    print(f"\nUpload {output} to https://wigle.net/uploads")


if __name__ == "__main__":
    main()
