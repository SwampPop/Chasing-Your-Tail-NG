#!/usr/bin/env python3
"""
WiGLE Network Lookup - Search for networks by BSSID, SSID, or location
Uses credentials from config.json
"""

import json
import requests
import sys
from pathlib import Path

class WiGLELookup:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.api_base = "https://api.wigle.net/api/v2"
        
        wigle_config = self.config.get('wigle', {})
        self.api_name = wigle_config.get('api_name', '')
        self.api_token = wigle_config.get('api_token', '')
        
        if not self.api_name or not self.api_token:
            print("ERROR: WiGLE credentials not found in config.json")
            print("Add: \"wigle\": {\"api_name\": \"AIDxxx\", \"api_token\": \"xxx\"}")
            sys.exit(1)
    
    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _request(self, endpoint, params=None):
        """Make authenticated request to WiGLE API"""
        url = f"{self.api_base}/{endpoint}"
        try:
            response = requests.get(
                url, 
                params=params,
                auth=(self.api_name, self.api_token),
                timeout=30
            )
            data = response.json()
            
            if not data.get('success', True):
                print(f"API Error: {data.get('message', 'Unknown error')}")
                return None
            return data
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def search_bssid(self, bssid):
        """Search for a specific BSSID"""
        print(f"\n=== Searching for BSSID: {bssid} ===\n")
        data = self._request("network/search", {"netid": bssid})
        
        if data and data.get('results'):
            for r in data['results']:
                print(f"SSID: {r.get('ssid', 'Hidden')}")
                print(f"BSSID: {r.get('netid')}")
                print(f"Location: {r.get('trilat')}, {r.get('trilong')}")
                print(f"City: {r.get('city', 'N/A')}, {r.get('region', 'N/A')}")
                print(f"Road: {r.get('road', 'N/A')}")
                print(f"First seen: {r.get('firsttime')}")
                print(f"Last seen: {r.get('lasttime')}")
                print()
            return data['results']
        else:
            print("No results found")
            return []
    
    def search_ssid(self, ssid):
        """Search for networks by SSID"""
        print(f"\n=== Searching for SSID: {ssid} ===\n")
        data = self._request("network/search", {"ssid": ssid, "resultsPerPage": 25})
        
        if data and data.get('results'):
            print(f"Found {data.get('totalResults', 0)} networks named '{ssid}'\n")
            for r in data['results'][:10]:
                print(f"  {r.get('netid')} - {r.get('city', 'N/A')}, {r.get('region', 'N/A')}")
                print(f"    Coords: {r.get('trilat')}, {r.get('trilong')}")
            return data['results']
        else:
            print("No results found")
            return []
    
    def search_area(self, lat, lon, radius_km=0.5):
        """Search for networks in a geographic area"""
        # Convert radius to lat/lon range (approximate)
        lat_range = radius_km / 111  # ~111km per degree latitude
        lon_range = radius_km / 85   # ~85km per degree longitude at this latitude
        
        params = {
            "latrange1": lat - lat_range,
            "latrange2": lat + lat_range,
            "longrange1": lon - lon_range,
            "longrange2": lon + lon_range,
            "resultsPerPage": 100
        }
        
        print(f"\n=== Searching area around {lat}, {lon} (radius ~{radius_km}km) ===\n")
        data = self._request("network/search", params)
        
        if data and data.get('results'):
            print(f"Found {data.get('totalResults', 0)} networks in area\n")
            
            # Group by SSID
            by_ssid = {}
            for r in data['results']:
                ssid = r.get('ssid', 'Hidden')
                if ssid not in by_ssid:
                    by_ssid[ssid] = []
                by_ssid[ssid].append(r)
            
            for ssid, networks in sorted(by_ssid.items()):
                print(f"  {ssid}: {len(networks)} network(s)")
            
            return data['results']
        else:
            print("No results found")
            return []


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python3 wigle_lookup.py bssid <MAC_ADDRESS>")
        print("  python3 wigle_lookup.py ssid <NETWORK_NAME>")
        print("  python3 wigle_lookup.py area <LAT> <LON> [radius_km]")
        print()
        print("Examples:")
        print("  python3 wigle_lookup.py bssid 20:F1:9E:3E:94:47")
        print("  python3 wigle_lookup.py ssid casita")
        print("  python3 wigle_lookup.py area 29.922 -90.373 0.5")
        return
    
    lookup = WiGLELookup()
    cmd = sys.argv[1].lower()
    
    if cmd == "bssid":
        lookup.search_bssid(sys.argv[2])
    elif cmd == "ssid":
        lookup.search_ssid(sys.argv[2])
    elif cmd == "area" and len(sys.argv) >= 4:
        lat = float(sys.argv[2])
        lon = float(sys.argv[3])
        radius = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
        lookup.search_area(lat, lon, radius)
    else:
        print("Unknown command. Run without arguments for help.")


if __name__ == "__main__":
    main()
