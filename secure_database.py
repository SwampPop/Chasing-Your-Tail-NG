"""
Secure database operations - prevents SQL injection
"""
import sqlite3
import json
import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class SecureKismetDB:
    """Secure wrapper for Kismet database operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self) -> None:
        """Establish secure database connection"""
        try:
            self._connection = sqlite3.connect(self.db_path, timeout=30.0)
            self._connection.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database {self.db_path}: {e}")
            raise
    
    def close(self) -> None:
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def execute_safe_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute parameterized query safely"""
        if not self._connection:
            raise RuntimeError("Database not connected")
        
        try:
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database query failed: {query}, params: {params}, error: {e}")
            raise
    
    def get_devices_by_time_range(self, start_time: float, end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get devices within time range with proper parameterization
        
        Args:
            start_time: Unix timestamp for start time
            end_time: Optional unix timestamp for end time
            
        Returns:
            List of device dictionaries
        """
        if end_time is not None:
            query = "SELECT devmac, type, device, last_time FROM devices WHERE last_time >= ? AND last_time <= ?"
            params = (start_time, end_time)
        else:
            query = "SELECT devmac, type, device, last_time FROM devices WHERE last_time >= ?"
            params = (start_time,)
        
        rows = self.execute_safe_query(query, params)
        
        devices = []
        for row in rows:
            try:
                # Parse device JSON safely
                device_data = None
                if row['device']:
                    try:
                        device_data = json.loads(row['device'])
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse device JSON for {row['devmac']}: {e}")
                
                devices.append({
                    'mac': row['devmac'],
                    'type': row['type'],
                    'device_data': device_data,
                    'last_time': row['last_time']
                })
            except Exception as e:
                logger.warning(f"Error processing device row: {e}")
                continue
        
        return devices
    
    def get_mac_addresses_by_time_range(self, start_time: float, end_time: Optional[float] = None) -> List[str]:
        """Get just MAC addresses for a time range"""
        devices = self.get_devices_by_time_range(start_time, end_time)
        return [device['mac'] for device in devices if device['mac']]
    
    def get_probe_requests_by_time_range(self, start_time: float, end_time: Optional[float] = None) -> List[Dict[str, str]]:
        """
        Get probe requests with SSIDs for time range
        
        Returns:
            List of dicts with 'mac', 'ssid', 'timestamp'
        """
        devices = self.get_devices_by_time_range(start_time, end_time)
        
        probes = []
        for device in devices:
            mac = device['mac']
            device_data = device['device_data']
            
            if not device_data:
                continue
            
            # Extract probe request SSID safely
            try:
                dot11_device = device_data.get('dot11.device', {})
                if not isinstance(dot11_device, dict):
                    continue
                    
                probe_record = dot11_device.get('dot11.device.last_probed_ssid_record', {})
                if not isinstance(probe_record, dict):
                    continue
                
                ssid = probe_record.get('dot11.probedssid.ssid', '')
                if ssid and isinstance(ssid, str):
                    probes.append({
                        'mac': mac,
                        'ssid': ssid,
                        'timestamp': device['last_time']
                    })
            except (KeyError, TypeError, AttributeError) as e:
                logger.debug(f"No probe data for device {mac}: {e}")
                continue
        
        return probes
    
    def validate_connection(self) -> bool:
        """Validate database connection and basic structure"""
        try:
            # Test basic query
            result = self.execute_safe_query("SELECT COUNT(*) as count FROM devices LIMIT 1")
            count = result[0]['count'] if result else 0
            logger.info(f"Database contains {count} devices")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database validation failed: {e}")
            return False


class SecureTimeWindows:
    """Secure time window management for device tracking"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.time_windows = config.get('timing', {}).get('time_windows', {
            'recent': 5,
            'medium': 10, 
            'old': 15,
            'oldest': 20
        })
    
    def get_time_boundaries(self) -> Dict[str, float]:
        """Calculate secure time boundaries"""
        now = datetime.now()
        
        boundaries = {}
        for window_name, minutes in self.time_windows.items():
            boundary_time = now - timedelta(minutes=minutes)
            boundaries[f'{window_name}_time'] = time.mktime(boundary_time.timetuple())
        
        # Add current time boundary (2 minutes ago for active scanning)
        current_boundary = now - timedelta(minutes=2)
        boundaries['current_time'] = time.mktime(current_boundary.timetuple())
        
        return boundaries
    
    def filter_devices_by_ignore_list(self, devices: List[str], ignore_list: List[str]) -> List[str]:
        """Safely filter devices against ignore list"""
        if not ignore_list:
            return devices
        
        # Convert ignore list to set for O(1) lookup
        ignore_set = set(mac.upper() for mac in ignore_list)
        
        filtered = []
        for device in devices:
            if isinstance(device, str) and device.upper() not in ignore_set:
                filtered.append(device)
        
        return filtered
    
    def filter_ssids_by_ignore_list(self, ssids: List[str], ignore_list: List[str]) -> List[str]:
        """Safely filter SSIDs against ignore list"""
        if not ignore_list:
            return ssids
        
        ignore_set = set(ignore_list)
        
        filtered = []
        for ssid in ssids:
            if isinstance(ssid, str) and ssid not in ignore_set:
                filtered.append(ssid)
        
        return filtered


def create_secure_db_connection(db_path: str) -> SecureKismetDB:
    """Factory function to create secure database connection"""
    return SecureKismetDB(db_path)