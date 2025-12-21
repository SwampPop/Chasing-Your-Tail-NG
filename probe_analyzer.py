#!/usr/bin/env python3

import json
import glob
import sqlite3
import argparse
import os
import requests
from cyt_constants import SystemConstants
from datetime import datetime

# Load config with secure credentials
from secure_credentials import secure_config_loader
config, credential_manager = secure_config_loader('config.json')

# ANSI Color Codes for Alerting
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Known Drone Manufacturer MAC Prefixes (OUIs)
# This is a short list. In production, this should be a larger database.
DRONE_OUIS = {
    # DJI
    "60:60:1F": "DJI Technology",
    "34:D2:62": "DJI Technology",
    "40:6C:8F": "DJI Technology",
    "58:6B:14": "DJI Technology",
    "E4:0F:53": "DJI Technology",

    # Parrot
    "90:03:B7": "Parrot SA",
    "A0:14:3D": "Parrot SA",
    "00:12:1C": "Parrot SA",

    # Autel
    "00:1C:27": "Autel Robotics",  # Note: sometimes generic

    # Skydio
    "D8:3A:DD": "Skydio",

    # Yuneec
    "E0:B6:F5": "Yuneec",

    # Generic / GoPro
    "F4:DD:9E": "GoPro (Karma)",
}


class ProbeAnalyzer:
    def __init__(self, local_only=True):
        self.wigle_api_key = credential_manager.get_wigle_token()
        self.local_only = local_only

        if not self.wigle_api_key and not local_only:
            print(
                f"{YELLOW}⚠️  No WiGLE API token found. "
                f"Defaulting to local analysis.{RESET}")
            self.local_only = True

        self.probes = {}

    def check_drone_threat(self, mac):
        """Check if a MAC address belongs to a known drone manufacturer"""
        try:
            # Normalize MAC format (uppercase)
            clean_mac = mac.upper()
            # Extract the first 8 chars (XX:XX:XX)
            prefix = clean_mac[:8]

            if prefix in DRONE_OUIS:
                return DRONE_OUIS[prefix]
        except (AttributeError, TypeError, IndexError):
            # Invalid MAC format - not a string or too short
            pass
        return None

    def parse_database(self, db_path):
        print(f"[*] Reading database: {db_path}")
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Get WiFi devices, Bluetooth devices, and APs (Drones often act as APs)
                query = ("SELECT device FROM devices WHERE "
                         "type='Wi-Fi Client' OR type='Wi-Fi AP' OR "
                         "type='Bluetooth' OR type='BTLE'")
                cursor.execute(query)

                rows = cursor.fetchall()

                for row in rows:
                    try:
                        data = json.loads(row[0])
                        mac = data.get('kismet.device.base.macaddr')

                        # Check for Drone Threat IMMEDIATELY
                        drone_manuf = self.check_drone_threat(mac)

                        # Extract Probed SSIDs
                        if ('dot11.device' in data and
                                'dot11.device.probed_ssid_map' in
                                data['dot11.device']):
                            probed_map = data['dot11.device'][
                                'dot11.device.probed_ssid_map']
                            for result in probed_map:
                                ssid = result.get('dot11.probedssid.ssid')
                                last_seen = result.get(
                                    'dot11.probedssid.last_time')

                                if ssid and len(ssid) > 0:
                                    if ssid not in self.probes:
                                        self.probes[ssid] = {
                                            'count': 0,
                                            'macs': set(),
                                            'timestamps': [],
                                            'drones': []
                                        }

                                    self.probes[ssid]['count'] += 1
                                    self.probes[ssid]['macs'].add(mac)

                                    if drone_manuf:
                                        self.probes[ssid]['drones'].append(
                                            f"{drone_manuf} ({mac})")

                                    if last_seen:
                                        self.probes[ssid]['timestamps'].append(
                                            last_seen)

                    except (json.JSONDecodeError, AttributeError, KeyError, TypeError):
                        # Invalid JSON, missing fields, or malformed data
                        continue

        except sqlite3.Error as e:
            print(f"{RED}[!] Database error: {e}{RESET}")
        except (IOError, OSError) as e:
            print(f"{RED}[!] File system error: {e}{RESET}")

    def query_wigle(self, ssid):
        if self.local_only or not self.wigle_api_key:
            return None

        print(f"   🌐 Querying WiGLE for: {ssid}")
        headers = {'Authorization': f'Basic {self.wigle_api_key}'}
        params = {'ssid': ssid}

        # Standard search bounds from config would go here

        try:
            response = requests.get(
                'https://api.wigle.net/api/v2/network/search',
                headers=headers, params=params,
                timeout=SystemConstants.WIGLE_API_TIMEOUT_SECONDS)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.Timeout:
            print(f"   ⏱️  WiGLE query timed out for {ssid}")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Network connection error querying WiGLE")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ WiGLE API error: {e}")
        except (json.JSONDecodeError, ValueError):
            print(f"   ⚠️  Invalid response from WiGLE API")
        return None

    def run_analysis(self, db_path):
        self.parse_database(db_path)

        sorted_ssids = sorted(self.probes.items(),
                              key=lambda x: len(x[1]['macs']), reverse=True)

        print("\n" + "="*60)
        print("CYT DRONE & PROBE HUNTER")
        print("="*60)

        drone_count = 0

        for ssid, data in sorted_ssids:
            unique_devices = len(data['macs'])
            drones_found = data['drones']

            # --- ALERT LOGIC ---

            # 1. DRONE DETECTED
            if len(drones_found) > 0:
                drone_count += 1
                print(
                    f"\n{RED}[!!!] DRONE DETECTED PROBING SSID: {ssid}{RESET}")
                for d in drones_found:
                    print(f"{RED}   └─ TARGET IDENTIFIED: {d}{RESET}")

            # 2. RARE TARGETS (Potential Surveillance)
            elif unique_devices < 3:
                print(f"\n[TARGET] SSID: {ssid}")
                print(
                    f"   ├─ Devices probing: {unique_devices} "
                    f"{list(data['macs'])}")

                # Run WiGLE only on high interest
                wigle_data = self.query_wigle(ssid)
                if wigle_data and 'results' in wigle_data:
                    results = wigle_data['results']
                    print(
                        f"   └─ 🌍 WiGLE: Found {len(results)} locations.")
                    if results:
                        print(
                            "      📍 Last seen near: "
                            f"{results[0].get('trilat')}, "
                            f"{results[0].get('trilong')}")

        if drone_count == 0:
            print(
                f"\n{GREEN}[*] No Drones Detected in this capture.{RESET}")


def get_latest_db():
    files = glob.glob("*.kismet") + glob.glob("/var/log/kismet/*.kismet")
    if not files:
        return None
    return max(files, key=os.path.getctime)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--wigle', action='store_true',
                        help='Enable WiGLE API')
    parser.add_argument('--local', action='store_true',
                        help='Force local only')
    parser.add_argument('--db', help='Specific Kismet DB file')
    args = parser.parse_args()

    is_local = True
    if args.wigle:
        is_local = False

    analyzer = ProbeAnalyzer(local_only=is_local)
    target_db = args.db if args.db else get_latest_db()

    if target_db:
        analyzer.run_analysis(target_db)
    else:
        print(f"{YELLOW}[!] No Kismet database found.{RESET}")
