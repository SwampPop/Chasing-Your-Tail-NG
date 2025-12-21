#!/usr/bin/env python3
"""
Device Investigation Tool for Kismet Captures
Helps categorize devices for ignore list creation

Usage: python3 investigate_devices.py
"""

import sqlite3
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import glob

def find_latest_kismet_db():
    """Find the most recent Kismet database"""
    # Check config.json for path
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            db_path = config['paths']['kismet_logs']

            if os.path.isdir(db_path):
                db_path = os.path.join(db_path, "*.kismet")

            files = glob.glob(db_path)
            if files:
                return max(files, key=os.path.getctime)
    except:
        pass

    print("ERROR: Could not find Kismet database")
    print("Make sure you're running from the CYT directory with config.json")
    sys.exit(1)

def format_timestamp(ts):
    """Convert Unix timestamp to readable date"""
    if ts:
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return "Unknown"

def get_device_type_summary(db_path):
    """Get count of devices by type"""
    print("\n" + "="*70)
    print("DEVICE TYPE SUMMARY")
    print("="*70)

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM devices
            GROUP BY type
            ORDER BY count DESC
        """)

        total = 0
        for row in cursor.fetchall():
            device_type, count = row
            total += count
            print(f"  {device_type:25s} : {count:4d} devices")

        print(f"  {'TOTAL':25s} : {total:4d} devices")

def get_wifi_aps(db_path):
    """Get all WiFi access points (routers)"""
    print("\n" + "="*70)
    print("WIFI ACCESS POINTS (Routers - Likely Static)")
    print("="*70)
    print("\nThese are usually routers. Yours should go in ignore list.")
    print("Neighbors' static routers should also be ignored.\n")

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT devmac, type, last_signal, packets,
                   datetime(first_time, 'unixepoch') as first_seen,
                   datetime(last_time, 'unixepoch') as last_seen
            FROM devices
            WHERE type = 'Wi-Fi AP'
            ORDER BY last_signal DESC
            LIMIT 50
        """)

        print(f"{'MAC Address':<20} {'Signal':<10} {'Packets':<10} {'First Seen':<20} {'Last Seen':<20}")
        print("-" * 100)

        for row in cursor.fetchall():
            mac, dtype, signal, packets, first_seen, last_seen = row
            signal_str = f"{signal} dBm" if signal else "Unknown"

            # Categorization hint
            if signal and signal > -50:
                hint = "← VERY CLOSE (yours or neighbor)"
            elif signal and signal > -70:
                hint = "← NEARBY"
            else:
                hint = "← FAR AWAY"

            print(f"{mac:<20} {signal_str:<10} {packets:<10} {first_seen:<20} {last_seen:<20} {hint}")

def get_wifi_clients(db_path):
    """Get WiFi client devices (phones, laptops, etc.)"""
    print("\n" + "="*70)
    print("WIFI CLIENT DEVICES (Phones, Laptops, IoT - Potentially Mobile)")
    print("="*70)
    print("\nThese could be mobile devices. Unknown ones should NOT be ignored.\n")

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT devmac, min_signal, max_signal, packets,
                   datetime(first_time, 'unixepoch') as first_seen,
                   datetime(last_time, 'unixepoch') as last_seen
            FROM devices
            WHERE type = 'Wi-Fi Device'
            ORDER BY last_time DESC
            LIMIT 50
        """)

        print(f"{'MAC Address':<20} {'Signal Range':<20} {'Packets':<10} {'First Seen':<20} {'Last Seen':<20}")
        print("-" * 110)

        for row in cursor.fetchall():
            mac, min_sig, max_sig, packets, first_seen, last_seen = row

            if min_sig and max_sig:
                signal_str = f"{min_sig} to {max_sig} dBm"
                # Variable signal = mobile device
                if abs(max_sig - min_sig) > 20:
                    hint = "← MOBILE (signal varies)"
                else:
                    hint = "← STATIC (consistent signal)"
            else:
                signal_str = "Unknown"
                hint = ""

            print(f"{mac:<20} {signal_str:<20} {packets:<10} {first_seen:<20} {last_seen:<20} {hint}")

def get_bluetooth_devices(db_path):
    """Get Bluetooth devices"""
    print("\n" + "="*70)
    print("BLUETOOTH DEVICES (Phones, Trackers, TPMS, Wearables)")
    print("="*70)
    print("\nAirTags, Tiles, smartwatches, car TPMS. Unknown trackers are threats!\n")

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT devmac, type, packets,
                   datetime(first_time, 'unixepoch') as first_seen,
                   datetime(last_time, 'unixepoch') as last_seen
            FROM devices
            WHERE type IN ('Bluetooth', 'BTLE')
            ORDER BY last_time DESC
            LIMIT 50
        """)

        rows = cursor.fetchall()

        if not rows:
            print("  No Bluetooth devices captured yet.")
            print("  (Kismet may need Bluetooth capture enabled)")
            return

        print(f"{'MAC Address':<20} {'Type':<15} {'Packets':<10} {'First Seen':<20} {'Last Seen':<20}")
        print("-" * 100)

        for row in rows:
            mac, dtype, packets, first_seen, last_seen = row
            print(f"{mac:<20} {dtype:<15} {packets:<10} {first_seen:<20} {last_seen:<20}")

def investigate_specific_device(db_path, mac):
    """Deep dive into a specific device"""
    print("\n" + "="*70)
    print(f"DETAILED INVESTIGATION: {mac}")
    print("="*70)

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT devmac, type, phyname,
                   min_signal, max_signal, packets,
                   datetime(first_time, 'unixepoch') as first_seen,
                   datetime(last_time, 'unixepoch') as last_seen,
                   min_lat, min_lon, max_lat, max_lon
            FROM devices
            WHERE devmac = ?
        """, (mac,))

        row = cursor.fetchone()

        if not row:
            print(f"  Device {mac} not found in database")
            return

        devmac, dtype, phyname, min_sig, max_sig, packets, first_seen, last_seen, min_lat, min_lon, max_lat, max_lon = row

        print(f"\nBASIC INFO:")
        print(f"  MAC Address    : {devmac}")
        print(f"  Device Type    : {dtype}")
        print(f"  PHY Type       : {phyname or 'Unknown'}")
        print(f"  First Seen     : {first_seen}")
        print(f"  Last Seen      : {last_seen}")
        print(f"  Total Packets  : {packets}")

        print(f"\nSIGNAL ANALYSIS:")
        if min_sig and max_sig:
            print(f"  Signal Range   : {min_sig} to {max_sig} dBm")
            print(f"  Signal Variance: {abs(max_sig - min_sig)} dBm")

            if abs(max_sig - min_sig) > 20:
                print(f"  Assessment     : MOBILE DEVICE (signal varies significantly)")
            else:
                print(f"  Assessment     : STATIC DEVICE (consistent signal)")

            if max_sig > -50:
                print(f"  Distance       : VERY CLOSE (yours or immediate neighbor)")
            elif max_sig > -70:
                print(f"  Distance       : NEARBY")
            else:
                print(f"  Distance       : FAR AWAY")
        else:
            print(f"  Signal Range   : No signal data")

        print(f"\nLOCATION DATA:")
        if min_lat and min_lon:
            print(f"  GPS Coordinates: {min_lat}, {min_lon}")
            if max_lat and max_lon:
                if abs(max_lat - min_lat) > 0.001 or abs(max_lon - min_lon) > 0.001:
                    print(f"  Movement       : YES (coordinates vary)")
                else:
                    print(f"  Movement       : NO (stationary)")
        else:
            print(f"  GPS Coordinates: Not available")

        # Categorization recommendation
        print(f"\nCATEGORIZATION RECOMMENDATION:")

        if dtype == 'Wi-Fi AP':
            print(f"  Category       : Router/Access Point")
            if max_sig and max_sig > -60:
                print(f"  Recommendation : ADD to ignore list (your router or neighbor's static router)")
            else:
                print(f"  Recommendation : REVIEW - Could be mobile hotspot if signal varies")

        elif dtype in ('Bluetooth', 'BTLE'):
            print(f"  Category       : Bluetooth Device")
            print(f"  Recommendation : CHECK if it's yours (phone, watch, car, earbuds)")
            print(f"                   If unknown: DO NOT IGNORE (could be tracker)")

        elif dtype == 'Wi-Fi Device':
            print(f"  Category       : WiFi Client")
            if min_sig and max_sig and abs(max_sig - min_sig) > 20:
                print(f"  Recommendation : MOBILE - Do NOT ignore unless it's your device")
            else:
                print(f"  Recommendation : Could be static IoT - verify it's yours before ignoring")

        else:
            print(f"  Category       : {dtype}")
            print(f"  Recommendation : INVESTIGATE FURTHER")

def get_manufacturer_oui(mac):
    """Get first 3 bytes of MAC for OUI lookup"""
    parts = mac.upper().split(':')
    if len(parts) >= 3:
        return ':'.join(parts[:3])
    return mac

def show_manufacturers(db_path):
    """Show device counts by manufacturer (OUI)"""
    print("\n" + "="*70)
    print("TOP MANUFACTURERS (by OUI prefix)")
    print("="*70)
    print("\nThis helps identify if devices are yours (Apple, Samsung, etc.)\n")

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT devmac FROM devices WHERE devmac IS NOT NULL
        """)

        oui_counts = {}
        for row in cursor.fetchall():
            mac = row[0]
            oui = get_manufacturer_oui(mac)
            oui_counts[oui] = oui_counts.get(oui, 0) + 1

        # Sort by count
        sorted_ouis = sorted(oui_counts.items(), key=lambda x: x[1], reverse=True)

        print(f"{'OUI Prefix':<20} {'Device Count':<15} {'To Lookup Manufacturer:'}")
        print("-" * 80)

        for oui, count in sorted_ouis[:30]:  # Top 30
            print(f"{oui:<20} {count:<15} curl -s 'https://api.macvendors.com/{oui}'")

def main_menu():
    """Interactive investigation menu"""
    db_path = find_latest_kismet_db()

    print("\n" + "="*70)
    print("KISMET DEVICE INVESTIGATION TOOL")
    print("="*70)
    print(f"\nDatabase: {db_path}\n")

    while True:
        print("\n" + "="*70)
        print("INVESTIGATION OPTIONS:")
        print("="*70)
        print("  1. Device Type Summary")
        print("  2. Show WiFi Access Points (Routers)")
        print("  3. Show WiFi Client Devices (Phones, Laptops)")
        print("  4. Show Bluetooth Devices")
        print("  5. Show Top Manufacturers (OUI)")
        print("  6. Investigate Specific Device (by MAC)")
        print("  7. Generate All Reports")
        print("  0. Exit")

        choice = input("\nEnter choice (0-7): ").strip()

        if choice == '0':
            print("\nExiting investigation tool.")
            break
        elif choice == '1':
            get_device_type_summary(db_path)
        elif choice == '2':
            get_wifi_aps(db_path)
        elif choice == '3':
            get_wifi_clients(db_path)
        elif choice == '4':
            get_bluetooth_devices(db_path)
        elif choice == '5':
            show_manufacturers(db_path)
        elif choice == '6':
            mac = input("\nEnter MAC address to investigate: ").strip().upper()
            investigate_specific_device(db_path, mac)
        elif choice == '7':
            get_device_type_summary(db_path)
            get_wifi_aps(db_path)
            get_wifi_clients(db_path)
            get_bluetooth_devices(db_path)
            show_manufacturers(db_path)
        else:
            print("Invalid choice. Please enter 0-7.")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
