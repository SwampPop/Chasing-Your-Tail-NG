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

        self.thresholds = {
            'min_appearances': 3,
            'min_time_span_hours': 1.0,
            'min_persistence_score': 0.5,
            'multi_location_bonus': 0.3,
            'threat_level_high': 0.8,
            'threat_level_critical': 0.9
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
