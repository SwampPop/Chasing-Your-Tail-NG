#!/usr/bin/env python3

################################################################################
# imsi_detector.py
# Purpose: Detect IMSI catchers (fake cell towers / Stingrays) using HackRF
# Integration: Uses kalibrate-hackrf for GSM scanning, gr-gsm for analysis
# Created: 2026-01-17
################################################################################

import os
import sys
import json
import time
import sqlite3
import logging
import subprocess
import threading
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger('CYT.IMSIDetector')


class ThreatLevel(Enum):
    """IMSI catcher threat levels"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class CellTower:
    """Represents a GSM cell tower"""
    arfcn: int  # Absolute Radio Frequency Channel Number
    frequency_mhz: float
    power_db: float
    mcc: Optional[int] = None  # Mobile Country Code
    mnc: Optional[int] = None  # Mobile Network Code
    lac: Optional[int] = None  # Location Area Code
    cell_id: Optional[int] = None
    first_seen: str = ""
    last_seen: str = ""
    detection_count: int = 1
    band: str = ""
    notes: str = ""


@dataclass
class IMSICatcherAlert:
    """Represents an IMSI catcher detection alert"""
    alert_id: int
    timestamp: str
    threat_level: ThreatLevel
    confidence: float  # 0.0 - 1.0
    arfcn: int
    frequency_mhz: float
    indicators: List[str] = field(default_factory=list)
    ie_ratio: Optional[float] = None  # Identity-Exposing ratio
    baseline_ie_ratio: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: str = ""


class IMSIDetector:
    """
    Detect IMSI catchers using HackRF One

    Detection methods:
    1. GSM base station scanning (kalibrate-hackrf)
    2. Cell tower anomaly detection (frequency, power, LAC/CID changes)
    3. Identity-Exposing message ratio analysis (requires gr-gsm in VM)

    Architecture:
    - macOS: Use kalibrate-hackrf for GSM scanning (Phase 1)
    - Linux/VM: Full gr-gsm analysis for IMSI detection (Phase 2)
    """

    # GSM frequency bands (MHz)
    GSM_BANDS = {
        'GSM850': (824.0, 849.0, 869.0, 894.0),  # US
        'GSM900': (890.0, 915.0, 935.0, 960.0),  # EU
        'EGSM': (880.0, 915.0, 925.0, 960.0),
        'DCS': (1710.0, 1785.0, 1805.0, 1880.0),
        'PCS': (1850.0, 1910.0, 1930.0, 1990.0),  # US
        'GSM-R': (876.0, 915.0, 921.0, 960.0),  # Railways
    }

    # Known legitimate carriers (US) - MCC 310, 311, 312
    US_CARRIERS = {
        (310, 260): 'T-Mobile',
        (310, 410): 'AT&T',
        (311, 480): 'Verizon',
        (310, 120): 'Sprint',
        (310, 26): 'T-Mobile',
        (311, 882): 'Verizon',
    }

    # Anomaly thresholds
    THRESHOLDS = {
        'ie_ratio_normal': 0.03,  # 3% baseline for LTE
        'ie_ratio_gsm_normal': 0.06,  # 6% baseline for GSM
        'ie_ratio_suspicious': 0.10,  # 10% = suspicious
        'ie_ratio_critical': 0.30,  # 30%+ = IMSI catcher likely
        'power_deviation_db': 20,  # Unusual if >20dB stronger than baseline
        'lac_change_threshold': 3,  # Suspicious if LAC changes >3 times/hour
    }

    def __init__(
        self,
        watchlist_db_path: str = 'watchlist.db',
        kalibrate_path: Optional[str] = None,
        callback: Optional[Callable[[IMSICatcherAlert], None]] = None
    ):
        """
        Initialize IMSI Detector

        Args:
            watchlist_db_path: Path to CYT watchlist database
            kalibrate_path: Path to kalibrate-hackrf binary (auto-detect if None)
            callback: Function to call on each alert
        """
        self.db_path = watchlist_db_path
        self.callback = callback

        # Find kalibrate-hackrf
        self.kalibrate_path = kalibrate_path or self._find_kalibrate()

        self._running = False
        self._scan_thread = None
        self._baseline_towers: Dict[int, CellTower] = {}

        self._init_database()
        logger.info(f"IMSI Detector initialized (kalibrate: {self.kalibrate_path})")

    def _find_kalibrate(self) -> Optional[str]:
        """Find kalibrate-hackrf binary"""
        # Check common locations
        paths = [
            os.path.expanduser('~/my_projects/0_active_projects/pentest/tools/stingray-detection/kalibrate-hackrf/src/kal'),
            '/usr/local/bin/kal',
            '/usr/bin/kal',
            '/opt/homebrew/bin/kal',
        ]

        for path in paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # Try which
        try:
            result = subprocess.run(['which', 'kal'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        logger.warning("kalibrate-hackrf not found - GSM scanning unavailable")
        return None

    def _init_database(self):
        """Initialize IMSI detection tables in watchlist database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Cell towers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cell_towers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arfcn INTEGER NOT NULL,
                frequency_mhz REAL NOT NULL,
                power_db REAL,
                mcc INTEGER,
                mnc INTEGER,
                lac INTEGER,
                cell_id INTEGER,
                band TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                detection_count INTEGER DEFAULT 1,
                is_baseline INTEGER DEFAULT 0,
                notes TEXT,
                UNIQUE(arfcn, mcc, mnc, lac, cell_id)
            )
        ''')

        # IMSI catcher alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS imsi_catcher_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                threat_level INTEGER NOT NULL,
                confidence REAL,
                arfcn INTEGER,
                frequency_mhz REAL,
                indicators TEXT,
                ie_ratio REAL,
                baseline_ie_ratio REAL,
                latitude REAL,
                longitude REAL,
                notes TEXT
            )
        ''')

        # LAC/CID change tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lac_cid_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                arfcn INTEGER,
                old_lac INTEGER,
                new_lac INTEGER,
                old_cid INTEGER,
                new_cid INTEGER,
                suspicious INTEGER DEFAULT 0
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_towers_arfcn ON cell_towers(arfcn)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON imsi_catcher_alerts(timestamp)')

        conn.commit()
        conn.close()

        logger.info(f"IMSI detection database initialized: {self.db_path}")

    def check_hackrf(self) -> Dict:
        """
        Check if HackRF is connected and working

        Returns:
            Status dict with connection info
        """
        try:
            result = subprocess.run(
                ['hackrf_info'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if 'Serial number' in result.stdout:
                # Parse serial number
                serial_match = re.search(r'Serial number: (\w+)', result.stdout)
                serial = serial_match.group(1) if serial_match else 'Unknown'

                return {
                    'connected': True,
                    'serial': serial,
                    'info': result.stdout.strip()
                }
            else:
                return {
                    'connected': False,
                    'error': 'No HackRF boards found'
                }

        except FileNotFoundError:
            return {
                'connected': False,
                'error': 'hackrf_info not installed'
            }
        except subprocess.TimeoutExpired:
            return {
                'connected': False,
                'error': 'HackRF check timed out'
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }

    def scan_gsm_band(self, band: str = 'GSM850') -> List[CellTower]:
        """
        Scan GSM band for cell towers using kalibrate-hackrf

        Args:
            band: GSM band to scan (GSM850, GSM900, EGSM, DCS, PCS)

        Returns:
            List of detected cell towers
        """
        if not self.kalibrate_path:
            logger.error("kalibrate-hackrf not available")
            return []

        if band not in self.GSM_BANDS:
            logger.error(f"Unknown GSM band: {band}")
            return []

        logger.info(f"Scanning {band} band for GSM base stations...")

        try:
            result = subprocess.run(
                [self.kalibrate_path, '-s', band, '-g', '30', '-l', '30'],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for scanning
            )

            towers = []
            now = datetime.now().isoformat()

            # Parse kalibrate output
            # Format: chan: 128 (937.4MHz + 10.2kHz)    power: 1234567.89
            for line in result.stdout.split('\n'):
                match = re.search(
                    r'chan:\s+(\d+)\s+\((\d+\.?\d*)MHz\s*([+-]\s*[\d.]+kHz)?\)\s+power:\s+([\d.]+)',
                    line
                )
                if match:
                    arfcn = int(match.group(1))
                    freq = float(match.group(2))
                    power = float(match.group(4))

                    tower = CellTower(
                        arfcn=arfcn,
                        frequency_mhz=freq,
                        power_db=10 * (power / 1e6) if power > 0 else 0,  # Rough conversion
                        first_seen=now,
                        last_seen=now,
                        band=band
                    )
                    towers.append(tower)

            logger.info(f"Found {len(towers)} cell towers on {band}")
            return towers

        except subprocess.TimeoutExpired:
            logger.error(f"GSM scan timed out on {band}")
            return []
        except Exception as e:
            logger.error(f"GSM scan failed: {e}")
            return []

    def scan_all_bands(self) -> List[CellTower]:
        """
        Scan all GSM bands for cell towers

        Returns:
            List of all detected cell towers
        """
        all_towers = []

        # US bands first
        for band in ['GSM850', 'PCS', 'GSM900', 'DCS']:
            towers = self.scan_gsm_band(band)
            all_towers.extend(towers)

        return all_towers

    def store_tower(self, tower: CellTower) -> int:
        """
        Store cell tower in database

        Args:
            tower: CellTower to store

        Returns:
            Database row ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO cell_towers (
                    arfcn, frequency_mhz, power_db, mcc, mnc, lac, cell_id,
                    band, first_seen, last_seen, detection_count, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(arfcn, mcc, mnc, lac, cell_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    power_db = excluded.power_db,
                    detection_count = detection_count + 1
            ''', (
                tower.arfcn,
                tower.frequency_mhz,
                tower.power_db,
                tower.mcc,
                tower.mnc,
                tower.lac,
                tower.cell_id,
                tower.band,
                tower.first_seen,
                tower.last_seen,
                tower.notes
            ))

            row_id = cursor.lastrowid
            conn.commit()
            return row_id

        except Exception as e:
            logger.error(f"Failed to store tower: {e}")
            return -1
        finally:
            conn.close()

    def analyze_towers(self, towers: List[CellTower]) -> List[IMSICatcherAlert]:
        """
        Analyze cell towers for IMSI catcher indicators

        Detection heuristics:
        1. Unusual power levels (much stronger than baseline)
        2. Unknown carrier (MCC/MNC not in known list)
        3. LAC/CID changes (rogue tower spoofing)
        4. Frequency deviation from normal allocation

        Args:
            towers: List of cell towers to analyze

        Returns:
            List of IMSI catcher alerts
        """
        alerts = []
        now = datetime.now().isoformat()

        for tower in towers:
            indicators = []
            threat_score = 0

            # Check 1: Power level anomaly
            if tower.arfcn in self._baseline_towers:
                baseline = self._baseline_towers[tower.arfcn]
                power_diff = tower.power_db - baseline.power_db

                if power_diff > self.THRESHOLDS['power_deviation_db']:
                    indicators.append(f"Unusual power: {power_diff:.1f}dB above baseline")
                    threat_score += 30

            # Check 2: Unknown carrier (if MCC/MNC available)
            if tower.mcc and tower.mnc:
                carrier_key = (tower.mcc, tower.mnc)
                if carrier_key not in self.US_CARRIERS:
                    indicators.append(f"Unknown carrier: MCC={tower.mcc}, MNC={tower.mnc}")
                    threat_score += 40

            # Check 3: Compare to baseline for LAC/CID changes
            if tower.arfcn in self._baseline_towers:
                baseline = self._baseline_towers[tower.arfcn]
                if tower.lac and baseline.lac and tower.lac != baseline.lac:
                    indicators.append(f"LAC changed: {baseline.lac} -> {tower.lac}")
                    threat_score += 25
                if tower.cell_id and baseline.cell_id and tower.cell_id != baseline.cell_id:
                    indicators.append(f"Cell ID changed: {baseline.cell_id} -> {tower.cell_id}")
                    threat_score += 25

            # Generate alert if indicators found
            if indicators:
                threat_level = ThreatLevel.NONE
                if threat_score >= 80:
                    threat_level = ThreatLevel.CRITICAL
                elif threat_score >= 60:
                    threat_level = ThreatLevel.HIGH
                elif threat_score >= 40:
                    threat_level = ThreatLevel.MEDIUM
                elif threat_score > 0:
                    threat_level = ThreatLevel.LOW

                alert = IMSICatcherAlert(
                    alert_id=0,  # Will be set on store
                    timestamp=now,
                    threat_level=threat_level,
                    confidence=min(threat_score / 100.0, 1.0),
                    arfcn=tower.arfcn,
                    frequency_mhz=tower.frequency_mhz,
                    indicators=indicators,
                    notes=f"Detected on {tower.band}"
                )
                alerts.append(alert)

        return alerts

    def store_alert(self, alert: IMSICatcherAlert) -> int:
        """Store IMSI catcher alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO imsi_catcher_alerts (
                timestamp, threat_level, confidence, arfcn, frequency_mhz,
                indicators, ie_ratio, baseline_ie_ratio, latitude, longitude, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.timestamp,
            alert.threat_level.value,
            alert.confidence,
            alert.arfcn,
            alert.frequency_mhz,
            json.dumps(alert.indicators),
            alert.ie_ratio,
            alert.baseline_ie_ratio,
            alert.latitude,
            alert.longitude,
            alert.notes
        ))

        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return alert_id

    def establish_baseline(self, scan_count: int = 3) -> Dict:
        """
        Establish baseline of normal cell towers

        Args:
            scan_count: Number of scans to average for baseline

        Returns:
            Baseline statistics
        """
        logger.info(f"Establishing baseline with {scan_count} scans...")

        all_towers: Dict[int, List[CellTower]] = {}

        for i in range(scan_count):
            logger.info(f"Baseline scan {i+1}/{scan_count}")
            towers = self.scan_all_bands()

            for tower in towers:
                if tower.arfcn not in all_towers:
                    all_towers[tower.arfcn] = []
                all_towers[tower.arfcn].append(tower)

            if i < scan_count - 1:
                time.sleep(30)  # Wait between scans

        # Average the measurements
        for arfcn, tower_list in all_towers.items():
            avg_power = sum(t.power_db for t in tower_list) / len(tower_list)

            baseline_tower = tower_list[0]
            baseline_tower.power_db = avg_power
            baseline_tower.detection_count = len(tower_list)

            self._baseline_towers[arfcn] = baseline_tower

            # Store as baseline in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE cell_towers SET is_baseline = 1 WHERE arfcn = ?',
                (arfcn,)
            )
            conn.commit()
            conn.close()

        logger.info(f"Baseline established: {len(self._baseline_towers)} towers")

        return {
            'tower_count': len(self._baseline_towers),
            'bands_covered': list(set(t.band for t in self._baseline_towers.values())),
            'arfcns': list(self._baseline_towers.keys())
        }

    def continuous_scan(self, interval: float = 60.0) -> None:
        """
        Continuously scan for IMSI catchers

        Args:
            interval: Seconds between scans
        """
        logger.info(f"Starting continuous IMSI catcher scanning (interval: {interval}s)")

        while self._running:
            try:
                towers = self.scan_all_bands()

                # Store all towers
                for tower in towers:
                    self.store_tower(tower)

                # Analyze for anomalies
                alerts = self.analyze_towers(towers)

                for alert in alerts:
                    alert.alert_id = self.store_alert(alert)

                    # Log and callback
                    self._log_alert(alert)
                    if self.callback:
                        self.callback(alert)

            except Exception as e:
                logger.error(f"Scan error: {e}")

            time.sleep(interval)

    def _log_alert(self, alert: IMSICatcherAlert) -> None:
        """Log IMSI catcher alert"""
        msg = (
            f"[{alert.threat_level.name}] IMSI Catcher Indicator! "
            f"ARFCN: {alert.arfcn} ({alert.frequency_mhz:.1f} MHz), "
            f"Confidence: {alert.confidence:.0%}"
        )

        for indicator in alert.indicators:
            msg += f"\n  - {indicator}"

        if alert.threat_level == ThreatLevel.CRITICAL:
            logger.critical(msg)
        elif alert.threat_level == ThreatLevel.HIGH:
            logger.warning(msg)
        else:
            logger.info(msg)

    def start(self, interval: float = 60.0, establish_baseline: bool = True) -> bool:
        """
        Start IMSI catcher detection

        Args:
            interval: Seconds between scans
            establish_baseline: Whether to establish baseline first

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("IMSI detector already running")
            return False

        # Check HackRF
        hackrf_status = self.check_hackrf()
        if not hackrf_status['connected']:
            logger.error(f"Cannot start: {hackrf_status.get('error')}")
            return False

        # Check kalibrate
        if not self.kalibrate_path:
            logger.error("kalibrate-hackrf not available")
            return False

        # Establish baseline if requested
        if establish_baseline and not self._baseline_towers:
            self.establish_baseline()

        self._running = True
        self._scan_thread = threading.Thread(
            target=self.continuous_scan,
            args=(interval,),
            daemon=True
        )
        self._scan_thread.start()

        logger.info("IMSI catcher detection started")
        return True

    def stop(self) -> None:
        """Stop IMSI catcher detection"""
        self._running = False
        if self._scan_thread:
            self._scan_thread.join(timeout=10)
        logger.info("IMSI catcher detection stopped")

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent IMSI catcher alerts"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM imsi_catcher_alerts
            WHERE datetime(timestamp) >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{hours} hours',))

        alerts = []
        for row in cursor.fetchall():
            alert = dict(row)
            alert['indicators'] = json.loads(alert['indicators'])
            alert['threat_level'] = ThreatLevel(alert['threat_level']).name
            alerts.append(alert)

        conn.close()
        return alerts

    def get_known_towers(self) -> List[Dict]:
        """Get all known cell towers from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM cell_towers
            ORDER BY detection_count DESC
        ''')

        towers = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return towers

    def summary(self) -> Dict:
        """Get detection summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count towers
        cursor.execute('SELECT COUNT(*) FROM cell_towers')
        tower_count = cursor.fetchone()[0]

        # Count baseline towers
        cursor.execute('SELECT COUNT(*) FROM cell_towers WHERE is_baseline = 1')
        baseline_count = cursor.fetchone()[0]

        # Count alerts by level
        cursor.execute('''
            SELECT threat_level, COUNT(*)
            FROM imsi_catcher_alerts
            GROUP BY threat_level
        ''')
        alerts_by_level = {ThreatLevel(row[0]).name: row[1] for row in cursor.fetchall()}

        # Total alerts
        cursor.execute('SELECT COUNT(*) FROM imsi_catcher_alerts')
        total_alerts = cursor.fetchone()[0]

        conn.close()

        return {
            'total_towers': tower_count,
            'baseline_towers': baseline_count,
            'total_alerts': total_alerts,
            'alerts_by_level': alerts_by_level,
            'hackrf_connected': self.check_hackrf()['connected'],
            'kalibrate_available': self.kalibrate_path is not None
        }


def alert_callback(alert: IMSICatcherAlert):
    """Example callback for IMSI catcher alerts"""
    print(f"\n{'='*70}")
    print(f"IMSI CATCHER ALERT - {alert.threat_level.name}")
    print(f"{'='*70}")
    print(f"ARFCN: {alert.arfcn}")
    print(f"Frequency: {alert.frequency_mhz:.1f} MHz")
    print(f"Confidence: {alert.confidence:.0%}")
    print(f"Indicators:")
    for indicator in alert.indicators:
        print(f"  - {indicator}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("IMSI Catcher Detector - CYT Integration Module")
    print("=" * 60)

    # Initialize detector
    detector = IMSIDetector(
        watchlist_db_path='watchlist.db',
        callback=alert_callback
    )

    # Check HackRF status
    hackrf = detector.check_hackrf()
    print(f"\nHackRF Status: {'Connected' if hackrf['connected'] else 'Not Connected'}")
    if hackrf['connected']:
        print(f"Serial: {hackrf['serial']}")
    else:
        print(f"Error: {hackrf.get('error')}")

    # Check kalibrate
    print(f"\nkalibrate-hackrf: {'Available' if detector.kalibrate_path else 'Not Found'}")
    if detector.kalibrate_path:
        print(f"Path: {detector.kalibrate_path}")

    print(f"\nSummary: {detector.summary()}")

    # Demo scan if HackRF connected
    if hackrf['connected']:
        print("\nStarting GSM band scan...")
        print("This will take ~2 minutes per band.\n")

        towers = detector.scan_gsm_band('GSM850')
        print(f"\nFound {len(towers)} towers on GSM850:")
        for tower in towers:
            print(f"  ARFCN {tower.arfcn}: {tower.frequency_mhz:.1f} MHz, Power: {tower.power_db:.1f}")
    else:
        print("\nConnect HackRF to enable GSM scanning.")
        print("\nTo test without hardware:")
        print("  1. Connect HackRF via USB")
        print("  2. Run: hackrf_info (should show serial number)")
        print("  3. Re-run this script")
