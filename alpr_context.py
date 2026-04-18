#!/usr/bin/env python3
"""
WATCHDOG ALPR Context — Provides awareness of known ALPR camera locations.

Loads known camera locations from local JSON database and provides:
- Proximity alerts when operator is near known ALPR cameras
- Coverage area awareness (which neighborhood's surveillance zone you're in)
- Context for new detections (is this near a known camera cluster?)
- Location logging for newly discovered cameras

Data sources:
- config/alpr_locations_nola.json (local database, populated from field observations)
- DeFlock (deflock.org) data can be imported manually
- Atlas of Surveillance (atlasofsurveillance.org) data can be imported
"""
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from geopy.distance import geodesic
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    import math

PROJECT_ROOT = os.path.dirname(__file__)
DEFAULT_LOCATIONS_PATH = os.path.join(
    PROJECT_ROOT, "config", "alpr_locations_nola.json"
)


class ALPRContext:
    """
    Provides spatial awareness of known surveillance infrastructure.
    """

    def __init__(self, locations_path: str = DEFAULT_LOCATIONS_PATH,
                 proximity_radius_meters: float = 200.0):
        self.locations: List[Dict] = []
        self.coverage_areas: List[Dict] = []
        self.proximity_radius = proximity_radius_meters
        self._load_locations(locations_path)
        self.locations_path = locations_path

    def _load_locations(self, path: str) -> None:
        """Load known ALPR locations from JSON file."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.locations = data.get('locations', [])
            self.coverage_areas = data.get('coverage_areas', [])
            logger.info(
                f"WATCHDOG ALPR context: {len(self.locations)} known locations, "
                f"{len(self.coverage_areas)} coverage areas loaded"
            )
        except FileNotFoundError:
            logger.warning(f"ALPR locations file not found: {path}")
        except Exception as e:
            logger.error(f"Error loading ALPR locations: {e}")

    def _distance_meters(self, lat1: float, lon1: float,
                         lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        if GEOPY_AVAILABLE:
            return geodesic((lat1, lon1), (lat2, lon2)).meters
        # Haversine fallback
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def get_nearby_cameras(self, latitude: float, longitude: float,
                           radius_meters: float = None) -> List[Dict]:
        """Find known cameras within radius of current position."""
        radius = radius_meters or self.proximity_radius
        nearby = []
        for loc in self.locations:
            dist = self._distance_meters(
                latitude, longitude,
                loc['latitude'], loc['longitude']
            )
            if dist <= radius:
                nearby.append({
                    **loc,
                    'distance_meters': round(dist, 1),
                })
        return sorted(nearby, key=lambda x: x['distance_meters'])

    def get_current_coverage_area(self, latitude: float,
                                  longitude: float) -> Optional[str]:
        """Determine which surveillance coverage area the operator is in."""
        for area in self.coverage_areas:
            bounds = area.get('bounds', {})
            if (bounds.get('south', 0) <= latitude <= bounds.get('north', 0) and
                    bounds.get('west', 0) <= longitude <= bounds.get('east', 0)):
                return area.get('name', 'Unknown Area')
        return None

    def add_observed_camera(self, latitude: float, longitude: float,
                            device_type: str = "alpr",
                            vendor: str = "Unknown",
                            description: str = "",
                            notes: str = "") -> str:
        """
        Add a newly observed camera to the local database.

        Returns the assigned location ID.
        """
        from datetime import datetime

        loc_id = f"NOLA-OBS-{len(self.locations)+1:04d}"
        new_loc = {
            "id": loc_id,
            "type": device_type,
            "vendor": vendor,
            "latitude": latitude,
            "longitude": longitude,
            "description": description,
            "observed_date": datetime.now().strftime('%Y-%m-%d'),
            "confidence": "high",
            "notes": notes,
        }
        self.locations.append(new_loc)
        self._save_locations()

        logger.info(
            f"WATCHDOG: New camera logged — {loc_id} at "
            f"({latitude:.4f}, {longitude:.4f}) [{vendor}]"
        )
        return loc_id

    def _save_locations(self) -> None:
        """Save updated locations back to JSON file."""
        try:
            data = {
                "_meta": {
                    "description": "Known ALPR and surveillance camera locations — Orleans Parish, LA",
                    "sources": ["DeFlock", "Atlas of Surveillance", "Manual observation"],
                    "last_updated": __import__('datetime').datetime.now().strftime('%Y-%m-%d'),
                },
                "locations": self.locations,
                "coverage_areas": self.coverage_areas,
            }
            with open(self.locations_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ALPR locations: {e}")

    def get_context_summary(self, latitude: float,
                            longitude: float) -> Dict:
        """Get full context for current position."""
        nearby = self.get_nearby_cameras(latitude, longitude)
        area = self.get_current_coverage_area(latitude, longitude)
        return {
            "coverage_area": area,
            "nearby_cameras": len(nearby),
            "nearest_camera": nearby[0] if nearby else None,
            "cameras": nearby,
        }
