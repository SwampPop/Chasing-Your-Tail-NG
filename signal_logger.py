#!/usr/bin/env python3
"""
Signal Strength Logger - Track signal strength over time for triangulation
Logs watchlist device signals with timestamps for location hunting
"""

import subprocess
import json
import time
import os
from datetime import datetime
from pathlib import Path

class SignalLogger:
    def __init__(self, log_file="signal_log.csv"):
        self.log_file = Path(log_file)
        self.api_url = "http://localhost:8080/api/watchlist/sightings"
        
        # Initialize log file with header if new
        if not self.log_file.exists():
            with open(self.log_file, 'w') as f:
                f.write("timestamp,mac,alias,signal_dbm,proximity,age_seconds,notes\n")
    
    def get_sightings(self):
        """Fetch current watchlist sightings from API"""
        try:
            result = subprocess.run(
                ['curl', '-s', self.api_url],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return None
        except Exception as e:
            print(f"Error fetching sightings: {e}")
            return None
    
    def log_signals(self, sightings):
        """Log current signal readings"""
        if not sightings or 'sightings' not in sightings:
            return 0
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logged = 0
        
        with open(self.log_file, 'a') as f:
            for s in sightings['sightings']:
                # Only log devices with actual signal readings
                if s.get('signal') and s['signal'] != 0:
                    line = f"{timestamp},{s['mac']},{s['alias']},{s['signal']},{s['proximity']},{s['age_seconds']},{s.get('notes', '')[:50]}\n"
                    f.write(line)
                    logged += 1
        
        return logged
    
    def display_current(self, sightings):
        """Display current readings in terminal"""
        if not sightings or 'sightings' not in sightings:
            print("  No sightings available")
            return
        
        print(f"\n{'='*70}")
        print(f"  SIGNAL READINGS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        for s in sightings['sightings']:
            signal = s.get('signal', 0)
            
            # Visual signal bar
            if signal >= -50:
                bar = "█" * 10
                color = "\033[92m"  # Green
            elif signal >= -60:
                bar = "█" * 8 + "░" * 2
                color = "\033[92m"
            elif signal >= -70:
                bar = "█" * 6 + "░" * 4
                color = "\033[93m"  # Yellow
            elif signal >= -80:
                bar = "█" * 4 + "░" * 6
                color = "\033[93m"
            elif signal >= -90:
                bar = "█" * 2 + "░" * 8
                color = "\033[91m"  # Red
            else:
                bar = "░" * 10
                color = "\033[91m"
            
            reset = "\033[0m"
            
            # Highlight attacker devices
            if 'ATTACKER' in s['alias'] or 'SUSPECT' in s['alias']:
                prefix = "🔴"
            else:
                prefix = "  "
            
            print(f"{prefix} {s['alias'][:30]:<30}")
            print(f"   MAC: {s['mac']}")
            print(f"   Signal: {color}{signal:>4} dBm [{bar}]{reset} {s['proximity']}")
            print(f"   Last seen: {s['age_seconds']}s ago")
            print()
    
    def run(self, interval=3, target_mac=None):
        """Run continuous logging"""
        print(f"\n{'#'*70}")
        print(f"  SIGNAL STRENGTH LOGGER")
        print(f"  Logging to: {self.log_file}")
        print(f"  Interval: {interval} seconds")
        if target_mac:
            print(f"  Target: {target_mac}")
        print(f"  Press Ctrl+C to stop")
        print(f"{'#'*70}")
        
        readings = 0
        try:
            while True:
                sightings = self.get_sightings()
                
                if sightings:
                    # Filter to target if specified
                    if target_mac:
                        sightings['sightings'] = [
                            s for s in sightings['sightings'] 
                            if target_mac.upper() in s['mac'].upper()
                        ]
                    
                    logged = self.log_signals(sightings)
                    readings += logged
                    
                    # Clear screen and display
                    os.system('clear' if os.name == 'posix' else 'cls')
                    self.display_current(sightings)
                    print(f"  Total readings logged: {readings}")
                    print(f"  Log file: {self.log_file}")
                    print(f"\n  TIP: Walk toward houses - signal gets STRONGER = closer!")
                else:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Waiting for data...")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n\nLogging stopped. {readings} readings saved to {self.log_file}")
            self.show_summary()
    
    def show_summary(self):
        """Show summary of logged data"""
        if not self.log_file.exists():
            return
        
        print(f"\n{'='*70}")
        print("  SIGNAL LOG SUMMARY")
        print(f"{'='*70}")
        
        # Read and analyze log
        signals_by_mac = {}
        with open(self.log_file, 'r') as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    mac = parts[1]
                    signal = int(parts[3]) if parts[3] else 0
                    if mac not in signals_by_mac:
                        signals_by_mac[mac] = []
                    signals_by_mac[mac].append(signal)
        
        for mac, signals in signals_by_mac.items():
            if signals:
                print(f"\n  {mac}")
                print(f"    Readings: {len(signals)}")
                print(f"    Strongest: {max(signals)} dBm")
                print(f"    Weakest: {min(signals)} dBm")
                print(f"    Average: {sum(signals)//len(signals)} dBm")


if __name__ == "__main__":
    import sys
    
    target = None
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    logger = SignalLogger()
    logger.run(interval=3, target_mac=target)
