#!/usr/bin/env python3
"""
CYT Attacker Hunter - Automated Threat Investigation

Monitors for suspicious devices that match attacker patterns:
- Brief appearances (show up, then disappear)
- Deauth/disassociation frame sources
- High probe frequency with no association
- Devices targeting specific networks (casita, ClubKatniss)

Runs in both wardrive and stationary modes.
"""

import json
import time
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import signal

# Configuration
CONFIG = {
    "kismet_api": "http://localhost:2501",
    "kismet_user": "kismet",
    "kismet_pass": "cyt2026",
    "poll_interval": 5,  # seconds between checks
    "brief_appearance_threshold": 300,  # 5 minutes - devices seen less than this are suspicious
    "strong_signal_threshold": -50,  # dBm - unusually strong signals
    "probe_flood_threshold": 20,  # probes per minute
    "alert_sound": True,
    "log_file": "attacker_hunt.log",
    "data_file": "attacker_detections.json",

    # Target networks to monitor for attacks against
    "target_networks": ["casita", "ClubKatniss", "casacita"],

    # Known attacker patterns (from previous investigation)
    "known_attacker_ouis": [
        "C6:4F:D5",  # Cox pattern used in original attack (may be spoofed)
    ],

    # Suspicious behaviors to flag
    "suspicious_patterns": {
        "brief_appearance": True,      # Device seen briefly then gone
        "deauth_source": True,         # Device sending deauth frames
        "no_association": True,        # Device probing but never associating
        "high_probe_rate": True,       # Excessive probe requests
        "strong_then_gone": True,      # Strong signal that disappears
        "targeting_our_networks": True # Probing for our SSIDs specifically
    }
}

@dataclass
class DeviceTracking:
    """Track a device's behavior over time"""
    mac: str
    first_seen: datetime
    last_seen: datetime
    signals: List[int] = field(default_factory=list)
    locations: List[dict] = field(default_factory=list)
    probe_count: int = 0
    probed_ssids: Set[str] = field(default_factory=set)
    associated: bool = False
    deauth_count: int = 0
    manufacturer: str = ""
    device_type: str = ""
    flags: Set[str] = field(default_factory=set)

    @property
    def duration_seen(self) -> float:
        """How long has this device been visible (seconds)"""
        return (self.last_seen - self.first_seen).total_seconds()

    @property
    def avg_signal(self) -> float:
        """Average signal strength"""
        return sum(self.signals) / len(self.signals) if self.signals else -100

    @property
    def max_signal(self) -> int:
        """Strongest signal seen"""
        return max(self.signals) if self.signals else -100

    @property
    def is_suspicious(self) -> bool:
        """Does this device have any suspicious flags?"""
        return len(self.flags) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export"""
        return {
            "mac": self.mac,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "duration_seconds": self.duration_seen,
            "signal_avg": self.avg_signal,
            "signal_max": self.max_signal,
            "signal_readings": self.signals[-20:],  # Last 20 readings
            "locations": self.locations[-20:],  # Last 20 locations
            "probe_count": self.probe_count,
            "probed_ssids": list(self.probed_ssids),
            "associated": self.associated,
            "deauth_count": self.deauth_count,
            "manufacturer": self.manufacturer,
            "device_type": self.device_type,
            "flags": list(self.flags),
            "is_suspicious": self.is_suspicious
        }


class AttackerHunter:
    """Main attacker hunting engine"""

    def __init__(self, config: dict):
        self.config = config
        self.devices: Dict[str, DeviceTracking] = {}
        self.suspicious_devices: Dict[str, DeviceTracking] = {}
        self.alerts: List[dict] = []
        self.running = False
        self.start_time = None
        self.script_dir = Path(__file__).parent

        # Set up logging
        self.log_path = self.script_dir / config["log_file"]
        self.data_path = self.script_dir / config["data_file"]

    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)

        with open(self.log_path, "a") as f:
            f.write(log_line + "\n")

    def alert(self, device: DeviceTracking, reason: str):
        """Trigger alert for suspicious device"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "mac": device.mac,
            "reason": reason,
            "flags": list(device.flags),
            "signal": device.max_signal,
            "duration": device.duration_seen,
            "locations": device.locations[-5:] if device.locations else []
        }
        self.alerts.append(alert_data)

        self.log(f"ALERT: {reason} - MAC: {device.mac}, Signal: {device.max_signal}dBm", "ALERT")

        # Sound alert if enabled
        if self.config["alert_sound"]:
            self.play_alert_sound()

        # Add to suspicious devices
        self.suspicious_devices[device.mac] = device

        # Save immediately
        self.save_data()

    def play_alert_sound(self):
        """Play alert sound on macOS"""
        try:
            # Use macOS say command for audio alert
            subprocess.Popen(
                ["say", "-v", "Samantha", "Suspicious device detected"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Also play system alert sound
            subprocess.Popen(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass  # Ignore sound errors

    def fetch_kismet_devices(self) -> List[dict]:
        """Fetch current devices from Kismet API"""
        try:
            import urllib.request
            import base64

            url = f"{self.config['kismet_api']}/devices/views/all/devices.json"

            # Set up authentication
            credentials = f"{self.config['kismet_user']}:{self.config['kismet_pass']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            request = urllib.request.Request(url)
            request.add_header("Authorization", f"Basic {encoded_credentials}")

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data

        except Exception as e:
            self.log(f"Error fetching Kismet data: {e}", "ERROR")
            return []

    def fetch_kismet_alerts(self) -> List[dict]:
        """Fetch alerts from Kismet (deauth detections, etc.)"""
        try:
            import urllib.request
            import base64

            url = f"{self.config['kismet_api']}/alerts/wrapped/last-time/0/alerts.json"

            credentials = f"{self.config['kismet_user']}:{self.config['kismet_pass']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            request = urllib.request.Request(url)
            request.add_header("Authorization", f"Basic {encoded_credentials}")

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data.get("kismet.alert.list", [])

        except Exception as e:
            self.log(f"Error fetching alerts: {e}", "ERROR")
            return []

    def extract_device_info(self, device_data: dict) -> Optional[dict]:
        """Extract relevant info from Kismet device data"""
        try:
            mac = device_data.get("kismet.device.base.macaddr", "")
            if not mac:
                return None

            # Get location data
            location = device_data.get("kismet.device.base.location", {})
            loc_fix = location.get("kismet.common.location.loc_fix", 0)

            lat, lon = 0, 0
            if loc_fix >= 2:
                last_loc = location.get("kismet.common.location.last", {})
                geopoint = last_loc.get("kismet.common.location.geopoint", [0, 0])
                if geopoint and len(geopoint) >= 2:
                    lon, lat = geopoint[0], geopoint[1]

            # Get signal
            signal_data = device_data.get("kismet.device.base.signal", {})
            signal = signal_data.get("kismet.common.signal.last_signal", -100)

            # Get probed SSIDs
            probed_ssids = set()
            dot11 = device_data.get("dot11.device", {})
            probed_list = dot11.get("dot11.device.probed_ssid_map", [])
            for probe in probed_list:
                ssid = probe.get("dot11.probedssid.ssid", "")
                if ssid:
                    probed_ssids.add(ssid)

            # Check if associated
            associated = bool(dot11.get("dot11.device.last_bssid", ""))

            # Get manufacturer
            manuf = device_data.get("kismet.device.base.manuf", "Unknown")

            # Get device type
            dev_type = device_data.get("kismet.device.base.type", "Unknown")

            # Get packet counts
            packets = device_data.get("kismet.device.base.packets.total", 0)

            return {
                "mac": mac,
                "signal": signal,
                "lat": lat,
                "lon": lon,
                "probed_ssids": probed_ssids,
                "associated": associated,
                "manufacturer": manuf,
                "device_type": dev_type,
                "packets": packets
            }

        except Exception as e:
            return None

    def analyze_device(self, device_info: dict) -> DeviceTracking:
        """Analyze a device and update tracking"""
        mac = device_info["mac"]
        now = datetime.now()

        # Get or create tracking record
        if mac in self.devices:
            tracking = self.devices[mac]
            tracking.last_seen = now
        else:
            tracking = DeviceTracking(
                mac=mac,
                first_seen=now,
                last_seen=now
            )
            self.devices[mac] = tracking

        # Update tracking data
        tracking.signals.append(device_info["signal"])
        if device_info["lat"] != 0 and device_info["lon"] != 0:
            tracking.locations.append({
                "lat": device_info["lat"],
                "lon": device_info["lon"],
                "signal": device_info["signal"],
                "timestamp": now.isoformat()
            })

        tracking.probed_ssids.update(device_info["probed_ssids"])
        tracking.associated = device_info["associated"]
        tracking.manufacturer = device_info["manufacturer"]
        tracking.device_type = device_info["device_type"]
        tracking.probe_count = device_info["packets"]

        return tracking

    def check_suspicious_patterns(self, tracking: DeviceTracking):
        """Check device for suspicious patterns"""
        patterns = self.config["suspicious_patterns"]

        # Check for targeting our networks
        if patterns["targeting_our_networks"]:
            target_networks = set(n.lower() for n in self.config["target_networks"])
            probed_lower = set(s.lower() for s in tracking.probed_ssids)

            if target_networks & probed_lower:
                matched = target_networks & probed_lower
                tracking.flags.add(f"TARGETING_OUR_NETWORKS:{','.join(matched)}")

        # Check for strong signal (device is close)
        if tracking.max_signal > self.config["strong_signal_threshold"]:
            tracking.flags.add(f"STRONG_SIGNAL:{tracking.max_signal}dBm")

        # Check for no association (probing but never connecting)
        if patterns["no_association"]:
            if tracking.probed_ssids and not tracking.associated:
                if tracking.probe_count > 10:  # Has been probing
                    tracking.flags.add("NO_ASSOCIATION")

        # Check for known attacker OUI
        mac_prefix = tracking.mac[:8].upper()
        for oui in self.config["known_attacker_ouis"]:
            if mac_prefix == oui.upper():
                tracking.flags.add(f"KNOWN_ATTACKER_OUI:{oui}")

        # Check for locally administered address (randomized/spoofed MAC)
        second_char = tracking.mac[1].lower()
        if second_char in ['2', '6', 'a', 'e']:
            tracking.flags.add("RANDOMIZED_MAC")

    def check_disappeared_devices(self):
        """Check for devices that appeared briefly then disappeared"""
        now = datetime.now()
        threshold = self.config["brief_appearance_threshold"]

        for mac, tracking in list(self.devices.items()):
            time_since_seen = (now - tracking.last_seen).total_seconds()

            # Device hasn't been seen in a while
            if time_since_seen > 60:  # Not seen in last minute
                duration = tracking.duration_seen

                # Was it a brief appearance?
                if duration < threshold and duration > 5:  # Between 5 sec and 5 min
                    if "BRIEF_APPEARANCE" not in tracking.flags:
                        tracking.flags.add(f"BRIEF_APPEARANCE:{int(duration)}s")

                        # If it was also targeting our networks, high priority alert
                        if any("TARGETING" in f for f in tracking.flags):
                            self.alert(
                                tracking,
                                f"Brief appearance ({int(duration)}s) targeting our networks"
                            )
                        elif tracking.is_suspicious:
                            self.alert(
                                tracking,
                                f"Brief suspicious device ({int(duration)}s)"
                            )

    def process_kismet_alerts(self, alerts: List[dict]):
        """Process Kismet alerts for deauth/disassoc events"""
        for alert in alerts:
            alert_type = alert.get("kismet.alert.header", "")

            if "DEAUTH" in alert_type.upper() or "DISASSOC" in alert_type.upper():
                # Extract source MAC from alert text
                text = alert.get("kismet.alert.text", "")
                # Try to find MAC in the alert
                import re
                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', text)

                if mac_match:
                    mac = mac_match.group(0).upper()

                    if mac in self.devices:
                        tracking = self.devices[mac]
                        tracking.deauth_count += 1
                        tracking.flags.add(f"DEAUTH_SOURCE:{tracking.deauth_count}")

                        if tracking.deauth_count == 1:
                            self.alert(tracking, "Device sending deauth frames!")

    def save_data(self):
        """Save current detection data to file"""
        data = {
            "last_updated": datetime.now().isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_devices_seen": len(self.devices),
            "suspicious_devices": len(self.suspicious_devices),
            "alerts": self.alerts[-100:],  # Last 100 alerts
            "suspicious_device_details": {
                mac: tracking.to_dict()
                for mac, tracking in self.suspicious_devices.items()
            },
            "all_flagged_devices": {
                mac: tracking.to_dict()
                for mac, tracking in self.devices.items()
                if tracking.is_suspicious
            }
        }

        with open(self.data_path, "w") as f:
            json.dump(data, f, indent=2)

    def print_status(self):
        """Print current hunting status"""
        suspicious_count = sum(1 for d in self.devices.values() if d.is_suspicious)

        print("\n" + "=" * 60)
        print(f"ATTACKER HUNTER STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        print(f"Devices tracked: {len(self.devices)}")
        print(f"Suspicious devices: {suspicious_count}")
        print(f"Alerts triggered: {len(self.alerts)}")

        if self.suspicious_devices:
            print("\nSUSPICIOUS DEVICES:")
            for mac, tracking in self.suspicious_devices.items():
                print(f"  {mac}: {', '.join(tracking.flags)}")

        print("=" * 60 + "\n")

    def run(self):
        """Main hunting loop"""
        self.running = True
        self.start_time = datetime.now()

        self.log("=" * 60)
        self.log("ATTACKER HUNTER STARTED")
        self.log(f"Monitoring for attacks on: {', '.join(self.config['target_networks'])}")
        self.log("=" * 60)

        iteration = 0

        try:
            while self.running:
                iteration += 1

                # Fetch current devices
                devices = self.fetch_kismet_devices()

                for device_data in devices:
                    device_info = self.extract_device_info(device_data)
                    if device_info:
                        tracking = self.analyze_device(device_info)
                        self.check_suspicious_patterns(tracking)

                # Check for devices that disappeared
                self.check_disappeared_devices()

                # Process Kismet alerts (deauth detection)
                alerts = self.fetch_kismet_alerts()
                if alerts:
                    self.process_kismet_alerts(alerts)

                # Periodic status update
                if iteration % 12 == 0:  # Every minute (12 * 5 seconds)
                    self.print_status()
                    self.save_data()

                time.sleep(self.config["poll_interval"])

        except KeyboardInterrupt:
            self.log("Received interrupt signal")
        finally:
            self.running = False
            self.save_data()
            self.log("Attacker Hunter stopped")
            self.print_final_report()

    def print_final_report(self):
        """Print final summary report"""
        print("\n" + "=" * 60)
        print("ATTACKER HUNTER - FINAL REPORT")
        print("=" * 60)

        if self.start_time:
            duration = datetime.now() - self.start_time
            print(f"Duration: {duration}")

        print(f"Total devices seen: {len(self.devices)}")
        print(f"Suspicious devices: {len(self.suspicious_devices)}")
        print(f"Alerts triggered: {len(self.alerts)}")

        # Devices that targeted our networks
        targeting = [d for d in self.devices.values()
                     if any("TARGETING" in f for f in d.flags)]
        if targeting:
            print(f"\nDEVICES THAT TARGETED OUR NETWORKS ({len(targeting)}):")
            for d in targeting:
                print(f"  {d.mac}")
                print(f"    Manufacturer: {d.manufacturer}")
                print(f"    Max Signal: {d.max_signal} dBm")
                print(f"    Duration seen: {d.duration_seen:.0f}s")
                print(f"    Probed SSIDs: {', '.join(d.probed_ssids)}")
                print(f"    Flags: {', '.join(d.flags)}")
                if d.locations:
                    loc = d.locations[-1]
                    print(f"    Last location: {loc['lat']:.6f}N, {abs(loc['lon']):.6f}W")
                print()

        # Brief appearances
        brief = [d for d in self.devices.values()
                 if any("BRIEF" in f for f in d.flags)]
        if brief:
            print(f"\nBRIEF APPEARANCES ({len(brief)}):")
            for d in brief:
                print(f"  {d.mac} - {d.duration_seen:.0f}s - Flags: {', '.join(d.flags)}")

        # Deauth sources
        deauth = [d for d in self.devices.values()
                  if any("DEAUTH" in f for f in d.flags)]
        if deauth:
            print(f"\nDEAUTH SOURCES ({len(deauth)}):")
            for d in deauth:
                print(f"  {d.mac} - {d.deauth_count} deauths - Signal: {d.max_signal}dBm")
                if d.locations:
                    loc = d.locations[-1]
                    print(f"    Location: {loc['lat']:.6f}N, {abs(loc['lon']):.6f}W")

        print("\n" + "=" * 60)
        print(f"Full data saved to: {self.data_path}")
        print("=" * 60)


def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           CYT ATTACKER HUNTER v1.0                        ║
    ║   Automated Threat Detection & Investigation              ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Monitoring for:                                          ║
    ║  - Brief appearances (attack and disappear)               ║
    ║  - Deauth/disassociation sources                          ║
    ║  - Devices probing for your networks                      ║
    ║  - Randomized/spoofed MACs                                ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    hunter = AttackerHunter(CONFIG)

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down...")
        hunter.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    hunter.run()


if __name__ == "__main__":
    main()
