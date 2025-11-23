#!/usr/bin/env python3
"""
Home Base Monitor for CYT
Stationary "Pattern of Life" Analyzer.
Focuses on:
1. Whitelisting known devices (Neighbors/Home)
2. Detecting "Night Crawlers" (New devices seen at 3 AM)
3. Generating Daily Briefings
"""
import logging
import time
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from secure_database import SecureKismetDB
from secure_credentials import secure_config_loader
from alert_manager import AlertManager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("home_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HomeMonitor:
    def __init__(self):
        self.config, _ = secure_config_loader('config.json')
        self.alerter = AlertManager()
        
        # State
        self.known_devices = self._load_whitelist()
        self.daily_stats = defaultdict(int)
        self.night_threats = []
        
        # Settings
        self.night_start = 1  # 1 AM
        self.night_end = 5    # 5 AM
        self.min_duration = 300 # 5 minutes (ignore cars driving by)

    def _load_whitelist(self):
        """Load known devices from JSON"""
        if os.path.exists("whitelist.json"):
            with open("whitelist.json", "r") as f:
                return set(json.load(f))
        return set()

    def _save_whitelist(self):
        """Save known devices to JSON"""
        with open("whitelist.json", "w") as f:
            json.dump(list(self.known_devices), f)

    def analyze_traffic(self, db_path):
        """Main analysis loop"""
        logger.info(f"Analyzing traffic from: {db_path}")
        
        with SecureKismetDB(db_path) as db:
            # Get all devices seen in the last check interval
            now = time.time()
            lookback = 60 # Check last minute
            devices = db.get_devices_by_time_range(now - lookback, now)
            
            current_hour = datetime.now().hour
            is_night_mode = self.night_start <= current_hour < self.night_end

            for dev in devices:
                mac = dev['mac']
                if not mac: continue
                
                # 1. Update Stats
                self.daily_stats[mac] += 1
                
                # 2. Check Whitelist
                if mac in self.known_devices:
                    continue # Ignore known neighbors/devices

                # 3. STRANGER DANGER (Night Mode)
                if is_night_mode:
                    logger.warning(f"Night Crawler Detected: {mac}")
                    self.alerter.send_alert(f"🌙 NIGHT ALERT: New Device {mac} detected at {current_hour}:00")
                    self.night_threats.append(mac)
                
                # 4. Auto-Learn (Optional)
                # If we see a device for > 1 hour during the day, assume it's a neighbor
                if self.daily_stats[mac] > 60: # Seen 60 times (approx 1 hour)
                    logger.info(f"Auto-whitelisting neighbor: {mac}")
                    self.known_devices.add(mac)
                    self._save_whitelist()

    def generate_daily_report(self):
        """Print a summary of the last 24 hours"""
        report = f"""
        === DAILY SECURITY BRIEFING ===
        Date: {datetime.now().strftime('%Y-%m-%d')}
        
        Total Unique Devices: {len(self.daily_stats)}
        New Neighbors Identified: {len(self.daily_stats) - len(self.known_devices)}
        
        [NIGHT WATCH ALERTS]
        Threats Detected: {len(self.night_threats)}
        {', '.join(self.night_threats)}
        
        [TOP 5 UNKNOWN DEVICES]
        """
        # Sort by most frequent
        sorted_devs = sorted(self.daily_stats.items(), key=lambda x: x[1], reverse=True)
        for mac, count in sorted_devs[:5]:
            if mac not in self.known_devices:
                report += f"  - {mac}: Seen {count} times\n"
                
        print(report)
        # Optionally save to file
        with open(f"report_{datetime.now().strftime('%Y%m%d')}.txt", "w") as f:
            f.write(report)

    def run(self):
        logger.info("Home Monitor Active. Press Ctrl+C to stop.")
        
        # Find DB
        db_pattern = self.config['paths']['kismet_logs']
        
        # FIX: Handle directory paths correctly
        if os.path.isdir(db_pattern):
            db_pattern = os.path.join(db_pattern, "*.kismet")
            
        import glob
        files = glob.glob(db_pattern)
        
        # Filter out directories from the results just in case
        files = [f for f in files if os.path.isfile(f)]
        
        if not files:
            # Fallback for testing
            if os.path.exists("test_capture.kismet"):
                logger.info("No live DB found, using test database.")
                target_db = "test_capture.kismet"
            else:
                logger.error(f"No Kismet database files found at: {db_pattern}")
                return
        else:
            # Pick the newest file
            target_db = max(files, key=os.path.getctime)

        try:
            while True:
                self.analyze_traffic(target_db)
                
                # Generate report at 8:00 AM
                now = datetime.now()
                if now.hour == 8 and now.minute == 0 and now.second < 10:
                    self.generate_daily_report()
                    time.sleep(60) # Don't generate twice
                    
                time.sleep(60) # Scan every minute
        except KeyboardInterrupt:
            logger.info("Stopping...")
            self.generate_daily_report()

if __name__ == "__main__":
    monitor = HomeMonitor()
    monitor.run()
