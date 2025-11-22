#!/usr/bin/env python3

import json
import pathlib
import glob
import sqlite3
import argparse
import os
import requests

# Load config with secure credentials
from secure_credentials import secure_config_loader
config, credential_manager = secure_config_loader('config.json')

class ProbeAnalyzer:
    def __init__(self, local_only=True):
        # Get WiGLE API key from secure storage
        self.wigle_api_key = credential_manager.get_wigle_token()
        self.local_only = local_only
        
        if not self.wigle_api_key and not local_only:
            print("⚠️  No WiGLE API token found. Defaulting to local analysis.")
            self.local_only = True

        # Dictionary structure: { 'SSID_NAME': { 'count': 0, 'macs': set(), 'timestamps': [] } }
        self.probes = {} 

    def parse_database(self, db_path):
        """Parse Kismet DB for granular MAC-to-SSID mapping"""
        print(f"[*] Reading database: {db_path}")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # We only want Wi-Fi Clients (devices like phones), not Access Points
            query = "SELECT device FROM devices WHERE type='Wi-Fi Client'"
            cursor.execute(query)
            
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    data = json.loads(row[0])
                    mac = data.get('kismet.device.base.macaddr')
                    
                    # Extract Probed SSIDs from the Kismet JSON structure
                    if 'dot11.device' in data and 'dot11.device.probed_ssid_map' in data['dot11.device']:
                        probed_map = data['dot11.device']['dot11.device.probed_ssid_map']
                        
                        for result in probed_map:
                            ssid = result.get('dot11.probedssid.ssid')
                            last_seen = result.get('dot11.probedssid.last_time')
                            
                            if ssid and len(ssid) > 0:
                                if ssid not in self.probes:
                                    self.probes[ssid] = {
                                        'count': 0,
                                        'macs': set(),
                                        'timestamps': []
                                    }
                                
                                self.probes[ssid]['count'] += 1
                                self.probes[ssid]['macs'].add(mac)
                                if last_seen:
                                    self.probes[ssid]['timestamps'].append(last_seen)
                                    
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            conn.close()

        except Exception as e:
            print(f"[!] Error reading database: {e}")

    def query_wigle(self, ssid):
        """Query WiGLE for information about an SSID"""
        if self.local_only or not self.wigle_api_key:
            return None
            
        print(f"   🌐 Querying WiGLE for: {ssid}")
        headers = {'Authorization': f'Basic {self.wigle_api_key}'}
        params = {'ssid': ssid}
        
        # Add geographic bounding box if defined in config
        search_config = config.get('search', {})
        if all(search_config.get(k) for k in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
            params.update({
                'latrange1': search_config['lat_min'],
                'latrange2': search_config['lat_max'],
                'longrange1': search_config['lon_min'],
                'longrange2': search_config['lon_max'],
            })

        try:
            response = requests.get(
                'https://api.wigle.net/api/v2/network/search',
                headers=headers,
                params=params
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print("   [!] WiGLE Auth Failed")
                return {"error": "Auth Failed"}
        except Exception:
            pass
        return None

    def run_analysis(self, db_path):
        self.parse_database(db_path)
        
        # Sort by number of distinct devices probing for it
        sorted_ssids = sorted(self.probes.items(), key=lambda x: len(x[1]['macs']), reverse=True)
        
        print("\n" + "="*60)
        print(f"CYT DEEP PROBE ANALYSIS")
        print("="*60)
        
        for ssid, data in sorted_ssids:
            unique_devices = len(data['macs'])
            total_pings = data['count']
            
            # Filtering: We care more about Rare Probes (Targeted) than Common ones
            # If 100 people probe "Starbucks", it's noise.
            # If 1 person probes "Thom's Secret Network", it's a hit.
            
            if unique_devices < 3: # High interest
                print(f"\n[TARGET] SSID: {ssid}")
                print(f"   ├─ Devices probing: {unique_devices} {list(data['macs'])}")
                print(f"   └─ Total Requests:  {total_pings}")
                
                # Only run WiGLE on high-interest targets to save API credits
                wigle_data = self.query_wigle(ssid)
                if wigle_data and 'results' in wigle_data:
                     results = wigle_data['results']
                     print(f"   └─ 🌍 WiGLE: Found {len(results)} locations.")
                     if results:
                         print(f"      📍 Last seen near: {results[0].get('trilat')}, {results[0].get('trilong')}")
            
            elif unique_devices > 20:
                 # Just summary for common stuff
                 continue 

def get_latest_db():
    # Try current dir then standard log dir
    files = glob.glob("*.kismet") + glob.glob("/var/log/kismet/*.kismet")
    if not files:
        return None
    return max(files, key=os.path.getctime)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--wigle', action='store_true', help='Enable WiGLE API')
    parser.add_argument('--local', action='store_true', help='Force local only')
    parser.add_argument('--db', help='Specific Kismet DB file')
    args = parser.parse_args()

    # Logic: Default to local UNLESS --wigle is passed
    is_local = True
    if args.wigle:
        is_local = False
        
    analyzer = ProbeAnalyzer(local_only=is_local)
    
    target_db = args.db if args.db else get_latest_db()
    
    if target_db:
        analyzer.run_analysis(target_db)
    else:
        print("[!] No Kismet database found.")
