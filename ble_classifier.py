"""
BLE Device Classifier
Classifies BLE devices based on manufacturer IDs, UUIDs, and device names
"""
import logging
from typing import Dict, Any, Optional, List
from cyt_constants import DeviceType, SystemConstants

logger = logging.getLogger(__name__)


class BLEClassifier:
    """Classifies BLE devices into specific categories"""

    # Known tracker service UUIDs
    TRACKER_UUIDS = [
        'FE2C',  # Google Nearby / Fast Pair (used by many trackers)
        '181C',  # User Data Service (used by some trackers)
        'FD6F',  # Apple Find My network
    ]

    # Known wearable service UUIDs
    WEARABLE_UUIDS = [
        '180D',  # Heart Rate Service
        '180A',  # Device Information Service (common in wearables)
        '180F',  # Battery Service (common in wearables)
        '1816',  # Cycling Speed and Cadence
        '1814',  # Running Speed and Cadence
    ]

    def __init__(self):
        """Initialize BLE classifier"""
        pass

    def classify_device(self, ble_device: Dict[str, Any]) -> DeviceType:
        """
        Classify a BLE device based on manufacturer ID, UUIDs, and name

        Args:
            ble_device: Dictionary containing BLE device data with keys:
                - 'manufacturer': Manufacturer ID (int or None)
                - 'name': Device name (str)
                - 'uuid_list': List of service UUIDs (list of str)

        Returns:
            DeviceType enum value
        """
        manufacturer = ble_device.get('manufacturer')
        name = ble_device.get('name', '').lower()
        uuid_list = ble_device.get('uuid_list', [])

        # PRIORITY 1: Check for drones by manufacturer ID (highest threat priority)
        if manufacturer is not None:
            if manufacturer == SystemConstants.BLE_MANUFACTURER_DJI:
                logger.info(f"Detected DJI drone: {name}")
                return DeviceType.BLE_DRONE
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_PARROT:
                logger.info(f"Detected Parrot drone: {name}")
                return DeviceType.BLE_DRONE
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_AUTEL:
                logger.info(f"Detected Autel drone: {name}")
                return DeviceType.BLE_DRONE

        # PRIORITY 2: Check for trackers by manufacturer ID
        if manufacturer is not None:
            if manufacturer == SystemConstants.BLE_MANUFACTURER_APPLE:
                # Apple makes many BLE devices, check name for specifics
                if 'airtag' in name or 'tag' in name:
                    logger.info(f"Detected Apple AirTag: {name}")
                    return DeviceType.BLE_TRACKER
                # If no specific name match, check for Find My UUID
                if any(uuid.upper() == 'FD6F' for uuid in uuid_list):
                    logger.info(f"Detected Apple Find My device: {name}")
                    return DeviceType.BLE_TRACKER
                # Otherwise might be AirPods, iPhone, etc - check later
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_TILE:
                logger.info(f"Detected Tile tracker: {name}")
                return DeviceType.BLE_TRACKER
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_SAMSUNG:
                if 'tag' in name or 'smarttag' in name:
                    logger.info(f"Detected Samsung SmartTag: {name}")
                    return DeviceType.BLE_TRACKER

        # PRIORITY 3: Check for trackers by service UUIDs
        for uuid in uuid_list:
            if uuid.upper() in [u.upper() for u in self.TRACKER_UUIDS]:
                logger.info(f"Detected tracker by UUID {uuid}: {name}")
                return DeviceType.BLE_TRACKER

        # PRIORITY 4: Check for wearables by manufacturer ID
        if manufacturer is not None:
            if manufacturer == SystemConstants.BLE_MANUFACTURER_FITBIT:
                logger.info(f"Detected Fitbit wearable: {name}")
                return DeviceType.BLE_WEARABLE
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_GARMIN:
                logger.info(f"Detected Garmin wearable: {name}")
                return DeviceType.BLE_WEARABLE

        # PRIORITY 5: Check for wearables by service UUIDs
        for uuid in uuid_list:
            if uuid.upper() in [u.upper() for u in self.WEARABLE_UUIDS]:
                logger.info(f"Detected wearable by UUID {uuid}: {name}")
                return DeviceType.BLE_WEARABLE

        # PRIORITY 6: Fallback to device name keyword matching (least reliable)
        if name:
            # Check for drone keywords
            drone_keywords = ['drone', 'dji', 'mavic', 'phantom', 'parrot', 'autel']
            if any(keyword in name for keyword in drone_keywords):
                logger.info(f"Detected drone by name keyword: {name}")
                return DeviceType.BLE_DRONE

            # Check for tracker keywords
            tracker_keywords = ['tag', 'tracker', 'tile', 'airtag', 'smarttag']
            if any(keyword in name for keyword in tracker_keywords):
                logger.info(f"Detected tracker by name keyword: {name}")
                return DeviceType.BLE_TRACKER

            # Check for wearable keywords
            wearable_keywords = ['watch', 'fit', 'band', 'health', 'heart', 'garmin', 'fitbit']
            if any(keyword in name for keyword in wearable_keywords):
                logger.info(f"Detected wearable by name keyword: {name}")
                return DeviceType.BLE_WEARABLE

        # DEFAULT: Unknown BLE device
        logger.debug(f"Unknown BLE device: {name}, manufacturer: {manufacturer}")
        return DeviceType.BLE_UNKNOWN

    def is_likely_surveillance_device(self, device_type: DeviceType) -> bool:
        """
        Determine if a device type is likely used for surveillance/tracking

        Args:
            device_type: DeviceType enum value

        Returns:
            True if device is likely used for surveillance
        """
        surveillance_types = [
            DeviceType.BLE_TRACKER,
            DeviceType.BLE_DRONE,
            DeviceType.BLE_WEARABLE,  # Can follow user everywhere
        ]
        return device_type in surveillance_types

    def get_device_description(self, ble_device: Dict[str, Any],
                               device_type: DeviceType) -> str:
        """
        Generate a human-readable description of the BLE device

        Args:
            ble_device: BLE device data dictionary
            device_type: Classified device type

        Returns:
            Human-readable description string
        """
        name = ble_device.get('name', 'Unknown')
        manufacturer = ble_device.get('manufacturer')

        if device_type == DeviceType.BLE_DRONE:
            if manufacturer == SystemConstants.BLE_MANUFACTURER_DJI:
                return f"DJI Drone ({name})" if name else "DJI Drone"
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_PARROT:
                return f"Parrot Drone ({name})" if name else "Parrot Drone"
            else:
                return f"Drone ({name})" if name else "Drone"

        elif device_type == DeviceType.BLE_TRACKER:
            if manufacturer == SystemConstants.BLE_MANUFACTURER_APPLE:
                return "Apple AirTag" if "airtag" in name.lower() else "Apple Tracker"
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_TILE:
                return f"Tile Tracker ({name})" if name else "Tile Tracker"
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_SAMSUNG:
                return "Samsung SmartTag"
            else:
                return f"BLE Tracker ({name})" if name else "BLE Tracker"

        elif device_type == DeviceType.BLE_WEARABLE:
            if manufacturer == SystemConstants.BLE_MANUFACTURER_FITBIT:
                return f"Fitbit ({name})" if name else "Fitbit"
            elif manufacturer == SystemConstants.BLE_MANUFACTURER_GARMIN:
                return f"Garmin ({name})" if name else "Garmin"
            else:
                return f"Wearable ({name})" if name else "Wearable Device"

        else:
            return f"BLE Device ({name})" if name else f"BLE Device"
