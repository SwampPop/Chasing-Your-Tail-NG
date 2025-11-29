#!/usr/bin/env python3
"""
Export Kismet database to WiGLE CSV format

WiGLE CSV Format:
WigleWifi-1.4,appRelease=2.26,model=Kismet,release=1.0.0,device=CYT,
display=wardrive,board=CYT,brand=CYT
MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type

Usage:
    python3 export_to_wigle.py --db wardrive_logs/wardrive_20241129-1.kismet --output wigle_export.csv
"""

import sqlite3
import argparse
import csv
from typing import List, Dict
from datetime import datetime

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Export Kismet to WiGLE CSV')
    parser.add_argument('--db', required=True, help='Kismet .kismet database file')
    parser.add_argument('--output', default='wigle_export.csv', help='Output CSV file')
    return parser.parse_args()

def extract_networks_from_kismet(db_path: str) -> List[Dict]:
    """
    Extract WiFi networks with GPS data from Kismet database.

    Args:
        db_path: Path to Kismet .kismet database

    Returns:
        List of network dictionaries with BSSID, SSID, encryption, GPS, etc.
    """
    networks = []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query for WiFi access points with GPS data
        query = """
        SELECT
            devices.devmac AS bssid,
            devices.device_key,
            devices.type,
            devices.first_time,
            devices.last_time,
            devices.channel,
            devices.strongest_signal,
            devices.min_lat,
            devices.min_lon,
            devices.avg_lat,
            devices.avg_lon,
            devices.max_lat,
            devices.max_lon
        FROM devices
        WHERE devices.type = 'Wi-Fi AP'
        AND devices.avg_lat IS NOT NULL
        AND devices.avg_lon IS NOT NULL
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            bssid, device_key, dev_type, first_time, last_time, channel, signal, \
                min_lat, min_lon, avg_lat, avg_lon, max_lat, max_lon = row

            # Get SSID from separate query (stored differently in Kismet schema)
            cursor.execute(
                "SELECT ssid_text FROM ssid WHERE device_key = ? LIMIT 1",
                (device_key,)
            )
            ssid_row = cursor.fetchone()
            ssid = ssid_row[0] if ssid_row else "<Hidden SSID>"

            # Get encryption type
            cursor.execute(
                "SELECT cryptset FROM ssid WHERE device_key = ? LIMIT 1",
                (device_key,)
            )
            crypt_row = cursor.fetchone()
            auth_mode = parse_encryption(crypt_row[0] if crypt_row else 0)

            # Convert timestamps (Kismet uses Unix epoch)
            first_seen = datetime.fromtimestamp(first_time).strftime('%Y-%m-%d %H:%M:%S')

            # Build network dictionary
            network = {
                'bssid': bssid.upper(),
                'ssid': ssid,
                'auth_mode': auth_mode,
                'first_seen': first_seen,
                'channel': channel if channel else 0,
                'rssi': signal if signal else -100,
                'latitude': avg_lat,
                'longitude': avg_lon,
                'altitude': 0,  # Kismet doesn't always log altitude
                'accuracy': calculate_accuracy(min_lat, max_lat, min_lon, max_lon),
                'type': 'WIFI'
            }

            networks.append(network)

        conn.close()
        return networks

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return []

def parse_encryption(cryptset: int) -> str:
    """
    Parse Kismet cryptset bitmask to WiGLE auth mode.

    Args:
        cryptset: Kismet cryptset integer (bitmask)

    Returns:
        WiGLE-compatible auth mode string
    """
    # Kismet cryptset bitmask values (from Kismet documentation)
    CRYPT_NONE = 0
    CRYPT_WEP = (1 << 1)
    CRYPT_WPA = (1 << 2)
    CRYPT_WPA2 = (1 << 3)
    CRYPT_WPA3 = (1 << 4)
    CRYPT_PSK = (1 << 5)
    CRYPT_EAP = (1 << 6)

    if cryptset == CRYPT_NONE:
        return "[OPEN]"
    elif cryptset & CRYPT_WEP:
        return "[WEP]"
    elif cryptset & CRYPT_WPA3:
        return "[WPA3-PSK]" if cryptset & CRYPT_PSK else "[WPA3-EAP]"
    elif cryptset & CRYPT_WPA2:
        return "[WPA2-PSK]" if cryptset & CRYPT_PSK else "[WPA2-EAP]"
    elif cryptset & CRYPT_WPA:
        return "[WPA-PSK]" if cryptset & CRYPT_PSK else "[WPA-EAP]"
    else:
        return "[Unknown]"

def calculate_accuracy(min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> int:
    """
    Estimate GPS accuracy based on coordinate spread.

    Args:
        min_lat, max_lat, min_lon, max_lon: GPS coordinate boundaries

    Returns:
        Estimated accuracy in meters
    """
    # Simple estimation: convert lat/lon spread to meters
    # 1 degree latitude ≈ 111 km
    # (This is approximate; real calculation requires haversine formula)

    if min_lat is None or max_lat is None:
        return 100  # Default accuracy if no spread data

    lat_spread = abs(max_lat - min_lat) * 111000  # meters
    lon_spread = abs(max_lon - min_lon) * 111000 * 0.7  # approximate cosine adjustment

    # Use larger of the two spreads as accuracy estimate
    accuracy = max(lat_spread, lon_spread)

    return int(accuracy) if accuracy > 0 else 10  # Minimum 10m accuracy

def write_wigle_csv(networks: List[Dict], output_path: str):
    """
    Write networks to WiGLE-compatible CSV.

    Args:
        networks: List of network dictionaries
        output_path: Output CSV file path
    """
    try:
        with open(output_path, 'w', newline='') as csvfile:
            # Write WiGLE header
            csvfile.write("WigleWifi-1.4,appRelease=CYT-2.2,model=Kismet,release=2024.11,")
            csvfile.write("device=ChaseYourTail,display=Wardrive,board=CYT,brand=CYT\n")

            # Write column headers
            writer = csv.writer(csvfile)
            writer.writerow([
                'MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 'RSSI',
                'CurrentLatitude', 'CurrentLongitude', 'AltitudeMeters',
                'AccuracyMeters', 'Type'
            ])

            # Write network data
            for net in networks:
                writer.writerow([
                    net['bssid'],
                    net['ssid'],
                    net['auth_mode'],
                    net['first_seen'],
                    net['channel'],
                    net['rssi'],
                    net['latitude'],
                    net['longitude'],
                    net['altitude'],
                    net['accuracy'],
                    net['type']
                ])

        print(f"[+] Exported {len(networks)} networks to {output_path}")
        print(f"[+] Upload to WiGLE: https://wigle.net/")

    except IOError as e:
        print(f"[ERROR] Failed to write CSV: {e}")

def main():
    """Main export workflow."""
    args = parse_args()

    print(f"[*] Extracting networks from {args.db}...")
    networks = extract_networks_from_kismet(args.db)

    if not networks:
        print("[WARN] No networks with GPS data found in database.")
        print("[INFO] Ensure Kismet GPS was enabled during capture.")
        return

    print(f"[+] Found {len(networks)} networks with GPS coordinates")

    print(f"[*] Writing WiGLE CSV to {args.output}...")
    write_wigle_csv(networks, args.output)

    print("\n[+] Export complete!")
    print("[INFO] Before uploading to WiGLE, review CSV for any sensitive SSIDs")
    print("[INFO] (e.g., home network names that reveal location)")

if __name__ == "__main__":
    main()
