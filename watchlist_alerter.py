#!/usr/bin/env python3
"""
Watchlist Alerter - Real-time monitoring for suspicious devices
Checks Kismet database for watchlist devices and triggers alerts
"""

import sqlite3
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

class WatchlistAlerter:
    def __init__(self, cyt_dir="/home/parallels/CYT"):
        self.cyt_dir = Path(cyt_dir)
        self.watchlist_db = self.cyt_dir / "watchlist.db"
        self.kismet_dir = self.cyt_dir / "logs" / "kismet"
        self.alert_log = self.cyt_dir / "logs" / "watchlist_alerts.log"
        self.last_check = {}  # Track last seen time per MAC
        self.alert_cooldown = 300  # 5 minutes between repeat alerts
        
    def get_watchlist(self):
        """Load all watchlist entries"""
        try:
            conn = sqlite3.connect(str(self.watchlist_db))
            cursor = conn.execute("SELECT mac, alias, device_type, notes FROM devices")
            watchlist = {row[0].upper(): {
                'alias': row[1],
                'type': row[2],
                'notes': row[3]
            } for row in cursor.fetchall()}
            conn.close()
            return watchlist
        except Exception as e:
            print(f"[ERROR] Loading watchlist: {e}")
            return {}
    
    def get_latest_kismet_db(self):
        """Find most recent Kismet database"""
        try:
            dbs = sorted(self.kismet_dir.glob("*.kismet"), key=os.path.getmtime, reverse=True)
            return dbs[0] if dbs else None
        except Exception as e:
            print(f"[ERROR] Finding Kismet DB: {e}")
            return None
    
    def check_for_watchlist_devices(self, watchlist, since_minutes=5):
        """Check Kismet for any watchlist devices seen recently"""
        kismet_db = self.get_latest_kismet_db()
        if not kismet_db:
            return []
        
        alerts = []
        cutoff_time = int(time.time()) - (since_minutes * 60)
        
        try:
            conn = sqlite3.connect(f"file:{kismet_db}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            
            # Check each watchlist MAC
            for mac, info in watchlist.items():
                cursor = conn.execute("""
                    SELECT 
                        devmac,
                        strongest_signal,
                        first_time,
                        last_time,
                        json_extract(device, '$.kismet.device.base.packets.total') as packets
                    FROM devices 
                    WHERE UPPER(devmac) = ? 
                      AND last_time >= ?
                """, (mac, cutoff_time))
                
                row = cursor.fetchone()
                if row:
                    # Check cooldown
                    last_alert = self.last_check.get(mac, 0)
                    if time.time() - last_alert > self.alert_cooldown:
                        alerts.append({
                            'mac': mac,
                            'alias': info['alias'],
                            'type': info['type'],
                            'signal': row['strongest_signal'],
                            'first_seen': datetime.fromtimestamp(row['first_time']).strftime('%H:%M:%S'),
                            'last_seen': datetime.fromtimestamp(row['last_time']).strftime('%H:%M:%S'),
                            'packets': row['packets'] or 0,
                            'notes': info['notes']
                        })
                        self.last_check[mac] = time.time()
            
            conn.close()
            return alerts
            
        except Exception as e:
            print(f"[ERROR] Checking Kismet: {e}")
            return []
    
    def format_alert(self, alert):
        """Format alert for display and logging"""
        severity = "🔴 CRITICAL" if "Attack" in alert['type'] else "🟠 WARNING"
        
        msg = f"""
{'='*60}
{severity}: WATCHLIST DEVICE DETECTED
{'='*60}
Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
MAC:      {alert['mac']}
Alias:    {alert['alias']}
Type:     {alert['type']}
Signal:   {alert['signal']} dBm
Seen:     {alert['first_seen']} - {alert['last_seen']}
Packets:  {alert['packets']}
{'='*60}
Notes:    {alert['notes'][:100]}...
{'='*60}
"""
        return msg
    
    def log_alert(self, alert):
        """Write alert to log file"""
        try:
            self.alert_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alert_log, 'a') as f:
                f.write(f"{datetime.now().isoformat()}|{alert['mac']}|{alert['alias']}|{alert['signal']}|{alert['type']}\n")
        except Exception as e:
            print(f"[ERROR] Writing log: {e}")
    
    def run_check(self):
        """Run a single check cycle"""
        watchlist = self.get_watchlist()
        if not watchlist:
            return []
        
        alerts = self.check_for_watchlist_devices(watchlist)
        
        for alert in alerts:
            print(self.format_alert(alert))
            self.log_alert(alert)
        
        return alerts
    
    def run_continuous(self, interval=30):
        """Run continuous monitoring"""
        print(f"[WATCHLIST ALERTER] Starting continuous monitoring (interval: {interval}s)")
        print(f"[WATCHLIST ALERTER] Watching {len(self.get_watchlist())} devices")
        
        while True:
            try:
                alerts = self.run_check()
                if not alerts:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] No watchlist devices detected")
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n[WATCHLIST ALERTER] Stopped")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(interval)


def get_watchlist_status():
    """Return watchlist status as JSON for API"""
    alerter = WatchlistAlerter()
    watchlist = alerter.get_watchlist()
    alerts = alerter.check_for_watchlist_devices(watchlist, since_minutes=60)
    
    return {
        'watchlist_count': len(watchlist),
        'recent_sightings': len(alerts),
        'devices': list(watchlist.keys()),
        'alerts': alerts
    }


if __name__ == "__main__":
    import sys
    
    alerter = WatchlistAlerter()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single check
        alerts = alerter.run_check()
        print(f"Found {len(alerts)} watchlist devices")
    else:
        # Continuous monitoring
        alerter.run_continuous(interval=30)
