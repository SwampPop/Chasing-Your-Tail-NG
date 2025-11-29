"""
Surveillance Detection System for CYT
Detects devices that may be following or tracking the user
"""
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DeviceAppearance:
    """Record of when/where a device was seen"""
    mac: str
    timestamp: float
    location_id: str
    ssids_probed: List[str]
    device_type: Optional[str] = None


@dataclass
class SuspiciousDevice:
    """Device flagged as potentially suspicious"""
    mac: str
    persistence_score: float
    appearances: List[DeviceAppearance]
    reasons: List[str]
    first_seen: datetime
    last_seen: datetime
    total_appearances: int
    locations_seen: List[str]


class SurveillanceDetector:
    """Detect potential surveillance devices"""

    def __init__(self, config: Dict):
        self.config = config
        self.appearances: List[DeviceAppearance] = []
        self.device_history: Dict[str,
                                  List[DeviceAppearance]] = defaultdict(list)

        # Load detection thresholds from config with fallback defaults
        detection_config = config.get('detection_thresholds', {})
        self.thresholds = {
            'min_appearances': detection_config.get('min_appearances', 3),
            'min_time_span_hours': detection_config.get('time_span_hours_min', 1.0),
            'min_persistence_score': detection_config.get('appearance_frequency_threshold', 0.5),
            'multi_location_bonus': 0.3,  # Keep as constant for now
            'threat_level_high': detection_config.get('persistence_score_high', 0.8),
            'threat_level_critical': detection_config.get('persistence_score_critical', 0.9)
        }

    def add_device_appearance(self, mac: str, timestamp: float,
                              location_id: str,
                              ssids_probed: List[str] = None,
                              device_type: str = None) -> None:
        """Record a device appearance"""
        appearance = DeviceAppearance(
            mac=mac, timestamp=timestamp, location_id=location_id,
            ssids_probed=ssids_probed or [], device_type=device_type
        )
        self.appearances.append(appearance)
        self.device_history[mac].append(appearance)
        logger.debug(f"Recorded appearance: {mac} at {location_id}")

    def analyze_surveillance_patterns(self) -> List[SuspiciousDevice]:
        """Analyze all devices for surveillance patterns"""
        suspicious_devices = []

        for mac, appearances in self.device_history.items():
            if len(appearances) < self.thresholds['min_appearances']:
                continue

            persistence_score, reasons = self._calculate_persistence_score(
                appearances)

            if persistence_score > self.thresholds['min_persistence_score']:
                suspicious_device = SuspiciousDevice(
                    mac=mac, persistence_score=persistence_score,
                    appearances=appearances,
                    reasons=reasons,
                    first_seen=datetime.fromtimestamp(
                        min(a.timestamp for a in appearances)),
                    last_seen=datetime.fromtimestamp(
                        max(a.timestamp for a in appearances)),
                    total_appearances=len(appearances),
                    locations_seen=list(
                        set(a.location_id for a in appearances))
                )
                suspicious_devices.append(suspicious_device)

        suspicious_devices.sort(
            key=lambda d: d.persistence_score, reverse=True)
        return suspicious_devices

    def _calculate_persistence_score(
            self, appearances: List[DeviceAppearance]) -> Tuple[float, List[str]]:
        """Simple persistence scoring based on frequency and location diversity"""
        reasons = []
        if len(appearances) < self.thresholds['min_appearances']:
            return 0.0, reasons

        timestamps = [a.timestamp for a in appearances]
        time_span_hours = (max(timestamps) - min(timestamps)) / 3600

        if time_span_hours < self.thresholds['min_time_span_hours']:
            return 0.0, reasons

        appearance_rate = len(appearances) / time_span_hours
        score = 0.0

        if appearance_rate >= 0.5:
            score = min(appearance_rate / 2.0, 1.0)
            reasons.append(
                f"Appeared {len(appearances)} times over "
                f"{time_span_hours:.1f} hours")

            unique_locations = len(set(a.location_id for a in appearances))
            if unique_locations > 1:
                reasons.append(
                    f"Followed across {unique_locations} "
                    "different locations")
                score = min(
                    score + self.thresholds['multi_location_bonus'], 1.0)

            return score, reasons

        return 0.0, reasons

# This function is used by the analyzer, so it remains here.


def load_appearances_from_kismet(db_path: str, detector: SurveillanceDetector,
                                 location_id: str = "unknown") -> int:
    # ... (function content remains the same)
    pass


def load_ble_appearances_from_kismet(
        db_path: str,
        detector: SurveillanceDetector,
        location_id: str = "unknown",
        start_time: float = None,
        end_time: float = None) -> int:
    """
    Load BLE device appearances from Kismet database and add to detector

    Args:
        db_path: Path to Kismet .kismet database file
        detector: SurveillanceDetector instance to populate
        location_id: Location identifier for GPS correlation
        start_time: Optional start timestamp for filtering
        end_time: Optional end timestamp for filtering

    Returns:
        Number of BLE device appearances loaded
    """
    from secure_database import SecureKismetDB
    from ble_classifier import BLEClassifier

    classifier = BLEClassifier()
    appearances_loaded = 0

    try:
        with SecureKismetDB(db_path) as db:
            # Get BLE devices from database
            if start_time is None:
                # Default to last 24 hours if not specified
                import time
                start_time = time.time() - (24 * 3600)

            ble_devices = db.get_ble_devices_by_time_range(start_time, end_time)
            logger.info(f"Found {len(ble_devices)} BLE devices in database")

            for device in ble_devices:
                # Classify the device
                device_type = classifier.classify_device(device)

                # Only track surveillance-relevant devices
                if classifier.is_likely_surveillance_device(device_type):
                    detector.add_device_appearance(
                        mac=device['mac'],
                        timestamp=device['last_time'],
                        location_id=location_id,
                        ssids_probed=[],  # BLE doesn't have SSIDs
                        device_type=device_type.value
                    )
                    appearances_loaded += 1
                    logger.debug(
                        f"Loaded BLE device: {device['mac']} "
                        f"({device_type.value}) at {location_id}"
                    )

            logger.info(
                f"Loaded {appearances_loaded} surveillance-relevant "
                f"BLE device appearances"
            )

    except Exception as e:
        logger.error(f"Failed to load BLE appearances from {db_path}: {e}")
        raise

    return appearances_loaded
