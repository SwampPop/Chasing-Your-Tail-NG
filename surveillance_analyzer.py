#!/usr/bin/env python3
"""
Integrated Surveillance Analysis Tool for CYT
Analyzes both Wi-Fi and BLE devices for surveillance patterns
"""
import argparse
import glob
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional

from surveillance_detector import (
    SurveillanceDetector,
    load_appearances_from_kismet,
    load_ble_appearances_from_kismet,
    SuspiciousDevice
)
from gps_tracker import GPSTracker, KMLExporter, simulate_gps_data
from secure_credentials import secure_config_loader
from report_generator import ReportGenerator
from cyt_constants import PersistenceLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SurveillanceAnalyzer:
    """
    Main surveillance analysis orchestrator
    Coordinates detection, GPS tracking, and reporting
    """

    def __init__(self, config: Dict, kismet_db_paths: List[str], demo_mode: bool = False):
        """
        Initialize surveillance analyzer

        Args:
            config: Configuration dictionary
            kismet_db_paths: List of Kismet database paths to analyze
            demo_mode: If True, use simulated GPS data
        """
        self.config = config
        self.kismet_db_paths = kismet_db_paths
        self.demo_mode = demo_mode

        # Initialize components
        self.detector = SurveillanceDetector(config)
        self.gps_tracker = GPSTracker(config)
        # ReportGenerator is created when needed (after data is loaded)

        # Statistics
        self.stats = {
            'wifi_appearances': 0,
            'ble_appearances': 0,
            'total_devices': 0,
            'suspicious_devices': 0,
            'high_threat_devices': 0
        }

    def load_data_from_kismet_databases(self) -> None:
        """Load both Wi-Fi and BLE device data from all Kismet databases"""
        logger.info(f"Loading data from {len(self.kismet_db_paths)} Kismet databases...")

        for db_path in self.kismet_db_paths:
            if not os.path.exists(db_path):
                logger.warning(f"Database not found: {db_path}")
                continue

            try:
                # Extract location ID from database filename
                location_id = self._extract_location_from_path(db_path)

                # Load GPS data if available
                if not self.demo_mode:
                    self._load_gps_from_kismet(db_path, location_id)

                # Load Wi-Fi device appearances
                wifi_count = load_appearances_from_kismet(
                    db_path, self.detector, location_id
                )
                self.stats['wifi_appearances'] += wifi_count
                logger.info(f"Loaded {wifi_count} Wi-Fi appearances from {db_path}")

                # Load BLE device appearances
                ble_count = load_ble_appearances_from_kismet(
                    db_path, self.detector, location_id
                )
                self.stats['ble_appearances'] += ble_count
                logger.info(f"Loaded {ble_count} BLE appearances from {db_path}")

            except Exception as e:
                logger.error(f"Error loading data from {db_path}: {e}")
                continue

        total_appearances = self.stats['wifi_appearances'] + self.stats['ble_appearances']
        logger.info(
            f"Total appearances loaded: {total_appearances} "
            f"(Wi-Fi: {self.stats['wifi_appearances']}, BLE: {self.stats['ble_appearances']})"
        )

    def _generate_demo_ble_devices(self) -> None:
        """Generate simulated BLE devices for demo mode"""
        import time
        from cyt_constants import DeviceType

        # Simulated BLE devices with varying threat levels
        demo_devices = [
            # High-threat DJI drone appearing multiple times
            {
                'mac': 'AA:BB:CC:DD:EE:01',
                'type': DeviceType.BLE_DRONE.value,
                'appearances': 8,
                'locations': ['Phoenix_North', 'Phoenix_Central', 'Phoenix_South']
            },
            # Medium-threat AirTag (tracker)
            {
                'mac': 'AA:BB:CC:DD:EE:02',
                'type': DeviceType.BLE_TRACKER.value,
                'appearances': 5,
                'locations': ['Phoenix_North', 'Phoenix_Central']
            },
            # Low-threat Fitbit (wearable)
            {
                'mac': 'AA:BB:CC:DD:EE:03',
                'type': DeviceType.BLE_WEARABLE.value,
                'appearances': 3,
                'locations': ['Phoenix_North']
            },
        ]

        base_time = time.time()
        for device in demo_devices:
            for i in range(device['appearances']):
                location = device['locations'][i % len(device['locations'])]
                # Spread appearances over 6 hours
                timestamp = base_time - (6 * 3600) + (i * (6 * 3600 / device['appearances']))

                self.detector.add_device_appearance(
                    mac=device['mac'],
                    timestamp=timestamp,
                    location_id=location,
                    ssids_probed=[],
                    device_type=device['type']
                )

        logger.info(f"Generated {len(demo_devices)} demo BLE devices with multiple appearances")
        self.stats['ble_appearances'] = sum(d['appearances'] for d in demo_devices)

    def _extract_location_from_path(self, db_path: str) -> str:
        """Extract location identifier from database path"""
        # Extract timestamp from Kismet filename format: Kismet-YYYYMMDD-HH-MM-SS-1.kismet
        basename = os.path.basename(db_path)
        if basename.startswith('Kismet-'):
            # Use timestamp as location ID
            parts = basename.replace('.kismet', '').split('-')
            if len(parts) >= 4:
                return f"{parts[1]}-{parts[2]}{parts[3]}"  # YYYYMMDD-HHMM
        return "location_unknown"

    def _load_gps_from_kismet(self, db_path: str, location_id: str) -> None:
        """Load GPS coordinates from Kismet database"""
        try:
            from secure_database import SecureKismetDB

            with SecureKismetDB(db_path) as db:
                # Query GPS data from Kismet (if available)
                # Kismet stores GPS in snapshots table
                query = "SELECT lat, lon, alt, ts_sec FROM snapshots WHERE lat IS NOT NULL LIMIT 1"
                results = db.execute_safe_query(query)

                if results:
                    row = results[0]
                    latitude = row['lat']
                    longitude = row['lon']
                    timestamp = row['ts_sec']

                    if latitude != 0 and longitude != 0:
                        self.gps_tracker.add_location(
                            latitude, longitude, timestamp, location_id
                        )
                        logger.info(
                            f"Loaded GPS coordinates: {latitude}, {longitude} "
                            f"for {location_id}"
                        )

        except Exception as e:
            logger.debug(f"No GPS data available in {db_path}: {e}")

    def analyze_surveillance_patterns(self) -> List[SuspiciousDevice]:
        """Run surveillance detection analysis"""
        logger.info("Analyzing surveillance patterns...")

        suspicious_devices = self.detector.analyze_surveillance_patterns()

        self.stats['total_devices'] = len(self.detector.device_history)
        self.stats['suspicious_devices'] = len(suspicious_devices)

        # Count high-threat devices
        high_threat = sum(
            1 for device in suspicious_devices
            if device.persistence_score >= PersistenceLevel.HIGH.threshold
        )
        self.stats['high_threat_devices'] = high_threat

        logger.info(
            f"Analysis complete: {self.stats['suspicious_devices']} suspicious devices found "
            f"({high_threat} high-threat)"
        )

        return suspicious_devices

    def analyze_for_stalking(self, min_persistence_score: float = 0.7) -> List[SuspiciousDevice]:
        """Specifically analyze for stalking patterns"""
        suspicious_devices = self.detector.analyze_surveillance_patterns()

        stalking_candidates = []
        for device in suspicious_devices:
            if device.persistence_score >= min_persistence_score:
                locations = len(device.locations_seen)
                appearances = device.total_appearances

                time_span = device.last_seen - device.first_seen
                time_span_hours = time_span.total_seconds() / 3600

                stalking_score = 0
                stalking_reasons = []

                if locations >= 3:
                    stalking_score += 0.4
                    stalking_reasons.append(
                        f"Follows across {locations} locations")

                if appearances >= 10:
                    stalking_score += 0.3
                    stalking_reasons.append(
                        f"High frequency ({appearances} appearances)")

                if time_span_hours >= 24:
                    stalking_score += 0.3
                    stalking_reasons.append(
                        f"Persistent over {time_span_hours/24:.1f} days")

                if stalking_score >= 0.6:
                    # These attributes are dynamically added for the report
                    device.stalking_score = stalking_score
                    device.stalking_reasons = stalking_reasons
                    stalking_candidates.append(device)

        return stalking_candidates

    def generate_reports(self, suspicious_devices: List[SuspiciousDevice]) -> Dict[str, str]:
        """Generate surveillance analysis reports"""
        logger.info("Generating reports...")

        # Create ReportGenerator with actual data
        report_generator = ReportGenerator(
            suspicious_devices=suspicious_devices,
            all_appearances=self.detector.appearances,
            device_history=self.detector.device_history,
            thresholds=self.detector.thresholds,
            config=self.config
        )

        # Create output directory
        report_dir = "surveillance_reports"
        os.makedirs(report_dir, exist_ok=True)

        # Generate timestamp for report filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate Markdown report
        md_filename = f"surveillance_report_{timestamp}.md"
        md_path = os.path.join(report_dir, md_filename)

        # Use the actual ReportGenerator method
        markdown_content = report_generator.generate_surveillance_report(md_path)
        logger.info(f"Markdown report saved: {md_path}")

        # Note: HTML generation via pandoc is optional, skip for now
        return {
            'markdown': md_path
        }

    def export_kml(self, suspicious_devices: List[SuspiciousDevice]) -> Optional[str]:
        """Export surveillance data to KML for Google Earth"""
        if not self.gps_tracker.locations:
            logger.warning("No GPS data available, skipping KML export")
            return None

        logger.info("Exporting KML visualization...")

        # Create output directory
        kml_dir = "kml_files"
        os.makedirs(kml_dir, exist_ok=True)

        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kml_filename = f"surveillance_map_{timestamp}.kml"
        kml_path = os.path.join(kml_dir, kml_filename)

        # Use KMLExporter to generate KML
        exporter = KMLExporter()
        kml_content = exporter.generate_kml(
            self.gps_tracker,  # Pass GPSTracker object, not list
            suspicious_devices
        )

        with open(kml_path, 'w') as f:
            f.write(kml_content)

        logger.info(f"KML file saved: {kml_path}")
        return kml_path

    def run_full_analysis(self) -> Dict:
        """Run complete surveillance analysis workflow"""
        logger.info("=" * 60)
        logger.info("CHASING YOUR TAIL - Surveillance Analysis")
        logger.info("=" * 60)

        # Load demo GPS data if in demo mode
        if self.demo_mode:
            logger.info("Demo mode: Using simulated GPS and BLE data")
            self.gps_tracker.locations = simulate_gps_data()
            # Generate simulated BLE devices for demo
            self._generate_demo_ble_devices()
        else:
            # Step 1: Load data from Kismet databases
            self.load_data_from_kismet_databases()

        if not self.detector.device_history:
            logger.error("No device data loaded. Exiting.")
            return {'error': 'No data loaded'}

        # Step 2: Run surveillance analysis
        suspicious_devices = self.analyze_surveillance_patterns()

        if not suspicious_devices:
            logger.info("No suspicious devices detected.")
            return {'status': 'No threats detected', 'stats': self.stats}

        # Step 3: Generate reports
        report_paths = self.generate_reports(suspicious_devices)

        # Step 4: Export KML if GPS data available
        kml_path = self.export_kml(suspicious_devices)

        # Print summary
        self._print_summary(suspicious_devices)

        logger.info("=" * 60)
        logger.info("Analysis complete!")
        logger.info("=" * 60)

        return {
            'status': 'success',
            'suspicious_devices': len(suspicious_devices),
            'reports': report_paths,
            'kml': kml_path,
            'stats': self.stats
        }

    def _print_summary(self, suspicious_devices: List[SuspiciousDevice]) -> None:
        """Print analysis summary to console"""
        print("\n" + "=" * 60)
        print("SURVEILLANCE ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total devices tracked: {self.stats['total_devices']}")
        print(f"Wi-Fi appearances: {self.stats['wifi_appearances']}")
        print(f"BLE appearances: {self.stats['ble_appearances']}")
        print(f"Suspicious devices: {self.stats['suspicious_devices']}")
        print(f"High-threat devices: {self.stats['high_threat_devices']}")
        print()

        if suspicious_devices:
            print("TOP THREATS:")
            print("-" * 60)
            for i, device in enumerate(suspicious_devices[:5], 1):
                threat_level = PersistenceLevel.from_score(device.persistence_score)
                print(f"{i}. {device.mac}")
                print(f"   Type: {device.appearances[0].device_type if device.appearances else 'Unknown'}")
                print(f"   Threat Level: {threat_level.value} {threat_level.emoji}")
                print(f"   Persistence Score: {device.persistence_score:.2f}")
                print(f"   Locations: {len(device.locations_seen)}")
                print(f"   Appearances: {device.total_appearances}")
                print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Chasing Your Tail - Surveillance Detection System'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode with simulated GPS data'
    )
    parser.add_argument(
        '--kismet-dir',
        type=str,
        default='.',
        help='Directory containing Kismet .kismet database files (default: current directory)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to config.json (default: config.json)'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config, _ = secure_config_loader(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        # Use default config
        config = {}

    # Find Kismet databases
    kismet_db_paths = glob.glob(os.path.join(args.kismet_dir, '*.kismet'))

    if not kismet_db_paths:
        logger.error(f"No Kismet databases found in {args.kismet_dir}")
        logger.info("Please specify --kismet-dir pointing to directory with .kismet files")
        sys.exit(1)

    logger.info(f"Found {len(kismet_db_paths)} Kismet database(s)")

    # Run analysis
    analyzer = SurveillanceAnalyzer(config, kismet_db_paths, demo_mode=args.demo)
    results = analyzer.run_full_analysis()

    if 'error' in results:
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
