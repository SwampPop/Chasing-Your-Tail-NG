#!/usr/bin/env python3
"""
WATCHDOG Reporter — Detection logging, map generation, and CVD memo creation.

Handles:
- JSON/SQLite detection logging with GPS correlation
- Interactive Folium map generation with camera/ALPR/drone layers
- CVD memo generation from Jinja2 template for responsible disclosure
- Notification routing via Apprise (Telegram, ntfy, etc.)
"""
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jinja2 import Template

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "templates")
CVD_TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "cvd_memo.md")

# Try imports for optional features
try:
    import folium
    from folium.plugins import HeatMap, MarkerCluster
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import apprise
    APPRISE_AVAILABLE = True
except ImportError:
    APPRISE_AVAILABLE = False


class DetectionLogger:
    """Log camera/surveillance detections to SQLite database."""

    def __init__(self, db_path: str = "watchdog_detections.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create detection tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                manufacturer TEXT,
                device_type TEXT,
                confidence REAL,
                ssid TEXT,
                rssi INTEGER,
                channel INTEGER,
                latitude REAL,
                longitude REAL,
                timestamp REAL,
                detection_method TEXT,
                is_setup_mode INTEGER,
                first_seen REAL,
                last_seen REAL,
                seen_count INTEGER DEFAULT 1,
                details TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_id TEXT UNIQUE NOT NULL,
                severity TEXT,
                device_type TEXT,
                manufacturer TEXT,
                description TEXT,
                evidence TEXT,
                remediation TEXT,
                discovery_date TEXT,
                disclosure_deadline TEXT,
                status TEXT DEFAULT 'OPEN',
                memo_generated INTEGER DEFAULT 0,
                memo_sent INTEGER DEFAULT 0,
                escalation_level INTEGER DEFAULT 0,
                details TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_detections_mac
            ON detections(mac)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                mac TEXT NOT NULL,
                attack_type TEXT,
                severity TEXT,
                reason TEXT,
                signal INTEGER,
                count INTEGER DEFAULT 1,
                evidence TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_attacks_mac
            ON attacks(mac)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_attacks_ts
            ON attacks(ts)
        """)
        conn.commit()
        conn.close()

    def log_detection(self, detection) -> None:
        """Log a CameraDetection to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if MAC already exists
        cursor.execute(
            "SELECT id, seen_count, first_seen FROM detections WHERE mac = ?",
            (detection.mac,)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE detections SET
                    rssi = ?, channel = ?, latitude = ?, longitude = ?,
                    last_seen = ?, seen_count = seen_count + 1,
                    confidence = MAX(confidence, ?)
                WHERE mac = ?
            """, (
                detection.rssi, detection.channel,
                detection.latitude, detection.longitude,
                detection.timestamp, detection.confidence,
                detection.mac
            ))
        else:
            cursor.execute("""
                INSERT INTO detections
                (mac, manufacturer, device_type, confidence, ssid, rssi,
                 channel, latitude, longitude, timestamp, detection_method,
                 is_setup_mode, first_seen, last_seen, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detection.mac, detection.manufacturer, detection.device_type,
                detection.confidence, detection.ssid, detection.rssi,
                detection.channel, detection.latitude, detection.longitude,
                detection.timestamp, detection.detection_method,
                1 if detection.is_setup_mode else 0,
                detection.timestamp, detection.timestamp,
                json.dumps(detection.match_details)
            ))

        conn.commit()
        conn.close()

    def log_attack(self, alert: Dict) -> None:
        """Persist an attack alert (deauth, disassoc, brief appearance, etc.).

        Expected keys: ts (float), mac, attack_type, severity, reason,
        signal (int), count (int), evidence (dict — serialized to JSON).
        Any missing key is substituted with a sensible default.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO attacks
                (ts, mac, attack_type, severity, reason, signal, count, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    float(alert.get("ts", time.time())),
                    alert.get("mac", ""),
                    alert.get("attack_type", "UNKNOWN"),
                    alert.get("severity", "med"),
                    alert.get("reason", ""),
                    int(alert.get("signal", 0) or 0),
                    int(alert.get("count", 1) or 1),
                    json.dumps(alert.get("evidence", {})),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_attacks(self, limit: int = 100) -> List[Dict]:
        """Return the most recent attacks, newest first."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM attacks ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_detections(self) -> List[Dict]:
        """Retrieve all detections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM detections ORDER BY last_seen DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_detections_with_gps(self) -> List[Dict]:
        """Retrieve detections that have GPS coordinates."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM detections
            WHERE latitude != 0 AND longitude != 0
            ORDER BY last_seen DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]


class WatchdogMapGenerator:
    """Generate interactive Folium maps of surveillance device detections."""

    DEVICE_COLORS = {
        'camera': 'blue',
        'alpr': 'red',
        'drone': 'orange',
        'ble_tracker': 'purple',
        'unknown': 'gray',
    }

    DEVICE_ICONS = {
        'camera': 'eye-open',
        'alpr': 'road',
        'drone': 'plane',
        'ble_tracker': 'tag',
        'unknown': 'question-sign',
    }

    def __init__(self):
        if not FOLIUM_AVAILABLE:
            raise ImportError("Folium required: pip install folium")

    def generate_map(self, detections: List[Dict],
                     output_file: str = "watchdog_map.html",
                     center_lat: float = 0.0,
                     center_lon: float = 0.0) -> str:
        """
        Generate interactive surveillance detection map.

        Default center: 0,0 (auto-centers on detection data if available)
        """
        # Filter detections with GPS
        gps_detections = [
            d for d in detections
            if d.get('latitude', 0) != 0 and d.get('longitude', 0) != 0
        ]

        # Use first detection as center if available
        if gps_detections:
            center_lat = gps_detections[0]['latitude']
            center_lon = gps_detections[0]['longitude']

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles="CartoDB dark_matter",
        )

        # Add OpenStreetMap as alternative tile layer
        folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)

        # --- Camera detections layer ---
        for device_type in ['camera', 'alpr', 'drone', 'ble_tracker', 'unknown']:
            type_detections = [
                d for d in gps_detections
                if d.get('device_type') == device_type
            ]
            if not type_detections:
                continue

            group = folium.FeatureGroup(
                name=f"{device_type.upper()} ({len(type_detections)})"
            )

            for det in type_detections:
                conf = det.get('confidence', 0)
                seen = det.get('seen_count', 1)
                first = datetime.fromtimestamp(
                    det.get('first_seen', 0)
                ).strftime('%Y-%m-%d %H:%M') if det.get('first_seen') else 'Unknown'
                last = datetime.fromtimestamp(
                    det.get('last_seen', 0)
                ).strftime('%Y-%m-%d %H:%M') if det.get('last_seen') else 'Unknown'

                popup_html = f"""
                <div style="font-family: monospace; min-width: 250px;">
                    <b style="color: {self.DEVICE_COLORS.get(device_type, 'gray')};">
                        {device_type.upper()}: {det.get('manufacturer', 'Unknown')}
                    </b><br>
                    <b>MAC:</b> {det.get('mac', 'Unknown')}<br>
                    <b>SSID:</b> {det.get('ssid', 'N/A')}<br>
                    <b>Confidence:</b> {conf:.0%}<br>
                    <b>RSSI:</b> {det.get('rssi', 'N/A')} dBm<br>
                    <b>Channel:</b> {det.get('channel', 'N/A')}<br>
                    <b>Method:</b> {det.get('detection_method', 'N/A')}<br>
                    <b>First seen:</b> {first}<br>
                    <b>Last seen:</b> {last}<br>
                    <b>Times seen:</b> {seen}
                </div>
                """

                folium.Marker(
                    location=[det['latitude'], det['longitude']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{det.get('manufacturer', '?')} ({device_type})",
                    icon=folium.Icon(
                        color=self.DEVICE_COLORS.get(device_type, 'gray'),
                        icon=self.DEVICE_ICONS.get(device_type, 'info-sign'),
                    ),
                ).add_to(group)

            group.add_to(m)

        # --- Heatmap layer ---
        if gps_detections:
            heat_data = [
                [d['latitude'], d['longitude']]
                for d in gps_detections
            ]
            HeatMap(
                heat_data,
                name="Detection Density",
                min_opacity=0.3,
                radius=25,
                blur=15,
            ).add_to(m)

        # Layer control
        folium.LayerControl().add_to(m)

        # Save
        m.save(output_file)
        logger.info(
            f"WATCHDOG map generated: {output_file} "
            f"({len(gps_detections)} detections plotted)"
        )
        return output_file


class CVDMemoGenerator:
    """Generate Coordinated Vulnerability Disclosure memos."""

    def __init__(self, template_path: str = CVD_TEMPLATE_PATH):
        try:
            with open(template_path, 'r') as f:
                self.template = Template(f.read())
            logger.info(f"CVD template loaded from {template_path}")
        except FileNotFoundError:
            logger.error(f"CVD template not found: {template_path}")
            self.template = None

    def generate_finding_id(self, device_type: str) -> str:
        """Generate a unique finding ID."""
        prefix = {
            'camera': 'CAM',
            'alpr': 'ALPR',
            'drone': 'UAV',
        }.get(device_type, 'WD')
        timestamp = datetime.now().strftime('%Y%m%d')
        seq = int(time.time()) % 10000
        return f"WD-{prefix}-{timestamp}-{seq:04d}"

    def should_generate_memo(self, severity: str, days_open: int = 0) -> bool:
        """
        Determine if a finding meets the actionable threshold.

        Only CRITICAL and HIGH generate memos.
        MEDIUM escalates to HIGH after 30 days.
        """
        if severity in ('CRITICAL', 'HIGH'):
            return True
        if severity == 'MEDIUM' and days_open >= 30:
            return True
        return False

    def generate_memo(self, finding: Dict,
                      researcher_name: str = "",
                      researcher_contact: str = "",
                      output_dir: str = "watchdog_reports") -> Optional[str]:
        """
        Generate a CVD memo from a finding.

        Returns the output file path, or None if template unavailable.
        """
        if not self.template:
            logger.error("Cannot generate memo — template not loaded")
            return None

        os.makedirs(output_dir, exist_ok=True)

        discovery_date = finding.get('discovery_date',
                                     datetime.now().strftime('%Y-%m-%d'))
        disclosure_deadline = (
            datetime.strptime(discovery_date, '%Y-%m-%d') + timedelta(days=90)
        ).strftime('%Y-%m-%d')
        followup_30 = (
            datetime.strptime(discovery_date, '%Y-%m-%d') + timedelta(days=30)
        ).strftime('%Y-%m-%d')
        followup_60 = (
            datetime.strptime(discovery_date, '%Y-%m-%d') + timedelta(days=60)
        ).strftime('%Y-%m-%d')

        finding_id = finding.get('finding_id',
                                 self.generate_finding_id(finding.get('device_type', 'unknown')))

        context = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'researcher_name': researcher_name,
            'researcher_contact': researcher_contact,
            'recipient_name': finding.get('recipient', 'Security Team'),
            'finding_id': finding_id,
            'severity': finding.get('severity', 'HIGH'),
            'device_type': finding.get('device_type', 'Surveillance Camera'),
            'manufacturer': finding.get('manufacturer', 'Unknown'),
            'affected_system': finding.get('affected_system', 'IP Camera'),
            'location_description': finding.get('location', 'Orleans Parish, LA'),
            'discovery_date': discovery_date,
            'disclosure_deadline': disclosure_deadline,
            'followup_date_30': followup_30,
            'followup_date_60': followup_60,
            'summary': finding.get('summary', ''),
            'description': finding.get('description', ''),
            'impact': finding.get('impact', ''),
            'cvss_score': finding.get('cvss_score', 'N/A'),
            'cve_reference': finding.get('cve_reference', 'N/A'),
            'evidence': finding.get('evidence', ''),
            'reproduction_steps': finding.get('reproduction_steps', ''),
            'remediation': finding.get('remediation', ''),
            'urgency': finding.get('urgency', 'High'),
            'remediation_effort': finding.get('remediation_effort', 'Low — configuration change'),
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'escalation_contact_1': finding.get('escalation_contact',
                                                'Project NOLA / City of New Orleans'),
            'authorization_basis': finding.get('authorization_basis',
                                               'Passive observation of publicly broadcast WiFi signals'),
        }

        memo_content = self.template.render(**context)

        output_file = os.path.join(
            output_dir, f"{finding_id}_CVD_MEMO.md"
        )
        with open(output_file, 'w') as f:
            f.write(memo_content)

        logger.info(f"CVD memo generated: {output_file}")
        return output_file


class WatchdogNotifier:
    """Send WATCHDOG alerts via Apprise (Telegram, ntfy, etc.)."""

    def __init__(self, apprise_urls: List[str] = None):
        self.apprise_obj = None
        if APPRISE_AVAILABLE and apprise_urls:
            self.apprise_obj = apprise.Apprise()
            for url in apprise_urls:
                self.apprise_obj.add(url)
            logger.info(
                f"WATCHDOG notifier: {len(apprise_urls)} target(s) configured"
            )

    def notify_detection(self, detection) -> None:
        """Send notification for a new detection."""
        if not self.apprise_obj:
            return

        # Only notify for confidence >= 0.5
        if detection.confidence < 0.5:
            return

        type_emoji = {
            'camera': '📷',
            'alpr': '🚨',
            'drone': '🛸',
            'ble_tracker': '📍',
        }.get(detection.device_type, '⚠️')

        title = f"{type_emoji} WATCHDOG: {detection.device_type.upper()}"
        body = (
            f"Manufacturer: {detection.manufacturer}\n"
            f"MAC: {detection.mac}\n"
            f"SSID: {detection.ssid or 'N/A'}\n"
            f"RSSI: {detection.rssi} dBm | CH: {detection.channel}\n"
            f"Confidence: {detection.confidence:.0%}\n"
            f"Method: {detection.detection_method}"
        )

        if detection.latitude and detection.longitude:
            body += f"\nLocation: {detection.latitude:.4f}, {detection.longitude:.4f}"

        notify_type = (
            apprise.NotifyType.FAILURE if detection.confidence >= 0.8
            else apprise.NotifyType.WARNING
        )

        try:
            self.apprise_obj.notify(
                title=title, body=body, notify_type=notify_type
            )
        except Exception as e:
            logger.error(f"WATCHDOG notification failed: {e}")

    def notify_finding(self, finding_id: str, severity: str,
                       description: str) -> None:
        """Send notification for an actionable finding."""
        if not self.apprise_obj:
            return

        title = f"🔒 WATCHDOG Finding: {finding_id}"
        body = (
            f"Severity: {severity}\n"
            f"{description}\n\n"
            f"CVD memo generated. Review and send within 24 hours."
        )

        self.apprise_obj.notify(
            title=title, body=body,
            notify_type=apprise.NotifyType.FAILURE
        )
