"""
GPS Integration for CYT
Correlates device appearances with GPS locations for surveillance detection
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)

@dataclass
class GPSLocation:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    timestamp: float = None
    accuracy: Optional[float] = None
    location_name: Optional[str] = None

@dataclass 
class LocationSession:
    location: GPSLocation
    start_time: float
    end_time: float
    devices_seen: List[str]
    session_id: str

class GPSTracker:
    def __init__(self, config: Dict):
        self.config = config
        self.locations = []
        self.location_sessions = []
        self.current_location = None
        
        gps_settings = config.get('gps_settings', {})
        self.location_threshold = gps_settings.get('location_threshold_meters', 100)
        self.session_timeout = gps_settings.get('session_timeout_seconds', 600)
        
    def add_gps_reading(self, latitude: float, longitude: float, 
                       altitude: float = None, accuracy: float = None,
                       location_name: str = None) -> str:
        timestamp = time.time()
        location = GPSLocation(latitude=latitude, longitude=longitude, altitude=altitude,
                             timestamp=timestamp, accuracy=accuracy, location_name=location_name)
        self.locations.append(location)
        location_id = self._get_location_cluster_id(location)
        self._update_current_session(location, location_id)
        logger.info(f"GPS reading added: {latitude:.6f}, {longitude:.6f} -> {location_id}")
        return location_id
    
    def _get_location_cluster_id(self, location: GPSLocation) -> str:
        for session in self.location_sessions:
            if self._calculate_distance(location, session.location) <= self.location_threshold:
                return session.session_id
        
        base_name = location.location_name.replace(' ', '_') if location.location_name else f"loc_{location.latitude:.4f}_{location.longitude:.4f}"
        existing_ids = [s.session_id for s in self.location_sessions]
        counter = 1
        location_id = base_name
        while location_id in existing_ids:
            location_id = f"{base_name}_{counter}"
            counter += 1
        return location_id
    
    def _update_current_session(self, location: GPSLocation, location_id: str) -> None:
        now = time.time()
        current_session = None
        for session in self.location_sessions:
            if session.session_id == location_id and (now - session.end_time <= self.session_timeout):
                session.end_time = now
                current_session = session
                break
        
        if not current_session:
            current_session = LocationSession(location=location, start_time=now, end_time=now,
                                            devices_seen=[], session_id=location_id)
            self.location_sessions.append(current_session)
        
        self.current_location = current_session
        logger.debug(f"Updated session: {location_id}")
    
    def _calculate_distance(self, loc1: GPSLocation, loc2: GPSLocation) -> float:
        R = 6371000
        lat1_rad, lat2_rad = math.radians(loc1.latitude), math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lon = math.radians(loc2.longitude - loc1.longitude)
        a = (math.sin(delta_lat/2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def add_device_at_current_location(self, mac: str) -> Optional[str]:
        if not self.current_location:
            logger.warning("No current location - cannot record device")
            return None
        if mac not in self.current_location.devices_seen:
            self.current_location.devices_seen.append(mac)
            logger.debug(f"Device {mac} seen at {self.current_location.session_id}")
        return self.current_location.session_id
    
    def get_location_history(self) -> List[LocationSession]:
        return sorted(self.location_sessions, key=lambda s: s.start_time)
    
    def get_devices_across_locations(self) -> Dict[str, List[str]]:
        device_locations = defaultdict(list)
        for session in self.location_sessions:
            for mac in session.devices_seen:
                if session.session_id not in device_locations[mac]:
                    device_locations[mac].append(session.session_id)
        
        return {mac: locs for mac, locs in device_locations.items() if len(locs) > 1}

class KMLExporter:
    def __init__(self):
        try:
            # Assumes 'template.kml' is in the same directory
            with open('template.kml', 'r') as f:
                self.kml_template = f.read()
        except FileNotFoundError:
            logger.error("CRITICAL: template.kml not found. KML export will fail.")
            self.kml_template = "{content}"

    # All other KMLExporter methods from the original file go here...
    # (generate_kml, _format_device_list, etc.)
    # This abbreviated response assumes you have the rest of the KMLExporter class code.
    # If not, I can provide it again.

def simulate_gps_data() -> List[Tuple[float, float, str]]:
    """Generate simulated GPS data for testing"""
    return [
        (33.4484, -112.0740, "Phoenix_Home"),
        (33.4734, -112.0431, "Phoenix_Office"), 
        (33.5076, -112.0726, "Phoenix_Mall"),
        (33.4942, -112.1122, "Phoenix_Restaurant"),
        (33.4484, -112.0740, "Phoenix_Home_Return")
    ]