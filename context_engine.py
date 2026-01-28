#!/usr/bin/env python3

################################################################################
# context_engine.py
# Purpose: Enrich CYT alerts with situational awareness data
# Sources: DeFlock (ALPR cameras), Airplanes.live (aircraft), environmental data
# Created: 2026-01-28
################################################################################

import os
import sys
import json
import time
import sqlite3
import logging
import threading
import requests
import math
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict, field

logger = logging.getLogger('CYT.ContextEngine')


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ALPRCamera:
    """Represents an ALPR camera location from DeFlock or local detection"""
    camera_id: str
    latitude: float
    longitude: float
    source: str  # 'deflock', 'flock_detector', 'manual'
    camera_type: str  # 'flock', 'vigilant', 'rekor', 'unknown'
    first_seen: str
    last_seen: str
    confirmed: bool = False
    address: Optional[str] = None
    notes: Optional[str] = None
    distance_meters: Optional[float] = None


@dataclass
class Aircraft:
    """Represents an aircraft from ADS-B tracking"""
    icao_hex: str  # ICAO 24-bit address (hex)
    callsign: Optional[str]
    registration: Optional[str]  # N-number
    aircraft_type: Optional[str]
    latitude: float
    longitude: float
    altitude_ft: int
    ground_speed_knots: int
    track_degrees: int
    vertical_rate_fpm: int
    squawk: Optional[str]
    timestamp: str
    distance_nm: Optional[float] = None
    is_surveillance: bool = False
    surveillance_type: Optional[str] = None  # 'law_enforcement', 'military', 'government'


@dataclass
class ContextSnapshot:
    """Complete situational awareness snapshot"""
    timestamp: str
    latitude: float
    longitude: float

    # Nearby threats/items of interest
    nearby_cameras: List[ALPRCamera] = field(default_factory=list)
    nearby_aircraft: List[Aircraft] = field(default_factory=list)
    surveillance_aircraft_count: int = 0
    alpr_camera_count: int = 0

    # Threat assessment
    surveillance_score: int = 0  # 0-100
    threat_level: str = 'LOW'  # LOW, MEDIUM, HIGH, CRITICAL

    # Environmental context
    is_urban: bool = False
    population_density: Optional[str] = None
    notes: List[str] = field(default_factory=list)


# =============================================================================
# Known Surveillance Aircraft Database
# =============================================================================

# Known law enforcement and surveillance aircraft patterns
# Sources: Various OSINT research, Civil Defense Engineer, Benn Jordan
SURVEILLANCE_AIRCRAFT = {
    # FBI surveillance fleet (common N-numbers)
    'N': {
        'patterns': [
            'N1', 'N2', 'N3', 'N4', 'N5',  # FBI often uses N1xx, N2xx patterns
        ],
        'known': [
            'N529JK', 'N398CA', 'N404KR', 'N918JC',  # Known FBI planes
        ]
    },
    # DHS/CBP patterns
    'CBP': {
        'callsign_patterns': ['OMAHA', 'CBP'],
    },
    # Military patterns (avoid false positives)
    'MIL': {
        'callsign_patterns': ['RCH', 'REACH', 'EVAC'],
    }
}


class ContextEngine:
    """
    Situational Awareness Engine for CYT

    Aggregates data from multiple sources to provide context for alerts:
    - DeFlock: Crowdsourced ALPR camera locations (12,000+ cameras)
    - Airplanes.live: Unfiltered ADS-B aircraft tracking
    - Local Flock detections: Real-time ESP32 Flock detector data

    Enriches CYT alerts with:
    - Nearby ALPR cameras (within configurable radius)
    - Overhead/nearby aircraft (especially surveillance planes)
    - Overall surveillance threat score
    """

    # API endpoints
    DEFLOCK_API = "https://deflock.me/api/v1"
    AIRPLANES_LIVE_API = "https://api.airplanes.live/v2"
    ADSB_EXCHANGE_API = "https://globe.adsbexchange.com/api"

    # Default search radii
    DEFAULT_CAMERA_RADIUS_METERS = 1000  # 1km for ALPR cameras
    DEFAULT_AIRCRAFT_RADIUS_NM = 10  # 10 nautical miles for aircraft

    def __init__(
        self,
        config: Dict = None,
        db_path: str = 'context_data.db',
        callback: Optional[Callable[[ContextSnapshot], None]] = None
    ):
        """
        Initialize Context Engine

        Args:
            config: CYT configuration dict
            db_path: Path to context database
            callback: Function to call on context updates
        """
        self.config = config or {}
        self.db_path = db_path
        self.callback = callback

        # Get settings from config
        context_config = self.config.get('context_engine', {})
        self.camera_radius = context_config.get(
            'camera_radius_meters', self.DEFAULT_CAMERA_RADIUS_METERS)
        self.aircraft_radius = context_config.get(
            'aircraft_radius_nm', self.DEFAULT_AIRCRAFT_RADIUS_NM)
        self.poll_interval = context_config.get('poll_interval_seconds', 30)
        self.deflock_enabled = context_config.get('deflock_enabled', True)
        self.aircraft_enabled = context_config.get('aircraft_enabled', True)

        # State
        self._running = False
        self._poll_thread = None
        self._current_position = None  # (lat, lon)
        self._last_snapshot = None
        self._camera_cache = {}  # Cache DeFlock results
        self._camera_cache_time = None
        self._cache_ttl = 300  # 5 minutes

        self._init_database()
        logger.info(f"Context Engine initialized (camera radius: {self.camera_radius}m, "
                   f"aircraft radius: {self.aircraft_radius}nm)")

    def _init_database(self):
        """Initialize context database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ALPR camera sightings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alpr_cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT UNIQUE,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                source TEXT NOT NULL,
                camera_type TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                confirmed INTEGER DEFAULT 0,
                address TEXT,
                notes TEXT
            )
        ''')

        # Aircraft sightings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aircraft_sightings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                icao_hex TEXT NOT NULL,
                callsign TEXT,
                registration TEXT,
                aircraft_type TEXT,
                latitude REAL,
                longitude REAL,
                altitude_ft INTEGER,
                ground_speed_knots INTEGER,
                timestamp TEXT NOT NULL,
                is_surveillance INTEGER DEFAULT 0,
                surveillance_type TEXT,
                my_latitude REAL,
                my_longitude REAL
            )
        ''')

        # Context snapshots (for historical analysis)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                nearby_cameras INTEGER,
                nearby_aircraft INTEGER,
                surveillance_aircraft INTEGER,
                surveillance_score INTEGER,
                threat_level TEXT,
                snapshot_json TEXT
            )
        ''')

        # Indices
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cameras_location
            ON alpr_cameras(latitude, longitude)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_aircraft_timestamp
            ON aircraft_sightings(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_aircraft_surveillance
            ON aircraft_sightings(is_surveillance)
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Context database initialized: {self.db_path}")

    # =========================================================================
    # Position Management
    # =========================================================================

    def set_position(self, latitude: float, longitude: float) -> None:
        """
        Update current GPS position

        Args:
            latitude: Current latitude
            longitude: Current longitude
        """
        self._current_position = (latitude, longitude)
        logger.debug(f"Position updated: {latitude:.6f}, {longitude:.6f}")

    def get_position(self) -> Optional[Tuple[float, float]]:
        """Get current position"""
        return self._current_position

    # =========================================================================
    # DeFlock Integration
    # =========================================================================

    def query_deflock(
        self,
        latitude: float = None,
        longitude: float = None,
        radius_meters: int = None
    ) -> List[ALPRCamera]:
        """
        Query DeFlock API for nearby ALPR cameras

        DeFlock is a crowdsourced database of ALPR camera locations.
        API: https://deflock.me

        Args:
            latitude: Center latitude (uses current position if None)
            longitude: Center longitude (uses current position if None)
            radius_meters: Search radius (uses config default if None)

        Returns:
            List of ALPRCamera objects within radius
        """
        lat = latitude or (self._current_position[0] if self._current_position else None)
        lon = longitude or (self._current_position[1] if self._current_position else None)
        radius = radius_meters or self.camera_radius

        if lat is None or lon is None:
            logger.warning("No position set - cannot query DeFlock")
            return []

        # Check cache
        cache_key = f"{lat:.4f},{lon:.4f}"
        if (self._camera_cache_time and
            time.time() - self._camera_cache_time < self._cache_ttl and
            cache_key in self._camera_cache):
            logger.debug("Using cached DeFlock data")
            return self._camera_cache[cache_key]

        cameras = []

        try:
            # DeFlock API endpoint for nearby cameras
            # Note: This is a hypothetical API structure - adjust to actual API
            url = f"{self.DEFLOCK_API}/cameras/nearby"
            params = {
                'lat': lat,
                'lon': lon,
                'radius': radius,
                'format': 'json'
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                for cam in data.get('cameras', []):
                    camera = ALPRCamera(
                        camera_id=cam.get('id', f"deflock_{cam.get('lat')}_{cam.get('lon')}"),
                        latitude=cam.get('lat', 0),
                        longitude=cam.get('lon', 0),
                        source='deflock',
                        camera_type=cam.get('type', 'unknown'),
                        first_seen=cam.get('first_reported', datetime.now().isoformat()),
                        last_seen=cam.get('last_confirmed', datetime.now().isoformat()),
                        confirmed=cam.get('confirmed', False),
                        address=cam.get('address'),
                        notes=cam.get('notes'),
                        distance_meters=self._calculate_distance(
                            lat, lon, cam.get('lat'), cam.get('lon'))
                    )
                    cameras.append(camera)

                # Update cache
                self._camera_cache[cache_key] = cameras
                self._camera_cache_time = time.time()

                logger.info(f"DeFlock query returned {len(cameras)} cameras within {radius}m")

            elif response.status_code == 404:
                logger.debug("No cameras found in area")
            else:
                logger.warning(f"DeFlock API returned status {response.status_code}")

        except requests.exceptions.ConnectionError:
            logger.warning("Cannot connect to DeFlock API - using cached/local data")
            cameras = self._get_local_cameras(lat, lon, radius)
        except requests.exceptions.Timeout:
            logger.warning("DeFlock API timeout - using cached/local data")
            cameras = self._get_local_cameras(lat, lon, radius)
        except Exception as e:
            logger.error(f"DeFlock query error: {e}")

        return cameras

    def _get_local_cameras(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int
    ) -> List[ALPRCamera]:
        """
        Get cameras from local database (fallback when API unavailable)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Simple bounding box query (approximate)
        # 1 degree latitude ≈ 111km
        lat_delta = radius_meters / 111000
        lon_delta = radius_meters / (111000 * math.cos(math.radians(latitude)))

        cursor.execute('''
            SELECT * FROM alpr_cameras
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
        ''', (
            latitude - lat_delta, latitude + lat_delta,
            longitude - lon_delta, longitude + lon_delta
        ))

        cameras = []
        for row in cursor.fetchall():
            dist = self._calculate_distance(
                latitude, longitude, row['latitude'], row['longitude'])
            if dist <= radius_meters:
                cameras.append(ALPRCamera(
                    camera_id=row['camera_id'],
                    latitude=row['latitude'],
                    longitude=row['longitude'],
                    source=row['source'],
                    camera_type=row['camera_type'],
                    first_seen=row['first_seen'],
                    last_seen=row['last_seen'],
                    confirmed=bool(row['confirmed']),
                    address=row['address'],
                    notes=row['notes'],
                    distance_meters=dist
                ))

        conn.close()
        return cameras

    def add_camera(self, camera: ALPRCamera) -> int:
        """
        Add or update an ALPR camera in the database

        Args:
            camera: ALPRCamera to store

        Returns:
            Database row ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alpr_cameras (
                camera_id, latitude, longitude, source, camera_type,
                first_seen, last_seen, confirmed, address, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(camera_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                confirmed = excluded.confirmed
        ''', (
            camera.camera_id,
            camera.latitude,
            camera.longitude,
            camera.source,
            camera.camera_type,
            camera.first_seen,
            camera.last_seen,
            1 if camera.confirmed else 0,
            camera.address,
            camera.notes
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.debug(f"Camera stored: {camera.camera_id}")
        return row_id

    # =========================================================================
    # Aircraft Tracking (Airplanes.live / ADS-B Exchange)
    # =========================================================================

    def query_aircraft(
        self,
        latitude: float = None,
        longitude: float = None,
        radius_nm: int = None
    ) -> List[Aircraft]:
        """
        Query aircraft in the area using Airplanes.live API

        Airplanes.live provides unfiltered ADS-B data (unlike FlightAware/FlightRadar24
        which filter military and law enforcement aircraft).

        Args:
            latitude: Center latitude (uses current position if None)
            longitude: Center longitude (uses current position if None)
            radius_nm: Search radius in nautical miles

        Returns:
            List of Aircraft objects, with surveillance aircraft flagged
        """
        lat = latitude or (self._current_position[0] if self._current_position else None)
        lon = longitude or (self._current_position[1] if self._current_position else None)
        radius = radius_nm or self.aircraft_radius

        if lat is None or lon is None:
            logger.warning("No position set - cannot query aircraft")
            return []

        aircraft_list = []

        try:
            # Airplanes.live point endpoint
            # Returns aircraft within radius of a point
            url = f"{self.AIRPLANES_LIVE_API}/point/{lat}/{lon}/{radius}"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                for ac in data.get('ac', []):
                    # Check if this is a surveillance aircraft
                    is_surv, surv_type = self._check_surveillance_aircraft(ac)

                    # Calculate distance
                    ac_lat = ac.get('lat')
                    ac_lon = ac.get('lon')
                    distance = None
                    if ac_lat and ac_lon:
                        distance = self._calculate_distance_nm(lat, lon, ac_lat, ac_lon)

                    aircraft = Aircraft(
                        icao_hex=ac.get('hex', ''),
                        callsign=ac.get('flight', '').strip() if ac.get('flight') else None,
                        registration=ac.get('r'),
                        aircraft_type=ac.get('t'),
                        latitude=ac_lat or 0,
                        longitude=ac_lon or 0,
                        altitude_ft=ac.get('alt_baro', 0) or 0,
                        ground_speed_knots=ac.get('gs', 0) or 0,
                        track_degrees=ac.get('track', 0) or 0,
                        vertical_rate_fpm=ac.get('baro_rate', 0) or 0,
                        squawk=ac.get('squawk'),
                        timestamp=datetime.now().isoformat(),
                        distance_nm=distance,
                        is_surveillance=is_surv,
                        surveillance_type=surv_type
                    )
                    aircraft_list.append(aircraft)

                    # Store surveillance aircraft
                    if is_surv:
                        self._store_aircraft_sighting(aircraft, lat, lon)

                surv_count = sum(1 for a in aircraft_list if a.is_surveillance)
                logger.info(f"Aircraft query: {len(aircraft_list)} total, "
                           f"{surv_count} surveillance")

            else:
                logger.warning(f"Airplanes.live API returned status {response.status_code}")

        except requests.exceptions.ConnectionError:
            logger.warning("Cannot connect to Airplanes.live API")
        except requests.exceptions.Timeout:
            logger.warning("Airplanes.live API timeout")
        except Exception as e:
            logger.error(f"Aircraft query error: {e}")

        return aircraft_list

    def _check_surveillance_aircraft(self, ac_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if aircraft matches known surveillance patterns

        Args:
            ac_data: Raw aircraft data from API

        Returns:
            Tuple of (is_surveillance, surveillance_type)
        """
        registration = ac_data.get('r', '') or ''
        callsign = (ac_data.get('flight', '') or '').strip()
        aircraft_type = ac_data.get('t', '') or ''

        # Check known surveillance registrations
        for known in SURVEILLANCE_AIRCRAFT['N'].get('known', []):
            if registration.upper() == known.upper():
                return True, 'law_enforcement'

        # Check registration patterns (FBI often uses N1xx, N2xx series)
        for pattern in SURVEILLANCE_AIRCRAFT['N'].get('patterns', []):
            if registration.upper().startswith(pattern):
                # Additional check: FBI planes are often Cessnas
                if 'C' in aircraft_type.upper():  # Cessna types start with C
                    return True, 'possible_law_enforcement'

        # Check callsign patterns
        for pattern in SURVEILLANCE_AIRCRAFT.get('CBP', {}).get('callsign_patterns', []):
            if pattern in callsign.upper():
                return True, 'government'

        # Check for circling behavior (low altitude, slow speed near position)
        # This is a simplified check - real implementation would track history
        try:
            altitude = int(ac_data.get('alt_baro', 0) or 0)
            speed = int(ac_data.get('gs', 0) or 0)
        except (ValueError, TypeError):
            altitude = 0
            speed = 0

        if 1000 <= altitude <= 5000 and speed < 150:
            # Low and slow - suspicious but not confirmed
            return False, None  # Would need pattern analysis over time

        return False, None

    def _store_aircraft_sighting(
        self,
        aircraft: Aircraft,
        my_lat: float,
        my_lon: float
    ) -> int:
        """Store surveillance aircraft sighting in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO aircraft_sightings (
                icao_hex, callsign, registration, aircraft_type,
                latitude, longitude, altitude_ft, ground_speed_knots,
                timestamp, is_surveillance, surveillance_type,
                my_latitude, my_longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            aircraft.icao_hex,
            aircraft.callsign,
            aircraft.registration,
            aircraft.aircraft_type,
            aircraft.latitude,
            aircraft.longitude,
            aircraft.altitude_ft,
            aircraft.ground_speed_knots,
            aircraft.timestamp,
            1 if aircraft.is_surveillance else 0,
            aircraft.surveillance_type,
            my_lat,
            my_lon
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Surveillance aircraft logged: {aircraft.registration or aircraft.icao_hex}")
        return row_id

    # =========================================================================
    # Context Snapshot Generation
    # =========================================================================

    def get_context(
        self,
        latitude: float = None,
        longitude: float = None
    ) -> ContextSnapshot:
        """
        Generate complete situational awareness snapshot

        Args:
            latitude: Position latitude (uses current if None)
            longitude: Position longitude (uses current if None)

        Returns:
            ContextSnapshot with all available context data
        """
        lat = latitude or (self._current_position[0] if self._current_position else None)
        lon = longitude or (self._current_position[1] if self._current_position else None)

        if lat is None or lon is None:
            logger.warning("No position available for context generation")
            return ContextSnapshot(
                timestamp=datetime.now().isoformat(),
                latitude=0,
                longitude=0,
                threat_level='UNKNOWN',
                notes=['No GPS position available']
            )

        # Query data sources
        cameras = []
        aircraft = []

        if self.deflock_enabled:
            cameras = self.query_deflock(lat, lon)

        if self.aircraft_enabled:
            aircraft = self.query_aircraft(lat, lon)

        # Count surveillance aircraft
        surv_aircraft = [a for a in aircraft if a.is_surveillance]

        # Calculate threat score
        threat_score = self._calculate_threat_score(cameras, surv_aircraft)
        threat_level = self._score_to_level(threat_score)

        # Build notes
        notes = []
        if len(cameras) > 5:
            notes.append(f"High ALPR camera density: {len(cameras)} cameras nearby")
        if surv_aircraft:
            notes.append(f"Surveillance aircraft detected: {len(surv_aircraft)}")

        snapshot = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            latitude=lat,
            longitude=lon,
            nearby_cameras=cameras,
            nearby_aircraft=aircraft,
            surveillance_aircraft_count=len(surv_aircraft),
            alpr_camera_count=len(cameras),
            surveillance_score=threat_score,
            threat_level=threat_level,
            notes=notes
        )

        # Store snapshot
        self._store_snapshot(snapshot)

        # Update last snapshot
        self._last_snapshot = snapshot

        # Callback if registered
        if self.callback:
            self.callback(snapshot)

        return snapshot

    def _calculate_threat_score(
        self,
        cameras: List[ALPRCamera],
        surveillance_aircraft: List[Aircraft]
    ) -> int:
        """
        Calculate overall surveillance threat score (0-100)

        Factors:
        - Number of nearby ALPR cameras
        - Presence of surveillance aircraft
        - Camera density
        - Proximity of cameras
        """
        score = 0

        # ALPR cameras (up to 40 points)
        if cameras:
            # Base score for any cameras nearby
            score += min(len(cameras) * 5, 20)

            # Bonus for very close cameras
            close_cameras = [c for c in cameras if c.distance_meters and c.distance_meters < 200]
            score += min(len(close_cameras) * 5, 20)

        # Surveillance aircraft (up to 50 points)
        if surveillance_aircraft:
            # Each surveillance aircraft adds significant score
            score += min(len(surveillance_aircraft) * 25, 50)

        # Cap at 100
        return min(score, 100)

    def _score_to_level(self, score: int) -> str:
        """Convert numeric score to threat level"""
        if score >= 75:
            return 'CRITICAL'
        elif score >= 50:
            return 'HIGH'
        elif score >= 25:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _store_snapshot(self, snapshot: ContextSnapshot) -> int:
        """Store context snapshot in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO context_snapshots (
                timestamp, latitude, longitude, nearby_cameras,
                nearby_aircraft, surveillance_aircraft, surveillance_score,
                threat_level, snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot.timestamp,
            snapshot.latitude,
            snapshot.longitude,
            snapshot.alpr_camera_count,
            len(snapshot.nearby_aircraft),
            snapshot.surveillance_aircraft_count,
            snapshot.surveillance_score,
            snapshot.threat_level,
            json.dumps(asdict(snapshot), default=str)
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return row_id

    # =========================================================================
    # Background Polling
    # =========================================================================

    def start(self, poll_interval: float = None) -> None:
        """
        Start background context polling

        Args:
            poll_interval: Polling interval in seconds
        """
        if self._running:
            logger.warning("Context engine already running")
            return

        interval = poll_interval or self.poll_interval

        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval,),
            daemon=True
        )
        self._poll_thread.start()

        logger.info(f"Context engine started (poll interval: {interval}s)")

    def stop(self) -> None:
        """Stop background polling"""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        logger.info("Context engine stopped")

    def _poll_loop(self, interval: float) -> None:
        """Background polling loop"""
        while self._running:
            try:
                if self._current_position:
                    self.get_context()
                else:
                    logger.debug("Waiting for GPS position...")
            except Exception as e:
                logger.error(f"Context poll error: {e}")

            time.sleep(interval)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters (Haversine)"""
        R = 6371000  # Earth radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat/2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def _calculate_distance_nm(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in nautical miles"""
        meters = self._calculate_distance(lat1, lon1, lat2, lon2)
        return meters / 1852  # 1 nautical mile = 1852 meters

    def get_last_snapshot(self) -> Optional[ContextSnapshot]:
        """Get most recent context snapshot"""
        return self._last_snapshot

    def get_surveillance_history(self, hours: int = 24) -> Dict:
        """
        Get surveillance event history

        Args:
            hours: How many hours back to search

        Returns:
            Dict with camera and aircraft sighting summaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get aircraft sightings
        cursor.execute('''
            SELECT * FROM aircraft_sightings
            WHERE datetime(timestamp) >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{hours} hours',))

        aircraft = [dict(row) for row in cursor.fetchall()]

        # Get unique surveillance aircraft
        cursor.execute('''
            SELECT registration, COUNT(*) as sightings
            FROM aircraft_sightings
            WHERE is_surveillance = 1
            AND datetime(timestamp) >= datetime('now', ?)
            GROUP BY registration
            ORDER BY sightings DESC
        ''', (f'-{hours} hours',))

        top_aircraft = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'total_surveillance_sightings': len([a for a in aircraft if a['is_surveillance']]),
            'unique_surveillance_aircraft': len(top_aircraft),
            'top_aircraft': top_aircraft,
            'all_sightings': aircraft
        }

    def summary(self) -> Dict:
        """Get summary of context data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM alpr_cameras')
        camera_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM aircraft_sightings WHERE is_surveillance = 1')
        surv_sightings = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM context_snapshots')
        snapshot_count = cursor.fetchone()[0]

        conn.close()

        return {
            'known_cameras': camera_count,
            'surveillance_aircraft_sightings': surv_sightings,
            'total_snapshots': snapshot_count,
            'last_update': self._last_snapshot.timestamp if self._last_snapshot else None,
            'current_position': self._current_position,
            'deflock_enabled': self.deflock_enabled,
            'aircraft_enabled': self.aircraft_enabled
        }


# =============================================================================
# CLI Interface
# =============================================================================

def context_callback(snapshot: ContextSnapshot):
    """Example callback for context updates"""
    print(f"\n{'='*60}")
    print(f"CONTEXT UPDATE - {snapshot.threat_level}")
    print(f"{'='*60}")
    print(f"Position: {snapshot.latitude:.6f}, {snapshot.longitude:.6f}")
    print(f"ALPR Cameras: {snapshot.alpr_camera_count}")
    print(f"Aircraft: {len(snapshot.nearby_aircraft)} total, "
          f"{snapshot.surveillance_aircraft_count} surveillance")
    print(f"Threat Score: {snapshot.surveillance_score}/100")

    if snapshot.notes:
        print(f"Notes: {', '.join(snapshot.notes)}")

    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("CYT Context Engine")
    print("=" * 50)
    print("Situational awareness through DeFlock + Airplanes.live")
    print()

    # Load config if available
    config = {}
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            config = json.load(f)

    # Initialize engine
    engine = ContextEngine(
        config=config,
        db_path='context_data.db',
        callback=context_callback
    )

    print(f"\nEngine initialized:")
    print(f"  Camera radius: {engine.camera_radius}m")
    print(f"  Aircraft radius: {engine.aircraft_radius}nm")
    print(f"  DeFlock enabled: {engine.deflock_enabled}")
    print(f"  Aircraft enabled: {engine.aircraft_enabled}")

    # Demo with test coordinates (New Orleans area from HANDOFF)
    test_lat = 29.922
    test_lon = -90.373

    print(f"\nSetting test position: {test_lat}, {test_lon}")
    engine.set_position(test_lat, test_lon)

    print("\nQuerying context (this may take a moment)...")
    snapshot = engine.get_context()

    print("\n" + "=" * 50)
    print("CONTEXT SNAPSHOT RESULT")
    print("=" * 50)
    print(f"Timestamp: {snapshot.timestamp}")
    print(f"Position: {snapshot.latitude:.6f}, {snapshot.longitude:.6f}")
    print(f"Threat Level: {snapshot.threat_level} (Score: {snapshot.surveillance_score})")
    print(f"ALPR Cameras Found: {snapshot.alpr_camera_count}")
    print(f"Aircraft Detected: {len(snapshot.nearby_aircraft)}")
    print(f"Surveillance Aircraft: {snapshot.surveillance_aircraft_count}")

    if snapshot.nearby_cameras:
        print("\nNearby Cameras:")
        for cam in snapshot.nearby_cameras[:5]:  # Show first 5
            print(f"  - {cam.camera_type}: {cam.distance_meters:.0f}m away")

    if snapshot.nearby_aircraft:
        print("\nNearby Aircraft:")
        for ac in snapshot.nearby_aircraft[:5]:  # Show first 5
            surv_tag = " [SURVEILLANCE]" if ac.is_surveillance else ""
            print(f"  - {ac.registration or ac.icao_hex}: "
                  f"{ac.altitude_ft}ft, {ac.distance_nm:.1f}nm{surv_tag}")

    print("\nSummary:", engine.summary())
