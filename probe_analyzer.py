#!/usr/bin/env python3

import json
import pathlib
import glob
import re
from datetime import datetime
import requests
import sqlite3
import argparse

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

class ProbeAnalyzer:
    def __init__(self, log_dir=None, local_only=False):
        self.log_dir = log_dir or pathlib.Path(config['paths']['log_dir'])
        self.wigle_api_key = config.get('api_keys', {}).get('wigle', {}).get('encoded_token')
        self.probes = {}  # Dictionary to store probe requests {ssid: [timestamps]}
        self.local_only = local_only  # New flag for local search only
        
    def parse_log_file(self, log_file):
        """Parse a single CYT log file for probe requests"""
        probe_pattern = re.compile(r'Found a probe!: (.*?)\n')
        # Update timestamp pattern to match log format
        timestamp_pattern = re.compile(r'Current Time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
        
        with open(log_file, 'r') as f:
            content = f.read()
            
        # Debug: Print all probes found in this file
        probes_found = probe_pattern.findall(content)
        print(f"\nFound {len(probes_found)} probes in {log_file}:")
        for probe in probes_found:
            print(f"- {probe}")
        
        for probe in probe_pattern.finditer(content):
            ssid = probe.group(1).strip()
            # Find nearest timestamp before this probe
            content_before = content[:probe.start()]
            timestamp_match = timestamp_pattern.findall(content_before)
            if timestamp_match:
                timestamp = timestamp_match[-1]  # Get last timestamp before probe
                if ssid not in self.probes:
                    self.probes[ssid] = []
                self.probes[ssid].append(timestamp)
            else:
                # If no timestamp found, use file creation time from filename
                # Format: cyt_log_MMDDYY_HHMMSS
                filename = str(log_file)
                date_str = filename.split('_')[2:4]  # ['MMDDYY', 'HHMMSS']
                if len(date_str) == 2:
                    timestamp = f"{date_str[0][:2]}-{date_str[0][2:4]}-{date_str[0][4:]} {date_str[1][:2]}:{date_str[1][2:4]}:{date_str[1][4:]}"
                    if ssid not in self.probes:
                        self.probes[ssid] = []
                    self.probes[ssid].append(timestamp)
    
    def parse_all_logs(self):
        """Parse all log files in the log directory"""
        log_files = self.log_dir.glob('cyt_log_*')
        log_count = 0
        print("\nScanning log files:")
        for log_file in log_files:
            print(f"- Reading {log_file}")
            self.parse_log_file(log_file)
            log_count += 1
        print(f"\nProcessed {log_count} log files")
            
    def query_wigle(self, ssid):
        """Query WiGLE for information about an SSID"""
        if not self.wigle_api_key:
            return {"error": "WiGLE API key not configured"}
            
        print(f"\nQuerying WiGLE for SSID: {ssid}")
        headers = {
            'Authorization': f'Basic {self.wigle_api_key}'
        }
        
        # Only include bounding box if local_only is True and coordinates are set
        params = {'ssid': ssid}
        if self.local_only:
            search_config = config.get('search', {})
            if all(search_config.get(k) is not None for k in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
                params.update({
                    'latrange1': search_config['lat_min'],
                    'latrange2': search_config['lat_max'],
                    'longrange1': search_config['lon_min'],
                    'longrange2': search_config['lon_max'],
                })
                print("Using local search area")
        
        try:
            response = requests.get(
                'https://api.wigle.net/api/v2/network/search',
                headers=headers,
                params=params
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
            
    def analyze_probes(self):
        """Analyze collected probe requests"""
        results = []
        total_ssids = len(self.probes)
        print(f"\nQuerying WiGLE for {total_ssids} unique SSIDs...")
        for i, (ssid, timestamps) in enumerate(self.probes.items(), 1):
            print(f"\nProgress: {i}/{total_ssids}")
            result = {
                "ssid": ssid,
                "count": len(timestamps),
                "first_seen": min(timestamps),
                "last_seen": max(timestamps),
                "wigle_data": self.query_wigle(ssid) if self.wigle_api_key else None
            }
            results.append(result)
        return results

def main():
    """
    Probe Request Analyzer for Chasing Your Tail
    
    This tool analyzes probe requests from CYT log files and can query WiGLE for SSID locations.
    
    Before running:
    1. Make sure you have CYT log files in your logs directory
    2. To use WiGLE lookups:
       - Get a WiGLE API key from wigle.net
       - Add it to config.json under api_keys->wigle
       - Set your search area in config.json under search
    """
    
    if len(glob.glob(str(pathlib.Path(config['paths']['log_dir']) / 'cyt_log_*'))) == 0:
        print("\nError: No log files found!")
        print(f"Please check the logs directory: {config['paths']['log_dir']}")
        print("Run Chasing Your Tail first to generate some logs.")
        return

    # Check WiGLE configuration
    if not config.get('api_keys', {}).get('wigle'):
        print("\nNote: WiGLE API key not configured.")
        print("To enable WiGLE lookups:")
        print("1. Get an API key from wigle.net")
        print("2. Add it to config.json under api_keys->wigle")
    
    parser = argparse.ArgumentParser(description='Analyze probe requests and query WiGLE')
    parser.add_argument('--local', action='store_true', 
                      help='Limit WiGLE search to configured bounding box')
    args = parser.parse_args()

    print("\nAnalyzing probe requests from CYT logs...")
    analyzer = ProbeAnalyzer(local_only=args.local)
    if args.local:
        print("WiGLE search limited to configured bounding box")
    else:
        print("WiGLE search will return global results")
    analyzer.parse_all_logs()
    results = analyzer.analyze_probes()
    
    if not results:
        print("\nNo probe requests found in logs!")
        print("Make sure Chasing Your Tail is running and detecting probes.")
        return
    
    # Print analysis results
    print(f"\nFound {len(results)} unique SSIDs in probe requests:")
    print("-" * 50)
    
    # Sort results by count (most frequent first)
    results.sort(key=lambda x: x['count'], reverse=True)
    
    for result in results:
        print(f"\nSSID: {result['ssid']}")
        print(f"Times seen: {result['count']}")
        print(f"First seen: {result['first_seen']}")
        print(f"Last seen: {result['last_seen']}")
        
        # Calculate time span
        first = datetime.strptime(result['first_seen'], '%m-%d-%y %H:%M:%S')
        last = datetime.strptime(result['last_seen'], '%m-%d-%y %H:%M:%S')
        duration = last - first
        if duration.total_seconds() > 0:
            print(f"Time span: {duration}")
            print(f"Average frequency: {result['count'] / duration.total_seconds():.2f} probes/second")
        
        if result.get('wigle_data'):
            if 'error' in result['wigle_data']:
                if result['wigle_data']['error'] != "WiGLE API key not configured":
                    print(f"WiGLE Error: {result['wigle_data']['error']}")
            else:
                print("\nWiGLE Data:")
                locations = result['wigle_data'].get('results', [])
                print(f"Known locations: {len(locations)}")
                if locations:
                    print("Recent sightings:")
                    for loc in locations[:3]:  # Show top 3 most recent
                        print(f"- Lat: {loc.get('trilat')}, Lon: {loc.get('trilong')}")
                        print(f"  Last seen: {loc.get('lastupdt')}")

if __name__ == "__main__":
    main() 