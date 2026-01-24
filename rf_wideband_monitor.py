#!/usr/bin/env python3

################################################################################
# rf_wideband_monitor.py
# Purpose: HackRF-based wideband RF surveillance detection for CYT
# Integrates: 1 MHz - 6 GHz spectrum monitoring to complement WiFi/BLE
# Created: 2026-01-08
################################################################################

import subprocess
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger('CYT.RFMonitor')


class RFWidebandMonitor:
    """
    HackRF-based wideband RF surveillance detection
    Complements Kismet WiFi/BLE monitoring for comprehensive threat detection

    Capabilities:
    - Wideband spectrum sweeps (1 MHz - 6 GHz)
    - Hidden camera detection (2.4 GHz video transmitters)
    - GPS tracker detection (GSM/LTE uplinks)
    - Drone control signal detection
    - RF correlation with WiFi/BLE detections
    """

    # Suspect frequency ranges (MHz)
    SUSPECT_FREQUENCIES = [
        (315, 315, "315 MHz - Key fobs, garage openers"),
        (433, 434, "433 MHz - Key fobs, sensors"),
        (900, 928, "ISM 900 MHz - Cordless phones, drone control"),
        (1575, 1575, "GPS L1 - GPS jamming detection"),
        (2400, 2483.5, "ISM 2.4 GHz - WiFi, Bluetooth, video transmitters"),
        (5150, 5850, "ISM 5 GHz - WiFi, drone control, FPV video"),
        (824, 894, "Cellular 850 - GSM uplink (GPS trackers)"),
        (1710, 1910, "Cellular AWS - LTE uplink (GPS trackers)"),
        (5650, 5850, "DJI drones - Control/video downlink")
    ]

    def __init__(self, config: Dict):
        """
        Initialize RF wideband monitor

        Args:
            config: RF monitoring configuration dict
        """
        self.config = config
        self.db_path = config.get('database', 'cyt_rf.db')
        self.sweep_interval = config.get('sweep_interval_seconds', 300)
        self.threshold_dbm = config.get('threshold_dbm', -60)
        self.correlation_enabled = config.get('correlation_enabled', True)

        self._init_database()

        # Check HackRF availability
        if not self._check_hackrf():
            logger.warning("HackRF device not detected - RF monitoring unavailable")
            self.available = False
        else:
            logger.info("HackRF device detected - RF monitoring enabled")
            self.available = True

    def _check_hackrf(self) -> bool:
        """Check if HackRF device is connected"""
        try:
            result = subprocess.run(
                ['hackrf_info'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "No HackRF boards found" not in result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _init_database(self):
        """Initialize RF detections database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rf_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_mhz REAL NOT NULL,
                power_dbm REAL NOT NULL,
                detection_type TEXT NOT NULL,
                threat_score INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                gps_lat REAL,
                gps_lon REAL,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rf_timestamp
            ON rf_detections(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rf_frequency
            ON rf_detections(frequency_mhz)
        ''')

        conn.commit()
        conn.close()

        logger.info(f"RF database initialized: {self.db_path}")

    def sweep_spectrum(
        self,
        start_mhz: float,
        end_mhz: float,
        bin_width_khz: int = 1000
    ) -> List[Dict]:
        """
        Use HackRF to sweep spectrum and identify strong signals

        Args:
            start_mhz: Start frequency in MHz
            end_mhz: End frequency in MHz
            bin_width_khz: FFT bin width in kHz

        Returns:
            List of detected signals above threshold
        """
        if not self.available:
            logger.warning("HackRF not available - skipping spectrum sweep")
            return []

        try:
            cmd = [
                'hackrf_sweep',
                '-f', f'{int(start_mhz)}:{int(end_mhz)}',
                '-w', str(bin_width_khz),
                '-1'  # Single sweep
            ]

            logger.info(f"Sweeping {start_mhz}-{end_mhz} MHz...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logger.error(f"hackrf_sweep failed: {result.stderr}")
                return []

            return self._parse_sweep_data(result.stdout)

        except subprocess.TimeoutExpired:
            logger.error("hackrf_sweep timeout")
            return []
        except Exception as e:
            logger.error(f"Sweep error: {e}")
            return []

    def _parse_sweep_data(self, sweep_output: str) -> List[Dict]:
        """
        Parse hackrf_sweep CSV output and identify anomalies

        Format: date, time, hz_low, hz_high, hz_bin_width, num_samples, dB, dB, dB...
        """
        signals = []

        for line in sweep_output.strip().split('\n'):
            if not line or line.startswith('date'):
                continue

            try:
                parts = line.split(', ')
                if len(parts) < 6:
                    continue

                hz_low = int(parts[2])
                hz_high = int(parts[3])
                db_values = [float(x) for x in parts[6:]]  # dB samples

                # Find peaks above threshold
                for i, power_db in enumerate(db_values):
                    if power_db > self.threshold_dbm:
                        freq_hz = hz_low + (i * (hz_high - hz_low) / len(db_values))

                        signals.append({
                            'frequency_mhz': freq_hz / 1e6,
                            'power_dbm': power_db,
                            'timestamp': datetime.now().isoformat()
                        })

            except (ValueError, IndexError) as e:
                logger.debug(f"Parse error: {e}")
                continue

        logger.info(f"Detected {len(signals)} signals above {self.threshold_dbm} dBm")
        return signals

    def detect_hidden_cameras(self) -> List[Dict]:
        """
        Scan for 2.4 GHz video transmitters (common in spy cameras)

        Returns:
            List of suspicious video transmitter signals
        """
        logger.info("Scanning for hidden cameras (2.4 GHz video TX)...")

        # Sweep 2.4 GHz ISM band with narrow bins for resolution
        signals = self.sweep_spectrum(2400, 2483.5, bin_width_khz=500)

        # Filter out known WiFi channels
        # WiFi channels: 2412, 2417, 2422, 2427, 2432, 2437, 2442, 2447, 2452, 2457, 2462 MHz
        wifi_channels = [2412 + (i * 5) for i in range(13)]
        wifi_bandwidth = 20  # MHz

        suspicious = []
        for signal in signals:
            freq = signal['frequency_mhz']

            # Check if signal is outside WiFi channels
            is_wifi = any(abs(freq - ch) < wifi_bandwidth/2 for ch in wifi_channels)

            if not is_wifi and signal['power_dbm'] > -50:  # Strong non-WiFi signal
                signal['detection_type'] = 'hidden_camera_suspect'
                signal['threat_score'] = 70
                signal['notes'] = f"Strong 2.4 GHz signal at {freq:.1f} MHz (not WiFi)"
                suspicious.append(signal)

        logger.info(f"Found {len(suspicious)} suspicious video TX signals")
        return suspicious

    def detect_gps_trackers(self) -> List[Dict]:
        """
        Monitor cellular uplink frequencies for GPS tracker GSM/LTE signals

        Returns:
            List of suspicious GPS tracker transmissions
        """
        logger.info("Scanning for GPS trackers (cellular uplinks)...")

        suspicious = []

        # Scan GSM 850 uplink (824-894 MHz)
        gsm_signals = self.sweep_spectrum(824, 894, bin_width_khz=200)
        for signal in gsm_signals:
            if signal['power_dbm'] > -70:
                signal['detection_type'] = 'gps_tracker_gsm'
                signal['threat_score'] = 60
                signal['notes'] = f"GSM uplink at {signal['frequency_mhz']:.1f} MHz"
                suspicious.append(signal)

        # Scan LTE Band 4 uplink (1710-1910 MHz)
        lte_signals = self.sweep_spectrum(1710, 1910, bin_width_khz=200)
        for signal in lte_signals:
            if signal['power_dbm'] > -70:
                signal['detection_type'] = 'gps_tracker_lte'
                signal['threat_score'] = 60
                signal['notes'] = f"LTE uplink at {signal['frequency_mhz']:.1f} MHz"
                suspicious.append(signal)

        logger.info(f"Found {len(suspicious)} suspicious GPS tracker signals")
        return suspicious

    def detect_drones(self) -> List[Dict]:
        """
        Scan for drone control signals (900 MHz, 2.4 GHz, 5.8 GHz)

        Returns:
            List of suspicious drone control signals
        """
        logger.info("Scanning for drone control signals...")

        suspicious = []

        # 900 MHz (long-range drones)
        signals_900 = self.sweep_spectrum(900, 928, bin_width_khz=100)
        for signal in signals_900:
            if signal['power_dbm'] > -60:
                signal['detection_type'] = 'drone_control_900'
                signal['threat_score'] = 50
                suspicious.append(signal)

        # 5.8 GHz (DJI and FPV drones)
        signals_58 = self.sweep_spectrum(5650, 5850, bin_width_khz=1000)
        for signal in signals_58:
            if signal['power_dbm'] > -55:
                signal['detection_type'] = 'drone_control_58'
                signal['threat_score'] = 60
                suspicious.append(signal)

        logger.info(f"Found {len(suspicious)} suspicious drone signals")
        return suspicious

    def correlate_with_kismet(
        self,
        rf_signals: List[Dict],
        kismet_db_path: str
    ) -> List[Dict]:
        """
        Cross-reference RF signals with Kismet WiFi/BLE detections
        Identify surveillance devices using both WiFi and RF transmission

        Args:
            rf_signals: RF detections from HackRF
            kismet_db_path: Path to Kismet database

        Returns:
            Correlated detections with increased threat scores
        """
        if not self.correlation_enabled:
            return rf_signals

        try:
            conn = sqlite3.connect(kismet_db_path)
            cursor = conn.cursor()

            correlated = []

            for signal in rf_signals:
                timestamp = signal['timestamp']

                # Query Kismet for WiFi/BLE devices detected at same time (±5 min)
                cursor.execute('''
                    SELECT device_mac, device_type, strongest_signal
                    FROM devices
                    WHERE first_time >= datetime(?, '-5 minutes')
                    AND first_time <= datetime(?, '+5 minutes')
                ''', (timestamp, timestamp))

                concurrent_devices = cursor.fetchall()

                if concurrent_devices:
                    signal['correlated_devices'] = len(concurrent_devices)
                    signal['threat_score'] = min(signal.get('threat_score', 50) + 20, 100)
                    signal['notes'] = (signal.get('notes', '') +
                                      f" | Correlated with {len(concurrent_devices)} WiFi/BLE devices")
                    correlated.append(signal)

            conn.close()

            logger.info(f"Correlated {len(correlated)} RF signals with Kismet detections")
            return correlated if correlated else rf_signals

        except Exception as e:
            logger.error(f"Correlation error: {e}")
            return rf_signals

    def save_detections(self, detections: List[Dict], gps_coords: Optional[Tuple[float, float]] = None):
        """
        Store RF detections in database

        Args:
            detections: List of RF detection dicts
            gps_coords: Optional (lat, lon) tuple for location tagging
        """
        if not detections:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for detection in detections:
            lat, lon = gps_coords if gps_coords else (None, None)

            cursor.execute('''
                INSERT INTO rf_detections
                (frequency_mhz, power_dbm, detection_type, threat_score, timestamp, gps_lat, gps_lon, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                detection['frequency_mhz'],
                detection['power_dbm'],
                detection.get('detection_type', 'unknown'),
                detection.get('threat_score', 0),
                detection['timestamp'],
                lat,
                lon,
                detection.get('notes', '')
            ))

        conn.commit()
        conn.close()

        logger.info(f"Saved {len(detections)} RF detections to database")

    def comprehensive_sweep(self) -> List[Dict]:
        """
        Perform comprehensive RF surveillance sweep
        Checks all suspect frequency ranges

        Returns:
            All detections from comprehensive sweep
        """
        logger.info("Starting comprehensive RF surveillance sweep...")

        all_detections = []

        # Targeted detection methods
        all_detections.extend(self.detect_hidden_cameras())
        all_detections.extend(self.detect_gps_trackers())
        all_detections.extend(self.detect_drones())

        # Additional suspect frequency sweeps
        for start, end, description in self.SUSPECT_FREQUENCIES:
            if start == end:  # Single frequency
                signals = self.sweep_spectrum(start - 5, start + 5, bin_width_khz=100)
            else:  # Range
                signals = self.sweep_spectrum(start, end, bin_width_khz=500)

            for signal in signals:
                signal['detection_type'] = description
                signal['threat_score'] = signal.get('threat_score', 30)
                all_detections.append(signal)

        logger.info(f"Comprehensive sweep complete: {len(all_detections)} total detections")
        return all_detections


if __name__ == '__main__':
    # Test module
    logging.basicConfig(level=logging.INFO)

    config = {
        'database': '/tmp/cyt_rf_test.db',
        'sweep_interval_seconds': 300,
        'threshold_dbm': -60,
        'correlation_enabled': False
    }

    monitor = RFWidebandMonitor(config)

    if monitor.available:
        print("✓ HackRF detected - running test sweep")
        detections = monitor.comprehensive_sweep()
        monitor.save_detections(detections)
        print(f"✓ Test complete: {len(detections)} detections saved")
    else:
        print("✗ HackRF not connected - module created but hardware needed for testing")
