#!/usr/bin/env python3

################################################################################
# flock_detector.py
# Purpose: Detect Flock Safety ALPR cameras and Raven gunshot detectors
# Integration: Connects to Flock You ESP32 detector via API or serial
# Created: 2026-01-17
################################################################################

import os
import sys
import json
import time
import sqlite3
import logging
import threading
import requests
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, asdict

logger = logging.getLogger('CYT.FlockDetector')


@dataclass
class FlockDetection:
    """Represents a single Flock/Raven detection event"""
    detection_id: int
    timestamp: str
    device_type: str  # FLOCK_CAMERA, RAVEN_GUNSHOT, PENGUIN, PIGVISION
    protocol: str  # wifi, bluetooth_le
    detection_method: str  # probe_request, beacon, ble_scan, raven_service_uuid
    mac_address: str
    rssi: int
    signal_strength: str  # STRONG, MEDIUM, WEAK
    threat_score: int  # 0-100
    threat_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    manufacturer: Optional[str] = None
    ssid: Optional[str] = None
    device_name: Optional[str] = None
    channel: Optional[int] = None
    notes: Optional[str] = None


class FlockDetector:
    """
    Detect Flock Safety ALPR cameras and Raven gunshot detectors

    Connects to Flock You ESP32 detector via:
    - HTTP API (Flask server at localhost:5000)
    - WebSocket for real-time events
    - Serial port for direct ESP32 connection

    Stores detections in CYT watchlist database for correlation
    with other surveillance indicators (WiFi, BLE, drones, IMSI catchers).
    """

    # Device type classifications
    DEVICE_TYPES = {
        'FLOCK_CAMERA': 'Flock Safety ALPR Camera',
        'RAVEN_GUNSHOT': 'SoundThinking/ShotSpotter Raven Gunshot Detector',
        'PENGUIN': 'Penguin Surveillance Device',
        'PIGVISION': 'Pigvision Surveillance System'
    }

    # Threat level thresholds
    THREAT_THRESHOLDS = {
        'CRITICAL': 90,
        'HIGH': 70,
        'MEDIUM': 50,
        'LOW': 0
    }

    def __init__(
        self,
        api_url: str = 'http://localhost:5000',
        watchlist_db_path: str = 'watchlist.db',
        serial_port: Optional[str] = None,
        callback: Optional[Callable[[FlockDetection], None]] = None
    ):
        """
        Initialize Flock Detector

        Args:
            api_url: URL of Flock You Flask server
            watchlist_db_path: Path to CYT watchlist database
            serial_port: Serial port for direct ESP32 connection (optional)
            callback: Function to call on each new detection
        """
        self.api_url = api_url.rstrip('/')
        self.db_path = watchlist_db_path
        self.serial_port = serial_port
        self.callback = callback

        self._running = False
        self._poll_thread = None
        self._last_detection_id = 0

        self._init_database()
        logger.info(f"Flock Detector initialized (API: {api_url})")

    def _init_database(self):
        """Initialize flock_detections table in watchlist database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main detections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flock_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER,
                timestamp TEXT NOT NULL,
                device_type TEXT NOT NULL,
                protocol TEXT,
                detection_method TEXT,
                mac_address TEXT,
                rssi INTEGER,
                signal_strength TEXT,
                threat_score INTEGER,
                threat_level TEXT,
                latitude REAL,
                longitude REAL,
                altitude REAL,
                manufacturer TEXT,
                ssid TEXT,
                device_name TEXT,
                channel INTEGER,
                notes TEXT,
                import_date TEXT NOT NULL
            )
        ''')

        # Index for efficient querying
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flock_timestamp
            ON flock_detections(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flock_device_type
            ON flock_detections(device_type)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flock_mac
            ON flock_detections(mac_address)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flock_location
            ON flock_detections(latitude, longitude)
        ''')

        # Camera locations table (for known camera positions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flock_camera_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT UNIQUE,
                device_type TEXT,
                first_seen TEXT,
                last_seen TEXT,
                detection_count INTEGER DEFAULT 1,
                latitude REAL,
                longitude REAL,
                address TEXT,
                notes TEXT
            )
        ''')

        conn.commit()
        conn.close()

        logger.info(f"Flock detections database initialized: {self.db_path}")

    def check_api_status(self) -> Dict:
        """
        Check if Flock You API server is running

        Returns:
            Status dict with connection info
        """
        try:
            response = requests.get(f"{self.api_url}/api/status", timeout=5)
            if response.status_code == 200:
                return {
                    'connected': True,
                    'status': response.json()
                }
        except requests.exceptions.RequestException as e:
            logger.debug(f"API not available: {e}")

        return {
            'connected': False,
            'error': 'Flock You API server not running'
        }

    def get_detections(self, filter_type: str = 'all', cumulative: bool = False) -> List[Dict]:
        """
        Get detections from Flock You API

        Args:
            filter_type: Filter by detection method ('all', 'wifi', 'ble', etc.)
            cumulative: Get cumulative (all-time) vs session (current) detections

        Returns:
            List of detection dicts
        """
        try:
            params = {
                'filter': filter_type,
                'type': 'cumulative' if cumulative else 'session'
            }
            response = requests.get(
                f"{self.api_url}/api/detections",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"API returned status {response.status_code}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get detections: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        Get detection statistics from Flock You API

        Returns:
            Stats dict with counts and session info
        """
        try:
            response = requests.get(f"{self.api_url}/api/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to get stats: {e}")

        return {}

    def _parse_detection(self, raw_detection: Dict) -> Optional[FlockDetection]:
        """
        Parse raw detection from API into FlockDetection object

        Args:
            raw_detection: Raw detection dict from API

        Returns:
            FlockDetection object or None if parsing fails
        """
        try:
            # Determine device type from raw data
            device_type = raw_detection.get('device_type', 'FLOCK_CAMERA')
            if 'device_category' in raw_detection:
                category = raw_detection['device_category'].upper()
                if 'RAVEN' in category:
                    device_type = 'RAVEN_GUNSHOT'
                elif 'PENGUIN' in category:
                    device_type = 'PENGUIN'
                elif 'PIGVISION' in category:
                    device_type = 'PIGVISION'
                else:
                    device_type = 'FLOCK_CAMERA'

            # Get GPS data if available
            gps = raw_detection.get('gps', {})

            # Determine threat level from score
            threat_score = raw_detection.get('threat_score', 50)
            threat_level = 'LOW'
            for level, threshold in sorted(
                self.THREAT_THRESHOLDS.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                if threat_score >= threshold:
                    threat_level = level
                    break

            detection = FlockDetection(
                detection_id=raw_detection.get('id', 0),
                timestamp=raw_detection.get('server_timestamp', datetime.now().isoformat()),
                device_type=device_type,
                protocol=raw_detection.get('protocol', 'unknown'),
                detection_method=raw_detection.get('detection_method', 'unknown'),
                mac_address=raw_detection.get('mac_address', ''),
                rssi=raw_detection.get('rssi', 0),
                signal_strength=raw_detection.get('signal_strength', 'UNKNOWN'),
                threat_score=threat_score,
                threat_level=threat_level,
                latitude=gps.get('latitude'),
                longitude=gps.get('longitude'),
                altitude=gps.get('altitude'),
                manufacturer=raw_detection.get('manufacturer'),
                ssid=raw_detection.get('ssid'),
                device_name=raw_detection.get('device_name'),
                channel=raw_detection.get('channel'),
                notes=raw_detection.get('notes')
            )

            return detection

        except Exception as e:
            logger.warning(f"Failed to parse detection: {e}")
            return None

    def store_detection(self, detection: FlockDetection) -> int:
        """
        Store detection in watchlist database

        Args:
            detection: FlockDetection to store

        Returns:
            Database row ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO flock_detections (
                detection_id, timestamp, device_type, protocol, detection_method,
                mac_address, rssi, signal_strength, threat_score, threat_level,
                latitude, longitude, altitude, manufacturer, ssid, device_name,
                channel, notes, import_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            detection.detection_id,
            detection.timestamp,
            detection.device_type,
            detection.protocol,
            detection.detection_method,
            detection.mac_address,
            detection.rssi,
            detection.signal_strength,
            detection.threat_score,
            detection.threat_level,
            detection.latitude,
            detection.longitude,
            detection.altitude,
            detection.manufacturer,
            detection.ssid,
            detection.device_name,
            detection.channel,
            detection.notes,
            datetime.now().isoformat()
        ))

        row_id = cursor.lastrowid

        # Update camera locations table
        if detection.latitude and detection.longitude:
            cursor.execute('''
                INSERT INTO flock_camera_locations (
                    mac_address, device_type, first_seen, last_seen,
                    detection_count, latitude, longitude
                ) VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(mac_address) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    detection_count = detection_count + 1
            ''', (
                detection.mac_address,
                detection.device_type,
                detection.timestamp,
                detection.timestamp,
                detection.latitude,
                detection.longitude
            ))

        conn.commit()
        conn.close()

        logger.debug(f"Stored detection {detection.detection_id}: {detection.device_type}")
        return row_id

    def poll_detections(self, interval: float = 5.0) -> None:
        """
        Poll API for new detections continuously

        Args:
            interval: Polling interval in seconds
        """
        logger.info(f"Starting detection polling (interval: {interval}s)")

        while self._running:
            try:
                detections = self.get_detections()

                for raw in detections:
                    det_id = raw.get('id', 0)

                    # Skip already processed detections
                    if det_id <= self._last_detection_id:
                        continue

                    detection = self._parse_detection(raw)
                    if detection:
                        self.store_detection(detection)

                        # Call callback if registered
                        if self.callback:
                            self.callback(detection)

                        # Log alert
                        self._log_alert(detection)

                        self._last_detection_id = det_id

            except Exception as e:
                logger.error(f"Polling error: {e}")

            time.sleep(interval)

    def _log_alert(self, detection: FlockDetection) -> None:
        """Log detection as alert based on threat level"""
        device_desc = self.DEVICE_TYPES.get(detection.device_type, detection.device_type)

        msg = (
            f"[{detection.threat_level}] {device_desc} detected! "
            f"MAC: {detection.mac_address}, RSSI: {detection.rssi}dBm, "
            f"Method: {detection.detection_method}"
        )

        if detection.latitude and detection.longitude:
            msg += f", GPS: ({detection.latitude:.6f}, {detection.longitude:.6f})"

        if detection.threat_level == 'CRITICAL':
            logger.critical(msg)
        elif detection.threat_level == 'HIGH':
            logger.warning(msg)
        else:
            logger.info(msg)

    def start(self, poll_interval: float = 5.0) -> None:
        """
        Start detection monitoring

        Args:
            poll_interval: Polling interval in seconds
        """
        if self._running:
            logger.warning("Flock detector already running")
            return

        # Check API status first
        status = self.check_api_status()
        if not status['connected']:
            logger.error(f"Cannot start: {status.get('error', 'Unknown error')}")
            logger.info("Ensure Flock You server is running: cd flock-you/api && python flockyou.py")
            return

        self._running = True
        self._poll_thread = threading.Thread(
            target=self.poll_detections,
            args=(poll_interval,),
            daemon=True
        )
        self._poll_thread.start()

        logger.info("Flock detector started")

    def stop(self) -> None:
        """Stop detection monitoring"""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        logger.info("Flock detector stopped")

    def get_camera_locations(self) -> List[Dict]:
        """
        Get all known camera locations from database

        Returns:
            List of camera location dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM flock_camera_locations
            ORDER BY detection_count DESC
        ''')

        locations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return locations

    def get_recent_detections(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        Get recent detections from database

        Args:
            hours: How many hours back to search
            limit: Maximum number of results

        Returns:
            List of detection dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM flock_detections
            WHERE datetime(timestamp) >= datetime('now', ?)
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'-{hours} hours', limit))

        detections = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return detections

    def generate_kml(self, output_path: str = 'flock_cameras.kml') -> str:
        """
        Generate KML file with camera locations for Google Earth

        Args:
            output_path: Path to write KML file

        Returns:
            Path to generated KML file
        """
        locations = self.get_camera_locations()

        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>Flock Safety Camera Locations</name>
    <description>ALPR and surveillance cameras detected by CYT</description>

    <Style id="flock_camera">
        <IconStyle>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/camera.png</href></Icon>
            <scale>1.2</scale>
        </IconStyle>
    </Style>

    <Style id="raven_detector">
        <IconStyle>
            <Icon><href>http://maps.google.com/mapfiles/kml/shapes/target.png</href></Icon>
            <scale>1.2</scale>
        </IconStyle>
    </Style>
'''

        for loc in locations:
            if not loc.get('latitude') or not loc.get('longitude'):
                continue

            style = 'raven_detector' if loc['device_type'] == 'RAVEN_GUNSHOT' else 'flock_camera'
            device_desc = self.DEVICE_TYPES.get(loc['device_type'], loc['device_type'])

            kml_content += f'''
    <Placemark>
        <name>{device_desc}</name>
        <description>
            MAC: {loc['mac_address']}
            First Seen: {loc['first_seen']}
            Last Seen: {loc['last_seen']}
            Detection Count: {loc['detection_count']}
        </description>
        <styleUrl>#{style}</styleUrl>
        <Point>
            <coordinates>{loc['longitude']},{loc['latitude']},0</coordinates>
        </Point>
    </Placemark>
'''

        kml_content += '''
</Document>
</kml>'''

        with open(output_path, 'w') as f:
            f.write(kml_content)

        logger.info(f"Generated KML with {len(locations)} camera locations: {output_path}")
        return output_path

    def summary(self) -> Dict:
        """
        Get summary of all detections

        Returns:
            Summary dict with counts and statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count by device type
        cursor.execute('''
            SELECT device_type, COUNT(*) as count
            FROM flock_detections
            GROUP BY device_type
        ''')
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Count unique cameras
        cursor.execute('SELECT COUNT(*) FROM flock_camera_locations')
        unique_cameras = cursor.fetchone()[0]

        # Count by threat level
        cursor.execute('''
            SELECT threat_level, COUNT(*) as count
            FROM flock_detections
            GROUP BY threat_level
        ''')
        by_threat = {row[0]: row[1] for row in cursor.fetchall()}

        # Total detections
        cursor.execute('SELECT COUNT(*) FROM flock_detections')
        total = cursor.fetchone()[0]

        conn.close()

        return {
            'total_detections': total,
            'unique_cameras': unique_cameras,
            'by_device_type': by_type,
            'by_threat_level': by_threat
        }


def detection_callback(detection: FlockDetection):
    """Example callback for real-time alerts"""
    print(f"\n{'='*60}")
    print(f"FLOCK DETECTION ALERT!")
    print(f"{'='*60}")
    print(f"Type: {detection.device_type}")
    print(f"MAC: {detection.mac_address}")
    print(f"Threat Level: {detection.threat_level} (Score: {detection.threat_score})")
    print(f"Method: {detection.detection_method}")
    print(f"RSSI: {detection.rssi} dBm ({detection.signal_strength})")
    if detection.latitude and detection.longitude:
        print(f"Location: {detection.latitude:.6f}, {detection.longitude:.6f}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Flock Detector - CYT Integration Module")
    print("=" * 50)

    # Initialize detector
    detector = FlockDetector(
        api_url='http://localhost:5000',
        watchlist_db_path='watchlist.db',
        callback=detection_callback
    )

    # Check API status
    status = detector.check_api_status()
    print(f"\nAPI Status: {'Connected' if status['connected'] else 'Not Connected'}")

    if status['connected']:
        print("\nStarting detection monitoring...")
        print("Press Ctrl+C to stop\n")

        detector.start(poll_interval=2.0)

        try:
            while True:
                time.sleep(10)
                summary = detector.summary()
                print(f"Detections: {summary['total_detections']}, "
                      f"Unique Cameras: {summary['unique_cameras']}")
        except KeyboardInterrupt:
            print("\nStopping detector...")
            detector.stop()
    else:
        print("\nFlock You API server not running.")
        print("To start the server:")
        print("  1. cd ~/my_projects/0_active_projects/pentest/tools/flock-detection/flock-you/api")
        print("  2. python3 -m venv venv && source venv/bin/activate")
        print("  3. pip install -r requirements.txt")
        print("  4. python flockyou.py")
        print("\nOnce the server is running, restart this module.")

    print("\nSummary:", detector.summary())
