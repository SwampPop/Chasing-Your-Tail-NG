#!/usr/bin/env python3
"""
WATCHDOG Camera Detector — Passive surveillance device detection module.

Detects IP cameras, ALPR systems, and surveillance infrastructure by:
1. MAC OUI matching against 70+ camera manufacturer prefixes
2. SSID pattern matching for camera setup/AP mode broadcasts
3. WiFi behavior analysis (static RSSI, 2.4GHz-only, non-randomized MAC)
4. Integration with DeFlock ALPR location data

Phase 1: Passive detection only (legal everywhere)
Phase 2: Active auditing (requires authorization — see WATCHDOG_CONOPS.md)

Integrates with CYT-NG as a detection module without breaking existing functionality.
"""
import fnmatch
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# Default paths relative to project root
PROJECT_ROOT = os.path.dirname(__file__)
DEFAULT_CAMERA_SIGS = os.path.join(PROJECT_ROOT, "config", "camera_signatures.yaml")
DEFAULT_DRONE_SIGS = os.path.join(PROJECT_ROOT, "config", "drone_signatures.yaml")


@dataclass
class CameraDetection:
    """A detected surveillance device."""
    mac: str
    manufacturer: str
    device_type: str  # 'camera', 'alpr', 'drone', 'ble_tracker', 'unknown'
    confidence: float  # 0.0-1.0
    ssid: str = ""
    rssi: int = -100
    channel: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    timestamp: float = 0.0
    detection_method: str = ""  # 'oui', 'ssid', 'behavior', 'combined'
    is_setup_mode: bool = False  # Camera broadcasting setup AP
    match_details: Dict = field(default_factory=dict)


class CameraDetector:
    """
    Passive surveillance device detector.

    Loads camera OUI prefixes and SSID patterns from YAML config,
    matches observed WiFi devices against the database.
    """

    # Characters indicating randomized MAC (local bit set)
    RANDOMIZED_INDICATORS = frozenset(['2', '6', 'a', 'e', 'A', 'E'])

    def __init__(self, camera_sigs_path: str = DEFAULT_CAMERA_SIGS,
                 drone_sigs_path: str = DEFAULT_DRONE_SIGS):
        self.camera_ouis: Dict[str, str] = {}
        self.chipset_indicators: Dict[str, str] = {}
        self.camera_ssid_patterns: Dict[str, List[str]] = {}
        self.alpr_ssid_patterns: List[str] = []
        self.detection_regex = None
        self.detections: List[CameraDetection] = []
        self.seen_macs: Dict[str, CameraDetection] = {}

        self._load_camera_signatures(camera_sigs_path)
        self._load_drone_signatures(drone_sigs_path)

        total_ouis = len(self.camera_ouis) + len(self.chipset_indicators)
        total_ssids = sum(len(v) for v in self.camera_ssid_patterns.values())
        logger.info(
            f"WATCHDOG: Loaded {total_ouis} OUI prefixes, "
            f"{total_ssids} camera SSID patterns, "
            f"{len(self.alpr_ssid_patterns)} ALPR patterns"
        )

    def _load_camera_signatures(self, path: str) -> None:
        """Load camera signature database from YAML."""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            self.camera_ouis = data.get("camera_oui_prefixes", {})
            self.chipset_indicators = data.get("chipset_camera_indicators", {})
            self.camera_ssid_patterns = data.get("camera_ssid_patterns", {})
            self.alpr_ssid_patterns = data.get("alpr_ssid_patterns", [])
            regex_str = data.get("detection_regex", "")
            if regex_str:
                self.detection_regex = re.compile(regex_str)
        except FileNotFoundError:
            logger.warning(f"Camera signatures not found: {path}")
        except Exception as e:
            logger.error(f"Error loading camera signatures: {e}")

    def _load_drone_signatures(self, path: str) -> None:
        """Load drone signatures and merge into detection database."""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            # Drone OUIs are handled by drone_signature_matcher.py
            # We only need the SSID patterns here for unified detection
        except FileNotFoundError:
            pass  # Drone signatures are optional
        except Exception as e:
            logger.debug(f"Drone signatures not loaded: {e}")

    def is_randomized_mac(self, mac: str) -> bool:
        """Check if MAC is randomized (local bit set)."""
        try:
            return len(mac) >= 2 and mac[1] in self.RANDOMIZED_INDICATORS
        except (IndexError, TypeError):
            return False

    def match_oui(self, mac: str) -> Optional[Tuple[str, str]]:
        """
        Match MAC against camera OUI database.

        Returns (manufacturer, source) or None.
        source is 'camera_oui' or 'chipset_indicator'.
        """
        if not mac or len(mac) < 8:
            return None
        prefix = mac[:8].upper()

        # Direct camera manufacturer match (high confidence)
        mfg = self.camera_ouis.get(prefix)
        if mfg:
            return (mfg, "camera_oui")

        # Chipset indicator match (medium confidence — needs corroboration)
        chipset = self.chipset_indicators.get(prefix)
        if chipset:
            return (chipset, "chipset_indicator")

        return None

    def match_ssid(self, ssid: str) -> Optional[Tuple[str, str, str]]:
        """
        Match SSID against camera and ALPR patterns.

        Returns (manufacturer, category, matched_pattern) or None.
        category is 'camera' or 'alpr'.
        """
        if not ssid:
            return None

        # Check ALPR patterns first (higher priority)
        for pattern in self.alpr_ssid_patterns:
            if fnmatch.fnmatch(ssid, pattern) or fnmatch.fnmatch(ssid.lower(), pattern.lower()):
                return ("ALPR", "alpr", pattern)

        # Check camera SSID patterns by manufacturer
        for manufacturer, patterns in self.camera_ssid_patterns.items():
            for pattern in patterns:
                if fnmatch.fnmatch(ssid, pattern) or fnmatch.fnmatch(ssid.lower(), pattern.lower()):
                    return (manufacturer, "camera", pattern)

        # Regex fallback for partial matches
        if self.detection_regex and self.detection_regex.search(ssid):
            return ("Unknown", "camera", "regex_match")

        return None

    def analyze_behavior(self, mac: str, rssi_history: List[int] = None,
                         channels: List[int] = None) -> Dict:
        """
        Analyze WiFi behavior to distinguish cameras from other devices.

        Returns dict with behavioral indicators.
        """
        indicators = {
            "is_static": False,
            "is_24ghz_only": False,
            "is_non_randomized": False,
            "is_always_on": False,
            "behavior_score": 0.0,
        }

        # Non-randomized MAC (cameras don't randomize)
        if not self.is_randomized_mac(mac):
            indicators["is_non_randomized"] = True
            indicators["behavior_score"] += 0.1

        # Static RSSI (camera doesn't move)
        if rssi_history and len(rssi_history) >= 5:
            mean_rssi = sum(rssi_history) / len(rssi_history)
            variance = sum((r - mean_rssi) ** 2 for r in rssi_history) / len(rssi_history)
            if variance < 4.0:  # Less than 2 dBm standard deviation
                indicators["is_static"] = True
                indicators["behavior_score"] += 0.15

        # 2.4GHz only (most cameras are 2.4GHz)
        if channels:
            if all(1 <= ch <= 14 for ch in channels):
                indicators["is_24ghz_only"] = True
                indicators["behavior_score"] += 0.05

        return indicators

    def detect(self, mac: str, ssid: str = "", rssi: int = -100,
               channel: int = 0, latitude: float = 0.0,
               longitude: float = 0.0,
               rssi_history: List[int] = None,
               channels: List[int] = None) -> Optional[CameraDetection]:
        """
        Analyze a device and determine if it's a surveillance device.

        Returns CameraDetection if detected, None if not suspicious.
        """
        confidence = 0.0
        manufacturer = "Unknown"
        device_type = "unknown"
        detection_method = ""
        is_setup = False
        details = {}

        # 1. OUI match
        oui_result = self.match_oui(mac)
        if oui_result:
            mfg, source = oui_result
            manufacturer = mfg
            if source == "camera_oui":
                confidence += 0.6
                device_type = "camera"
                detection_method = "oui"
                details["oui_match"] = mfg
            elif source == "chipset_indicator":
                confidence += 0.2
                details["chipset_match"] = mfg

        # 2. SSID match
        ssid_result = self.match_ssid(ssid)
        if ssid_result:
            mfg, category, pattern = ssid_result
            if manufacturer == "Unknown":
                manufacturer = mfg
            if category == "alpr":
                device_type = "alpr"
                confidence += 0.5
            else:
                device_type = "camera"
                confidence += 0.4
                is_setup = True  # Camera in AP/setup mode
            detection_method = detection_method + "+ssid" if detection_method else "ssid"
            details["ssid_match"] = {"manufacturer": mfg, "pattern": pattern}

        # 3. Behavioral analysis
        behavior = self.analyze_behavior(mac, rssi_history, channels)
        confidence += behavior["behavior_score"]
        if behavior["behavior_score"] > 0:
            detection_method = detection_method + "+behavior" if detection_method else "behavior"
            details["behavior"] = behavior

        # Clamp confidence
        confidence = min(confidence, 1.0)

        # Only report if confidence meets threshold
        if confidence < 0.3:
            return None

        detection = CameraDetection(
            mac=mac,
            manufacturer=manufacturer,
            device_type=device_type,
            confidence=confidence,
            ssid=ssid,
            rssi=rssi,
            channel=channel,
            latitude=latitude,
            longitude=longitude,
            timestamp=time.time(),
            detection_method=detection_method,
            is_setup_mode=is_setup,
            match_details=details,
        )

        # Update tracking
        if mac in self.seen_macs:
            existing = self.seen_macs[mac]
            # Update with stronger confidence if applicable
            if detection.confidence > existing.confidence:
                self.seen_macs[mac] = detection
            else:
                # Update RSSI and timestamp
                existing.rssi = rssi
                existing.timestamp = detection.timestamp
                return existing
        else:
            self.seen_macs[mac] = detection
            self.detections.append(detection)
            logger.warning(
                f"WATCHDOG: {device_type.upper()} detected — "
                f"{manufacturer} MAC:{mac} SSID:{ssid} "
                f"RSSI:{rssi} CH:{channel} Conf:{confidence:.0%}"
            )

        return detection

    def get_detections(self) -> List[CameraDetection]:
        """Return all detections."""
        return list(self.detections)

    def get_detection_summary(self) -> Dict:
        """Return summary statistics."""
        cameras = sum(1 for d in self.detections if d.device_type == "camera")
        alprs = sum(1 for d in self.detections if d.device_type == "alpr")
        drones = sum(1 for d in self.detections if d.device_type == "drone")
        return {
            "total": len(self.detections),
            "cameras": cameras,
            "alprs": alprs,
            "drones": drones,
            "unique_manufacturers": len(set(d.manufacturer for d in self.detections)),
        }

    def clear(self):
        """Clear all detections."""
        self.detections.clear()
        self.seen_macs.clear()


# Module-level singleton
_detector_instance: Optional[CameraDetector] = None


def get_detector() -> CameraDetector:
    """Get singleton CameraDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = CameraDetector()
    return _detector_instance


def detect_camera(mac: str, ssid: str = "", rssi: int = -100,
                  channel: int = 0, **kwargs) -> Optional[CameraDetection]:
    """Convenience function using singleton detector."""
    return get_detector().detect(mac, ssid, rssi, channel, **kwargs)
