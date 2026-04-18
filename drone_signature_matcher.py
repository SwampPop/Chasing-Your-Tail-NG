#!/usr/bin/env python3
"""
Drone and surveillance device signature matching.

Matches observed WiFi devices against known drone OUI prefixes,
SSID patterns, and Flock Safety ALPR camera signatures.

Uses config/drone_signatures.yaml as the signature database.
"""
import fnmatch
import logging
import os
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# Default path relative to project root
DEFAULT_SIGNATURES_PATH = os.path.join(
    os.path.dirname(__file__), "config", "drone_signatures.yaml"
)


class DroneSignatureMatcher:
    """Matches WiFi devices against known drone/surveillance signatures."""

    def __init__(self, signatures_path: str = DEFAULT_SIGNATURES_PATH):
        self.oui_prefixes: Dict[str, str] = {}
        self.ssid_patterns: Dict[str, List[str]] = {}
        self.dji_droneid_oui: str = ""
        self._load_signatures(signatures_path)

    def _load_signatures(self, path: str) -> None:
        """Load signatures from YAML file."""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            self.oui_prefixes = data.get("oui_prefixes", {})
            self.ssid_patterns = data.get("ssid_patterns", {})
            self.dji_droneid_oui = data.get("dji_droneid_oui", "")
            logger.info(
                f"Loaded {len(self.oui_prefixes)} drone OUI prefixes, "
                f"{sum(len(v) for v in self.ssid_patterns.values())} SSID patterns"
            )
        except FileNotFoundError:
            logger.warning(f"Drone signatures file not found: {path}")
        except Exception as e:
            logger.error(f"Error loading drone signatures: {e}")

    def match_oui(self, mac: str) -> Optional[str]:
        """
        Check if a MAC address matches a known drone manufacturer.

        Returns manufacturer name or None.
        """
        if not mac or len(mac) < 8:
            return None
        prefix = mac[:8].upper()
        return self.oui_prefixes.get(prefix)

    def match_ssid(self, ssid: str) -> Optional[Tuple[str, str]]:
        """
        Check if an SSID matches known drone/surveillance patterns.

        Returns (category, matched_pattern) or None.
        Categories: 'drone', 'flock_alpr', 'surveillance'
        """
        if not ssid:
            return None
        for category, patterns in self.ssid_patterns.items():
            for pattern in patterns:
                if fnmatch.fnmatch(ssid, pattern) or fnmatch.fnmatch(
                    ssid.lower(), pattern.lower()
                ):
                    return (category, pattern)
        return None

    def classify_device(
        self, mac: str, ssid: str = ""
    ) -> Dict[str, any]:
        """
        Classify a device based on MAC and SSID.

        Returns dict with:
          - is_drone: bool
          - is_flock: bool
          - is_surveillance: bool
          - manufacturer: str or None
          - matched_category: str or None
          - matched_pattern: str or None
          - confidence_boost: float (0.0-0.3 to add to behavioral score)
        """
        result = {
            "is_drone": False,
            "is_flock": False,
            "is_surveillance": False,
            "manufacturer": None,
            "matched_category": None,
            "matched_pattern": None,
            "confidence_boost": 0.0,
        }

        # Check OUI
        oui_match = self.match_oui(mac)
        if oui_match:
            result["is_drone"] = True
            result["manufacturer"] = oui_match
            result["confidence_boost"] = 0.3  # Strong signal

        # Check SSID
        ssid_match = self.match_ssid(ssid)
        if ssid_match:
            category, pattern = ssid_match
            result["matched_category"] = category
            result["matched_pattern"] = pattern

            if category == "drone":
                result["is_drone"] = True
                result["confidence_boost"] = max(
                    result["confidence_boost"], 0.25
                )
            elif category == "flock_alpr":
                result["is_flock"] = True
                result["confidence_boost"] = max(
                    result["confidence_boost"], 0.2
                )
            elif category == "surveillance":
                result["is_surveillance"] = True
                result["confidence_boost"] = max(
                    result["confidence_boost"], 0.1
                )

        return result


# Module-level singleton for easy import
_matcher_instance: Optional[DroneSignatureMatcher] = None


def get_matcher() -> DroneSignatureMatcher:
    """Get the singleton DroneSignatureMatcher instance."""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = DroneSignatureMatcher()
    return _matcher_instance


def classify_device(mac: str, ssid: str = "") -> Dict:
    """Convenience function using the singleton matcher."""
    return get_matcher().classify_device(mac, ssid)
