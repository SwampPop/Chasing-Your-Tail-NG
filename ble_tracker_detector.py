#!/usr/bin/env python3
"""
WATCHDOG BLE Tracker Detector — Detect AirTags, Tile, SmartTags, and other
Bluetooth Low Energy tracking devices.

Detection methods:
1. Apple Find My network advertisements (AirTags, AirPods, etc.)
2. Tile tracker advertisements
3. Samsung SmartTag advertisements
4. Generic BLE trackers with persistent advertising

Uses Kismet's BLE datasource or standalone bleak library.

References:
- OpenHaystack (SEEMOO lab) for Find My BLE advertisement format
- AirGuard (SEEMOO lab) for persistent tracker detection algorithms
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Apple Find My advertisement constants
# AirTags and Find My accessories use Apple's Continuity protocol
# Company ID 0x004C (Apple) in BLE advertisement manufacturer data
APPLE_COMPANY_ID = 0x004C
FIND_MY_TYPE = 0x12  # Find My Network type in Apple continuity

# Known tracker BLE signatures
TRACKER_SIGNATURES = {
    # Apple Find My network (AirTag, AirPods, FindMy accessories)
    "apple_findmy": {
        "company_id": 0x004C,
        "subtypes": [0x12],  # Find My network
        "name_patterns": [],  # AirTags don't advertise a name
        "description": "Apple Find My (AirTag/AirPods/FindMy accessory)",
    },
    # Tile trackers
    "tile": {
        "company_id": 0xFEED,  # Tile uses custom service UUID
        "service_uuids": ["0000feed-0000-1000-8000-00805f9b34fb"],
        "name_patterns": ["Tile"],
        "description": "Tile Tracker",
    },
    # Samsung SmartTag
    "samsung_smarttag": {
        "company_id": 0x0075,  # Samsung
        "name_patterns": ["SmartTag", "Galaxy SmartTag"],
        "description": "Samsung Galaxy SmartTag",
    },
    # Chipolo
    "chipolo": {
        "name_patterns": ["Chipolo"],
        "description": "Chipolo Tracker",
    },
}


@dataclass
class BLETrackerDetection:
    """A detected BLE tracking device."""
    mac: str
    tracker_type: str  # 'apple_findmy', 'tile', 'samsung_smarttag', etc.
    description: str
    rssi: int = -100
    first_seen: float = 0.0
    last_seen: float = 0.0
    seen_count: int = 1
    is_following: bool = False  # True if device persists across locations
    locations: List[tuple] = field(default_factory=list)


class BLETrackerDetector:
    """
    Detect BLE tracking devices from Kismet data or direct BLE scans.

    Uses persistence-based detection: a tracker that follows you across
    multiple locations over time is flagged as suspicious.
    """

    def __init__(self, follow_threshold_minutes: int = 30,
                 follow_threshold_locations: int = 2):
        self.trackers: Dict[str, BLETrackerDetection] = {}
        self.follow_threshold_minutes = follow_threshold_minutes
        self.follow_threshold_locations = follow_threshold_locations
        logger.info("WATCHDOG BLE tracker detector initialized")

    def process_ble_advertisement(self, mac: str, name: str = "",
                                   company_id: int = 0,
                                   service_uuids: List[str] = None,
                                   rssi: int = -100,
                                   manufacturer_data: bytes = None,
                                   latitude: float = 0.0,
                                   longitude: float = 0.0) -> Optional[BLETrackerDetection]:
        """
        Process a BLE advertisement and check if it's a tracker.

        Returns BLETrackerDetection if detected, None otherwise.
        """
        tracker_type = self._classify_tracker(
            mac, name, company_id, service_uuids, manufacturer_data
        )

        if not tracker_type:
            return None

        now = time.time()
        sig = TRACKER_SIGNATURES.get(tracker_type, {})

        if mac in self.trackers:
            # Update existing tracker
            tracker = self.trackers[mac]
            tracker.last_seen = now
            tracker.seen_count += 1
            tracker.rssi = rssi

            # Add location if GPS available
            if latitude and longitude:
                loc = (latitude, longitude)
                if not tracker.locations or tracker.locations[-1] != loc:
                    tracker.locations.append(loc)

            # Check for following behavior
            duration_minutes = (now - tracker.first_seen) / 60
            unique_locations = len(set(tracker.locations))

            if (duration_minutes >= self.follow_threshold_minutes and
                    unique_locations >= self.follow_threshold_locations):
                if not tracker.is_following:
                    tracker.is_following = True
                    logger.warning(
                        f"WATCHDOG BLE: FOLLOWING detected — "
                        f"{tracker.description} MAC:{mac} "
                        f"seen for {duration_minutes:.0f}min "
                        f"across {unique_locations} locations"
                    )

            return tracker
        else:
            # New tracker detection
            tracker = BLETrackerDetection(
                mac=mac,
                tracker_type=tracker_type,
                description=sig.get('description', tracker_type),
                rssi=rssi,
                first_seen=now,
                last_seen=now,
                locations=[(latitude, longitude)] if latitude and longitude else [],
            )
            self.trackers[mac] = tracker

            logger.info(
                f"WATCHDOG BLE: {tracker.description} detected — "
                f"MAC:{mac} RSSI:{rssi}"
            )
            return tracker

    def _classify_tracker(self, mac: str, name: str,
                          company_id: int,
                          service_uuids: List[str] = None,
                          manufacturer_data: bytes = None) -> Optional[str]:
        """Classify a BLE device as a specific tracker type."""
        service_uuids = service_uuids or []

        # Apple Find My detection
        if company_id == APPLE_COMPANY_ID and manufacturer_data:
            if len(manufacturer_data) >= 2:
                subtype = manufacturer_data[0]
                if subtype == FIND_MY_TYPE:
                    return "apple_findmy"

        # Check by name patterns
        name_lower = name.lower() if name else ""
        for tracker_type, sig in TRACKER_SIGNATURES.items():
            for pattern in sig.get("name_patterns", []):
                if pattern.lower() in name_lower:
                    return tracker_type

        # Check by service UUID
        for tracker_type, sig in TRACKER_SIGNATURES.items():
            for uuid in sig.get("service_uuids", []):
                if uuid in service_uuids:
                    return tracker_type

        # Check by company ID
        for tracker_type, sig in TRACKER_SIGNATURES.items():
            if sig.get("company_id") == company_id and company_id != 0:
                return tracker_type

        return None

    def get_active_trackers(self, max_age_seconds: int = 600) -> List[BLETrackerDetection]:
        """Get trackers seen within the last N seconds."""
        now = time.time()
        return [
            t for t in self.trackers.values()
            if (now - t.last_seen) <= max_age_seconds
        ]

    def get_following_trackers(self) -> List[BLETrackerDetection]:
        """Get trackers flagged as following the operator."""
        return [t for t in self.trackers.values() if t.is_following]

    def get_summary(self) -> Dict:
        """Get detection summary."""
        active = self.get_active_trackers()
        following = self.get_following_trackers()
        return {
            "total_seen": len(self.trackers),
            "active": len(active),
            "following": len(following),
            "types": {
                t.tracker_type: sum(1 for x in self.trackers.values()
                                    if x.tracker_type == t.tracker_type)
                for t in self.trackers.values()
            },
        }

    def clear(self):
        """Clear all tracker data."""
        self.trackers.clear()
