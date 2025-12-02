"""
Secure Main Logic for CYT
Core monitoring engine that handles device tracking, persistence detection,
and immediate threat alerting (Drones).
"""
import logging
import sqlite3
import time
from datetime import datetime
from typing import List, Set, Dict, Any, Optional
from secure_database import SecureKismetDB, SecureTimeWindows
from behavioral_drone_detector import BehavioralDroneDetector
from behavioral_report_generator import BehavioralReportGenerator, BehavioralDetection

logger = logging.getLogger(__name__)

# Import AlertManager - make it optional for backwards compatibility
try:
    from alert_manager import AlertManager
    ALERT_MANAGER_AVAILABLE = True
except ImportError:
    ALERT_MANAGER_AVAILABLE = False
    logger.warning("AlertManager not available - alerts will only be logged")

# ANSI Colors for Console Alerts
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Known Drone Manufacturer OUIs
DRONE_OUIS = {
    "60:60:1F": "DJI Technology",
    "34:D2:62": "DJI Technology",
    "40:6C:8F": "DJI Technology",
    "58:6B:14": "DJI Technology",
    "E4:0F:53": "DJI Technology",
    "90:03:B7": "Parrot SA",
    "A0:14:3D": "Parrot SA",
    "00:12:1C": "Parrot SA",
    "00:1C:27": "Autel Robotics",
    "D8:3A:DD": "Skydio",
    "E0:B6:F5": "Yuneec",
    "F4:DD:9E": "GoPro (Karma)",
}


class SecureCYTMonitor:
    """Secure monitoring logic for CYT"""

    def __init__(self, config: dict, ignore_list: List[str],
                 ssid_ignore_list: List[str], log_file,
                 alert_manager: Optional['AlertManager'] = None):
        self.config = config
        # Convert to set for O(1) lookup
        self.ignore_list = set(mac.upper() for mac in ignore_list)
        self.ssid_ignore_list = set(ssid_ignore_list)
        self.log_file = log_file
        self.time_manager = SecureTimeWindows(config)

        # Alert Manager integration (optional but recommended)
        self.alert_manager = alert_manager
        if not alert_manager and ALERT_MANAGER_AVAILABLE:
            logger.info("AlertManager not provided, creating default instance")
            try:
                self.alert_manager = AlertManager()
            except Exception as e:
                logger.warning(f"Could not initialize AlertManager: {e}")
                self.alert_manager = None

        # Initialize tracking lists
        self.past_five_mins_macs: Set[str] = set()
        self.five_ten_min_ago_macs: Set[str] = set()
        self.ten_fifteen_min_ago_macs: Set[str] = set()
        self.fifteen_twenty_min_ago_macs: Set[str] = set()

        self.past_five_mins_ssids: Set[str] = set()
        self.five_ten_min_ago_ssids: Set[str] = set()
        self.ten_fifteen_min_ago_ssids: Set[str] = set()
        self.fifteen_twenty_min_ago_ssids: Set[str] = set()

        # Alert throttling (prevent spamming the same alert)
        self.alert_cooldowns: Dict[str, float] = {}

        # Detection tracking for history recording
        self.recent_detections: List[Dict[str, Any]] = []

        # Behavioral Drone Detector
        behavior_config = self.config.get('behavioral_drone_detection', {})
        if behavior_config.get('enabled', False):
            self.behavioral_detector = BehavioralDroneDetector(config)
            self.behavioral_report_generator = BehavioralReportGenerator(config)
            logger.info("Behavioral drone detection enabled")
            logger.info("Behavioral report generator initialized")
        else:
            self.behavioral_detector = None
            self.behavioral_report_generator = None
            logger.info("Behavioral drone detection disabled")

    def _log_to_console(self, message: str) -> None:
        """Writes to stdout and the log file if available"""
        # Print to screen (with colors if applicable)
        print(message)

        # Write clean text to log file (strip ANSI codes for file)
        if self.log_file:
            clean_msg = message.replace(RED, "").replace(
                GREEN, "").replace(YELLOW, "").replace(RESET, "")
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_file.write(f"[{timestamp}] {clean_msg}\n")
            self.log_file.flush()

    def check_drone_threat(self, mac: str) -> str | None:
        """Fast lookup for drone manufacturers"""
        try:
            prefix = mac.upper()[:8]
            return DRONE_OUIS.get(prefix)
        except Exception:
            return None

    def _record_detection(self, mac: str, detection_type: str, threat_score: int = 0,
                          lat: Optional[float] = None, lon: Optional[float] = None) -> None:
        """Record a detection for later history archiving"""
        detection = {
            'mac': mac,
            'timestamp': time.time(),
            'detection_type': detection_type,
            'threat_score': threat_score,
            'location_id': None  # Will be set later if GPS available
        }
        if lat and lon:
            detection['latitude'] = lat
            detection['longitude'] = lon
        self.recent_detections.append(detection)

    def get_and_clear_detections(self) -> List[Dict[str, Any]]:
        """Get all recent detections and clear the buffer"""
        detections = self.recent_detections.copy()
        self.recent_detections.clear()
        return detections

    def initialize_tracking_lists(self, db: SecureKismetDB) -> None:
        """Initialize all tracking lists securely"""
        try:
            boundaries = self.time_manager.get_time_boundaries()

            # Initialize MAC tracking lists
            self._initialize_mac_lists(db, boundaries)

            # Initialize SSID tracking lists
            self._initialize_ssid_lists(db, boundaries)

            self._log_initialization_stats()

        except (sqlite3.Error, RuntimeError) as e:
            logger.error(f"Database error initializing tracking lists: {e}")
            raise
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                f"Configuration or data format error initializing tracking lists: {e}")
            raise

    def _initialize_mac_lists(self, db: SecureKismetDB, boundaries: dict[str, float]) -> None:
        """Initialize MAC address tracking lists"""
        # Past 5 minutes
        macs = db.get_mac_addresses_by_time_range(boundaries['recent_time'])
        self.past_five_mins_macs = self._filter_macs(macs)

        # 5-10 minutes ago
        macs = db.get_mac_addresses_by_time_range(
            boundaries['medium_time'], boundaries['recent_time'])
        self.five_ten_min_ago_macs = self._filter_macs(macs)

        # 10-15 minutes ago
        macs = db.get_mac_addresses_by_time_range(
            boundaries['old_time'], boundaries['medium_time'])
        self.ten_fifteen_min_ago_macs = self._filter_macs(macs)

        # 15-20 minutes ago
        macs = db.get_mac_addresses_by_time_range(
            boundaries['oldest_time'], boundaries['old_time'])
        self.fifteen_twenty_min_ago_macs = self._filter_macs(macs)

    def _initialize_ssid_lists(self, db: SecureKismetDB,
                               boundaries: Dict[str, float]) -> None:
        """Initialize SSID tracking lists"""
        # Past 5 minutes
        probes = db.get_probe_requests_by_time_range(
            boundaries['recent_time'])
        self.past_five_mins_ssids = self._filter_ssids(
            [p['ssid'] for p in probes])

        # 5-10 minutes ago
        probes = db.get_probe_requests_by_time_range(
            boundaries['medium_time'], boundaries['recent_time'])
        self.five_ten_min_ago_ssids = self._filter_ssids(
            [p['ssid'] for p in probes])

        # 10-15 minutes ago
        probes = db.get_probe_requests_by_time_range(
            boundaries['old_time'], boundaries['medium_time'])
        self.ten_fifteen_min_ago_ssids = self._filter_ssids(
            [p['ssid'] for p in probes])

        # 15-20 minutes ago
        probes = db.get_probe_requests_by_time_range(
            boundaries['oldest_time'], boundaries['old_time'])
        self.fifteen_twenty_min_ago_ssids = self._filter_ssids(
            [p['ssid'] for p in probes])

    def _filter_macs(self, mac_list: List[str]) -> Set[str]:
        """Filter MAC addresses against ignore list"""
        return {mac.upper() for mac in mac_list
                if mac.upper() not in self.ignore_list}

    def _filter_ssids(self, ssid_list: List[str]) -> Set[str]:
        """Filter SSIDs against ignore list"""
        return {ssid for ssid in ssid_list
                if ssid and ssid not in self.ssid_ignore_list}

    def _log_initialization_stats(self) -> None:
        """Log initialization statistics"""
        mac_stats = [
            ("Past 5 minutes", len(self.past_five_mins_macs)),
            ("5-10 minutes ago", len(self.five_ten_min_ago_macs)),
            ("10-15 minutes ago", len(self.ten_fifteen_min_ago_macs)),
            ("15-20 minutes ago", len(self.fifteen_twenty_min_ago_macs))
        ]

        ssid_stats = [
            ("Past 5 minutes", len(self.past_five_mins_ssids)),
            ("5-10 minutes ago", len(self.five_ten_min_ago_ssids)),
            ("10-15 minutes ago", len(self.ten_fifteen_min_ago_ssids)),
            ("15-20 minutes ago", len(self.fifteen_twenty_min_ago_ssids))
        ]

        for period, count in mac_stats:
            message = f"{count} MACs added to the {period} list"
            print(message)
            self.log_file.write(f"{message}\n")

        for period, count in ssid_stats:
            message = f"{count} Probed SSIDs added to the {period} list"
            print(message)
            self.log_file.write(f"{message}\n")

    def process_current_activity(self, db: SecureKismetDB) -> None:
        """Process current activity and detect matches"""
        try:
            boundaries = self.time_manager.get_time_boundaries()
            now = time.time()

            # Get current devices and probes
            current_devices = db.get_devices_by_time_range(
                boundaries['current_time'])

            for device in current_devices:
                mac = device['mac']
                device_data = device.get('device_data', {})

                if not mac:
                    continue

                # THREAT CHECK 1: DRONE HUNTER
                drone_manuf = self.check_drone_threat(mac)
                if drone_manuf:
                    # Check cooldown (alert max once every 30 seconds per drone)
                    last_alert = self.alert_cooldowns.get(mac, 0)
                    if now - last_alert > 30:
                        alert_msg = (
                            f"{RED}[!!!] DRONE DETECTED [!!!]{RESET}\n"
                            f"{RED}   Target: {drone_manuf}{RESET}\n"
                            f"{RED}   MAC:    {mac}{RESET}\n"
                            f"{RED}   Time:   {datetime.now().strftime('%H:%M:%S')}{RESET}"
                        )
                        self._log_to_console(alert_msg)

                        # Send alert via AlertManager (audio + Telegram)
                        if self.alert_manager:
                            clean_msg = f"DRONE DETECTED: {drone_manuf} - MAC: {mac}"
                            try:
                                self.alert_manager.send_alert(clean_msg, priority="critical")
                                logger.info("Drone alert sent via AlertManager")
                            except Exception as e:
                                logger.error(f"Failed to send drone alert: {e}")

                        # Record detection for history
                        self._record_detection(
                            mac,
                            detection_type=f"DRONE:{drone_manuf}",
                            lat=device.get('lat'),
                            lon=device.get('lon')
                        )

                        self.alert_cooldowns[mac] = now

                # THREAT CHECK 2: BEHAVIORAL DRONE DETECTION
                if self.behavioral_detector:
                    # Prepare device data for behavioral analysis
                    analysis_data = {
                        'mac': mac,
                        'signal': device_data.get('kismet.device.base.signal', {}).get('kismet.common.signal.last_signal', -100),
                        'lat': device.get('lat'),
                        'lon': device.get('lon'),
                        'channel': device_data.get('kismet.device.base.channel', 0),
                        'type': device_data.get('kismet.device.base.type', 'unknown'),
                        'num_clients': device_data.get('kismet.device.base.num_associated_clients', 0)
                    }

                    # Update device history
                    self.behavioral_detector.update_device_history(mac, analysis_data)

                    # Analyze for behavioral drone patterns
                    confidence, patterns = self.behavioral_detector.analyze_device(mac)
                    confidence_threshold = self.config.get('behavioral_drone_detection', {}).get('confidence_threshold', 0.60)

                    if confidence >= confidence_threshold:
                        # Check cooldown (alert max once every 60 seconds per behavioral drone)
                        last_alert = self.alert_cooldowns.get(f"behavioral_{mac}", 0)
                        if now - last_alert > 60:
                            alert_msg = (
                                f"{YELLOW}[!!!] BEHAVIORAL DRONE DETECTED [!!!]{RESET}\n"
                                f"{YELLOW}   MAC:        {mac}{RESET}\n"
                                f"{YELLOW}   Confidence: {confidence:.1%}{RESET}\n"
                                f"{YELLOW}   Time:       {datetime.now().strftime('%H:%M:%S')}{RESET}\n"
                                f"{YELLOW}   Patterns:   {sum(1 for p in patterns.values() if p.get('detected'))}/9 detected{RESET}"
                            )
                            self._log_to_console(alert_msg)

                            # Send alert via AlertManager
                            if self.alert_manager:
                                clean_msg = f"BEHAVIORAL DRONE DETECTED: {mac} - Confidence: {confidence:.1%}"
                                try:
                                    self.alert_manager.send_alert(clean_msg, priority="high")
                                    logger.info("Behavioral drone alert sent via AlertManager")
                                except Exception as e:
                                    logger.error(f"Failed to send behavioral drone alert: {e}")

                            # Record detection with confidence score
                            self._record_detection(
                                mac,
                                detection_type=f"BEHAVIORAL_DRONE",
                                threat_score=int(confidence * 100),  # Convert to 0-100 scale
                                lat=device.get('lat'),
                                lon=device.get('lon')
                            )

                            # Log detailed pattern summary
                            summary = self.behavioral_detector.get_detection_summary(mac, confidence, patterns)
                            logger.info(f"Behavioral drone details:\n{summary}")

                            # Generate detailed behavioral detection report
                            if self.behavioral_report_generator:
                                try:
                                    detection = BehavioralDetection(
                                        mac=mac,
                                        timestamp=now,
                                        confidence=confidence,
                                        patterns=patterns,
                                        device_history=self.behavioral_detector.device_history[mac],
                                        oui_manufacturer=analysis_data.get('manufacturer')
                                    )
                                    report_path = self.behavioral_report_generator.save_report(detection)
                                    logger.info(f"Behavioral detection report generated: {report_path}")
                                    self._log_to_console(
                                        f"{YELLOW}   Report:     {report_path}{RESET}"
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to generate behavioral detection report: {e}")

                            self.alert_cooldowns[f"behavioral_{mac}"] = now

                # Check for probe requests
                self._process_probe_requests(device_data, mac)

                # THREAT CHECK 3: PERSISTENCE (STALKER)
                self._process_mac_tracking(mac, now)

        except (sqlite3.Error, RuntimeError) as e:
            logger.error(f"Database error processing current activity: {e}")
        except (KeyError, TypeError, AttributeError) as e:
            logger.error(f"Data format error processing current activity: {e}")

    def _process_probe_requests(self, device_data: Dict, mac: str) -> None:
        """Process probe requests from device data"""
        if not device_data:
            return

        try:
            dot11_device = device_data.get('dot11.device', {})
            if not isinstance(dot11_device, dict):
                return

            probe_record = dot11_device.get(
                'dot11.device.last_probed_ssid_record', {})
            if not isinstance(probe_record, dict):
                return

            ssid = probe_record.get('dot11.probedssid.ssid', '')
            if not ssid or ssid in self.ssid_ignore_list:
                return

            # Log the probe
            message = f'Found a probe!: {ssid}'
            self.log_file.write(f'{message}\n')
            logger.info(f"Probe detected from {mac}: {ssid}")

            # Check against historical lists
            self._check_ssid_history(ssid)

        except (KeyError, TypeError, AttributeError) as e:
            logger.debug(f"No probe data for device {mac}: {e}")

    def _check_ssid_history(self, ssid: str) -> None:
        """Check SSID against historical tracking lists"""
        if ssid in self.five_ten_min_ago_ssids:
            message = f"Probe for {ssid} in 5 to 10 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(
                f"Repeated probe detected: {ssid} (5-10 min window)")

        if ssid in self.ten_fifteen_min_ago_ssids:
            message = f"Probe for {ssid} in 10 to 15 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(
                f"Repeated probe detected: {ssid} (10-15 min window)")

        if ssid in self.fifteen_twenty_min_ago_ssids:
            message = f"Probe for {ssid} in 15 to 20 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(
                f"Repeated probe detected: {ssid} (15-20 min window)")

    def _process_mac_tracking(self, mac: str, now: float) -> None:
        """Process MAC address tracking with persistence scoring"""
        if mac.upper() in self.ignore_list:
            return

        # Calculate threat score based on persistence across time buckets
        threat_score = 0
        if mac in self.past_five_mins_macs:
            threat_score += 1
        if mac in self.five_ten_min_ago_macs:
            threat_score += 2
        if mac in self.ten_fifteen_min_ago_macs:
            threat_score += 3
        if mac in self.fifteen_twenty_min_ago_macs:
            threat_score += 5

        # High persistence alert (Score >= 6 implies seen across multiple windows)
        if threat_score >= 6:
            last_alert = self.alert_cooldowns.get(f"stalk_{mac}", 0)
            if now - last_alert > 60:
                self._log_to_console(
                    f"{YELLOW}[!] PERSISTENT TARGET: {mac} (Score: {threat_score}){RESET}")

                # Send alert via AlertManager
                if self.alert_manager:
                    clean_msg = f"PERSISTENT TARGET DETECTED: {mac} - Threat Score: {threat_score}/11"
                    try:
                        self.alert_manager.send_alert(clean_msg, priority="high")
                        logger.info("Persistence alert sent via AlertManager")
                    except Exception as e:
                        logger.error(f"Failed to send persistence alert: {e}")

                # Record detection for history
                self._record_detection(
                    mac,
                    detection_type="PERSISTENT",
                    threat_score=threat_score
                )

                self.alert_cooldowns[f"stalk_{mac}"] = now

        # Check against historical lists for standard logging
        if mac in self.five_ten_min_ago_macs:
            message = f"{mac} in 5 to 10 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Device reappeared: {mac} (5-10 min window)")

        if mac in self.ten_fifteen_min_ago_macs:
            message = f"{mac} in 10 to 15 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Device reappeared: {mac} (10-15 min window)")

        if mac in self.fifteen_twenty_min_ago_macs:
            message = f"{mac} in 15 to 20 mins list"
            print(message)
            self.log_file.write(f"{message}\n")
            logger.warning(f"Device reappeared: {mac} (15-20 min window)")

    def rotate_tracking_lists(self, db: SecureKismetDB) -> None:
        """Rotate tracking lists and update with fresh data"""
        try:
            # Rotate MAC lists
            self.fifteen_twenty_min_ago_macs = self.ten_fifteen_min_ago_macs
            self.ten_fifteen_min_ago_macs = self.five_ten_min_ago_macs
            self.five_ten_min_ago_macs = self.past_five_mins_macs

            # Rotate SSID lists
            self.fifteen_twenty_min_ago_ssids = self.ten_fifteen_min_ago_ssids
            self.ten_fifteen_min_ago_ssids = self.five_ten_min_ago_ssids
            self.five_ten_min_ago_ssids = self.past_five_mins_ssids

            # Get fresh data for past 5 minutes
            boundaries = self.time_manager.get_time_boundaries()

            # Update past 5 minutes MAC list
            macs = db.get_mac_addresses_by_time_range(
                boundaries['recent_time'])
            self.past_five_mins_macs = self._filter_macs(macs)

            # Update past 5 minutes SSID list
            probes = db.get_probe_requests_by_time_range(
                boundaries['recent_time'])
            self.past_five_mins_ssids = self._filter_ssids(
                [p['ssid'] for p in probes])

            self._log_rotation_stats()

            # Clean up old behavioral detector history
            if self.behavioral_detector:
                max_age = self.config.get('behavioral_drone_detection', {}).get('history_cleanup_hours', 24)
                self.behavioral_detector.cleanup_old_history(max_age_hours=max_age)
                logger.debug(f"Behavioral detector history cleanup completed (max age: {max_age}h)")

        except (sqlite3.Error, RuntimeError) as e:
            logger.error(f"Database error rotating tracking lists: {e}")
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Data format error rotating tracking lists: {e}")

    def _log_rotation_stats(self) -> None:
        """Log rotation statistics"""
        print("Updated MAC tracking lists:")
        print(f"- 15-20 min ago: {len(self.fifteen_twenty_min_ago_macs)}")
        print(f"- 10-15 min ago: {len(self.ten_fifteen_min_ago_macs)}")
        print(f"- 5-10 min ago: {len(self.five_ten_min_ago_macs)}")
        print(f"- Current: {len(self.past_five_mins_macs)}")

        # Log to file
        self.log_file.write(
            f"{len(self.fifteen_twenty_min_ago_macs)} "
            "MACs moved to the 15-20 Min list\n")
        self.log_file.write(
            f"{len(self.ten_fifteen_min_ago_macs)} "
            "MACs moved to the 10-15 Min list\n")
        self.log_file.write(
            f"{len(self.five_ten_min_ago_macs)} "
            "MACs moved to the 5 to 10 mins ago list\n")

        print(
            f"{len(self.fifteen_twenty_min_ago_ssids)} "
            "Probed SSIDs moved to the 15 to 20 mins ago list")
        print(
            f"{len(self.ten_fifteen_min_ago_ssids)} "
            "Probed SSIDs moved to the 10 to 15 mins ago list")
        print(
            f"{len(self.five_ten_min_ago_ssids)} "
            "Probed SSIDs moved to the 5 to 10 mins ago list")

        self.log_file.write(
            f"{len(self.fifteen_twenty_min_ago_ssids)} "
            "Probed SSIDs moved to the 15 to 20 mins ago list\n")
        self.log_file.write(
            f"{len(self.ten_fifteen_min_ago_ssids)} "
            "Probed SSIDs moved to the 10 to 15 mins ago list\n")
        self.log_file.write(
            f"{len(self.five_ten_min_ago_ssids)} "
            "Probed SSIDs moved to the 5 to 10 mins ago list\n")
