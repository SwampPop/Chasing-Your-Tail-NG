"""
CYT Constants and Enums
Centralized constants for device types, alert types, and other system-wide values
"""
from enum import Enum


class DeviceType(Enum):
    """Wireless device types detected by Kismet"""
    WI_FI_CLIENT = "Wi-Fi Client"
    WI_FI_AP = "Wi-Fi AP"
    UAV = "UAV"
    DRONE = "DRONE"
    BLUETOOTH = "Bluetooth"
    BLE_TRACKER = "BLE Tracker"  # AirTags, Tiles, SmartTags
    BLE_WEARABLE = "BLE Wearable"  # Fitness trackers, smartwatches
    BLE_DRONE = "BLE Drone"  # DJI, Parrot, Autel drones
    BLE_UNKNOWN = "BLE Unknown"  # Generic BLE devices
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, type_str: str):
        """Convert string to DeviceType enum, defaulting to UNKNOWN"""
        for device_type in cls:
            if device_type.value == type_str:
                return device_type
        return cls.UNKNOWN


class AlertType(Enum):
    """Alert types for GUI and notifications"""
    DRONE = "DRONE"
    WATCHLIST = "ALERT"
    CONFIRMED_THREAT = "CONFIRMED THREAT"
    STATUS_MONITORING = "STATUS: MONITORING"

    def __str__(self):
        return self.value


class PersistenceLevel(Enum):
    """Threat persistence levels for surveillance detection"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @property
    def emoji(self) -> str:
        """Get emoji representation of threat level"""
        emoji_map = {
            PersistenceLevel.CRITICAL: "🚨",
            PersistenceLevel.HIGH: "⚠️",
            PersistenceLevel.MEDIUM: "🟡",
            PersistenceLevel.LOW: "🔵"
        }
        return emoji_map.get(self, "⚪")

    @property
    def threshold(self) -> float:
        """Get score threshold for this level"""
        threshold_map = {
            PersistenceLevel.CRITICAL: 0.8,
            PersistenceLevel.HIGH: 0.6,
            PersistenceLevel.MEDIUM: 0.4,
            PersistenceLevel.LOW: 0.0
        }
        return threshold_map.get(self, 0.0)

    @classmethod
    def from_score(cls, score: float):
        """Determine persistence level from score"""
        if score >= 0.8:
            return cls.CRITICAL
        elif score >= 0.6:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        else:
            return cls.LOW


# System-wide magic number documentation
class SystemConstants:
    """Documented magic numbers used throughout the system"""

    # GPS/Location constants
    EARTH_RADIUS_METERS = 6371000  # Earth's radius in meters for Haversine formula

    # Security constants
    PBKDF2_ITERATIONS = 250000  # PBKDF2 iterations for key derivation (OWASP recommendation)
    ENCRYPTION_KEY_LENGTH = 32  # Fernet encryption key length in bytes

    # File permissions (octal)
    FILE_PERMISSION_PRIVATE = 0o600  # -rw------- (owner read/write only)
    DIR_PERMISSION_PRIVATE = 0o700   # drwx------ (owner full access only)

    # Validation limits
    MAX_CREDENTIAL_LENGTH = 10000  # Maximum length for stored credentials
    MAX_STRING_LENGTH = 50         # Maximum length for sanitized strings

    # Network timeouts
    WIGLE_API_TIMEOUT_SECONDS = 10     # Timeout for WiGLE API requests
    PANDOC_TIMEOUT_SECONDS = 30        # Timeout for pandoc HTML generation

    # Database limits
    DB_CONNECTION_TIMEOUT = 30.0       # SQLite connection timeout in seconds

    # BLE Manufacturer IDs (Company Identifiers)
    # See: https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/
    BLE_MANUFACTURER_APPLE = 0x004C      # Apple Inc. (AirTags, AirPods, etc.)
    BLE_MANUFACTURER_DJI = 0x0B41        # DJI drones
    BLE_MANUFACTURER_PARROT = 0x0043     # Parrot drones
    BLE_MANUFACTURER_AUTEL = 0x0A5C      # Autel Robotics drones (Broadcom = Autel uses this)
    BLE_MANUFACTURER_SAMSUNG = 0x0075    # Samsung (SmartTags)
    BLE_MANUFACTURER_TILE = 0x004E       # Tile trackers
    BLE_MANUFACTURER_FITBIT = 0x0057     # Fitbit wearables
    BLE_MANUFACTURER_GARMIN = 0x0087     # Garmin wearables

    @classmethod
    def get_description(cls, constant_name: str) -> str:
        """Get human-readable description of a constant"""
        descriptions = {
            'EARTH_RADIUS_METERS': 'Earth radius for GPS distance calculations',
            'PBKDF2_ITERATIONS': 'Key derivation iterations (OWASP recommended)',
            'ENCRYPTION_KEY_LENGTH': 'Fernet encryption key size',
            'FILE_PERMISSION_PRIVATE': 'Private file permissions (owner only)',
            'DIR_PERMISSION_PRIVATE': 'Private directory permissions (owner only)',
            'MAX_CREDENTIAL_LENGTH': 'Maximum credential storage size',
            'MAX_STRING_LENGTH': 'Maximum sanitized string length',
            'WIGLE_API_TIMEOUT_SECONDS': 'WiGLE API request timeout',
            'PANDOC_TIMEOUT_SECONDS': 'Pandoc conversion timeout',
            'DB_CONNECTION_TIMEOUT': 'Database connection timeout'
        }
        return descriptions.get(constant_name, 'No description available')
