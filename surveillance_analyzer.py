#!/usr/bin/env python3
"""
Integrated Surveillance Analysis Tool for CYT

Orchestrates deep analysis of Kismet capture data by correlating device
appearances with GPS locations, detecting surveillance patterns, and
generating professional intelligence reports (Markdown, HTML, KML).

Usage:
    python3 surveillance_analyzer.py                  # Auto-detect latest DB
    python3 surveillance_analyzer.py --db path.kismet # Specify DB
    python3 surveillance_analyzer.py --demo           # Demo with simulated GPS
    python3 surveillance_analyzer.py --output ./out   # Custom output directory
"""
import argparse
import glob
import json
import logging
import os
import pathlib
import sys
import time
from datetime import datetime

from surveillance_detector import (SurveillanceDetector,
                                   load_appearances_from_kismet,
                                   SuspiciousDevice)
from gps_tracker import GPSTracker, KMLExporter, simulate_gps_data
from secure_credentials import secure_config_loader
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class SurveillanceAnalyzer:
    """Orchestrates surveillance analysis across Kismet captures.

    Ties together the detection engine, GPS tracker, and report generator
    to produce a complete surveillance intelligence picture.
    """

    def __init__(self, config: dict):
        self.config = config
        self.detector = SurveillanceDetector(config)
        self.gps_tracker = GPSTracker(config)
        self.kml_exporter = KMLExporter()
        self.suspicious_devices = []
        self.kismet_dbs_analyzed = []
        self.total_appearances_loaded = 0

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def analyze_kismet_data(self, db_path: str,
                            location_id: str = "unknown") -> int:
        """Load device appearances from a single Kismet database.

        Args:
            db_path: Path to the Kismet SQLite database.
            location_id: Friendly name for the capture location.

        Returns:
            Number of device appearances loaded.
        """
        logger.info(f"Analyzing Kismet database: {db_path}")
        count = load_appearances_from_kismet(
            db_path, self.detector, location_id)
        self.kismet_dbs_analyzed.append(db_path)
        self.total_appearances_loaded += count
        logger.info(
            f"Loaded {count} appearances from {os.path.basename(db_path)}")
        return count

    def analyze_all_databases(self, db_pattern: str) -> int:
        """Load all Kismet databases matching a glob pattern.

        Each database is treated as a separate location session.

        Args:
            db_pattern: Glob pattern (e.g. ``logs/kismet/*.kismet``).

        Returns:
            Total appearances loaded across all databases.
        """
        if os.path.isdir(db_pattern):
            db_pattern = os.path.join(db_pattern, "*.kismet")

        db_files = sorted(glob.glob(db_pattern), key=os.path.getctime)
        if not db_files:
            logger.warning(f"No Kismet databases found for: {db_pattern}")
            return 0

        total = 0
        for idx, db_path in enumerate(db_files, 1):
            location_id = f"capture_{idx}_{os.path.basename(db_path)}"
            total += self.analyze_kismet_data(db_path, location_id)

        logger.info(
            f"Analyzed {len(db_files)} databases, "
            f"{total} total appearances")
        return total

    # ------------------------------------------------------------------
    # GPS integration
    # ------------------------------------------------------------------

    def add_gps_location(self, latitude: float, longitude: float,
                         name: str = None) -> str:
        """Register a GPS location for correlation.

        Returns the cluster-assigned location ID.
        """
        return self.gps_tracker.add_gps_reading(
            latitude, longitude, location_name=name)

    def load_demo_gps(self) -> None:
        """Load simulated GPS waypoints for demo/testing."""
        for lat, lon, name in simulate_gps_data():
            self.gps_tracker.add_gps_reading(lat, lon, location_name=name)
        logger.info("Demo GPS data loaded (3 waypoints)")

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def run_full_analysis(self) -> list:
        """Run the complete surveillance detection analysis.

        Returns:
            List of SuspiciousDevice objects found.
        """
        logger.info("Running full surveillance pattern analysis...")
        self.suspicious_devices = (
            self.detector.analyze_surveillance_patterns())

        # Correlate devices with GPS locations
        cross_location = self.gps_tracker.get_devices_across_locations()
        if cross_location:
            logger.info(
                f"Devices seen across multiple locations: "
                f"{len(cross_location)}")

        logger.info(
            f"Analysis complete: {len(self.suspicious_devices)} "
            f"suspicious devices identified")
        return self.suspicious_devices

    def analyze_for_stalking(
            self, min_persistence_score: float = 0.7) -> list:
        """Specifically analyze for stalking patterns."""
        if not self.suspicious_devices:
            self.run_full_analysis()

        stalking_candidates = []
        for device in self.suspicious_devices:
            if device.persistence_score < min_persistence_score:
                continue

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
                    f"Persistent over {time_span_hours / 24:.1f} days")

            if stalking_score >= 0.6:
                device.stalking_score = stalking_score
                device.stalking_reasons = stalking_reasons
                stalking_candidates.append(device)

        return stalking_candidates

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_reports(self, output_dir: str = "surveillance_reports"
                         ) -> dict:
        """Generate all report formats.

        Args:
            output_dir: Directory to write reports into.

        Returns:
            Dict with paths to generated files.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        paths = {}

        # Markdown / HTML report
        md_path = os.path.join(output_dir,
                               f"surveillance_report_{timestamp}.md")
        reporter = ReportGenerator(
            suspicious_devices=self.suspicious_devices,
            all_appearances=self.detector.appearances,
            device_history=self.detector.device_history,
            thresholds=self.detector.thresholds,
            config=self.config
        )
        reporter.generate_surveillance_report(md_path)
        paths['markdown'] = md_path
        logger.info(f"Markdown report: {md_path}")

        html_path = md_path.replace('.md', '.html')
        if os.path.exists(html_path):
            paths['html'] = html_path

        # KML visualization
        kml_path = os.path.join(output_dir,
                                f"surveillance_map_{timestamp}.kml")
        self.kml_exporter.generate_kml(
            self.gps_tracker,
            surveillance_devices=self.suspicious_devices,
            output_file=kml_path)
        paths['kml'] = kml_path
        logger.info(f"KML visualization: {kml_path}")

        return paths

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def get_summary(self) -> dict:
        """Return a concise summary of the analysis results."""
        return {
            'databases_analyzed': len(self.kismet_dbs_analyzed),
            'total_appearances': self.total_appearances_loaded,
            'unique_devices': len(self.detector.device_history),
            'suspicious_devices': len(self.suspicious_devices),
            'gps_locations': len(self.gps_tracker.location_sessions),
            'cross_location_devices': len(
                self.gps_tracker.get_devices_across_locations()),
        }

    def print_summary(self) -> None:
        """Print a human-readable analysis summary to stdout."""
        s = self.get_summary()
        print("\n" + "=" * 60)
        print("  CYT SURVEILLANCE ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"  Databases analyzed:      {s['databases_analyzed']}")
        print(f"  Total appearances:       {s['total_appearances']}")
        print(f"  Unique devices:          {s['unique_devices']}")
        print(f"  Suspicious devices:      {s['suspicious_devices']}")
        print(f"  GPS locations:           {s['gps_locations']}")
        print(f"  Cross-location devices:  {s['cross_location_devices']}")
        print("=" * 60)

        if self.suspicious_devices:
            print("\n  TOP SUSPICIOUS DEVICES:")
            for i, dev in enumerate(self.suspicious_devices[:5], 1):
                score_pct = dev.persistence_score * 100
                locs = len(dev.locations_seen)
                print(f"    {i}. {dev.mac}  "
                      f"Score: {score_pct:.0f}%  "
                      f"Locations: {locs}  "
                      f"Appearances: {dev.total_appearances}")
        else:
            print("\n  No suspicious devices identified.")
        print()


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def _find_latest_kismet_db(config: dict) -> str:
    """Locate the most recent Kismet database using config paths."""
    pattern = config.get('paths', {}).get('kismet_logs', 'logs/kismet')
    if os.path.isdir(pattern):
        pattern = os.path.join(pattern, "*.kismet")

    files = glob.glob(pattern)
    if not files:
        # Fallback to test capture
        if os.path.exists("test_capture.kismet"):
            return "test_capture.kismet"
        return None
    return max(files, key=os.path.getctime)


def main():
    parser = argparse.ArgumentParser(
        description="CYT Surveillance Analysis Tool")
    parser.add_argument(
        '--db', type=str, default=None,
        help='Path to a specific Kismet database (or glob pattern)')
    parser.add_argument(
        '--output', type=str, default='surveillance_reports',
        help='Output directory for reports (default: surveillance_reports)')
    parser.add_argument(
        '--demo', action='store_true',
        help='Run with simulated GPS data for demonstration')
    parser.add_argument(
        '--stalking', action='store_true',
        help='Run stalking-specific analysis (higher threshold)')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Enable verbose/debug logging')

    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f'logs/analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
        ]
    )

    # Ensure log directory
    pathlib.Path('logs').mkdir(exist_ok=True)

    # Load config
    try:
        config, _ = secure_config_loader('config.json')
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        # Fall back to raw JSON
        with open('config.json', 'r') as f:
            config = json.load(f)

    # Create analyzer
    analyzer = SurveillanceAnalyzer(config)

    # Load GPS data
    if args.demo:
        analyzer.load_demo_gps()
        print("Running in DEMO mode with simulated GPS data.")

    # Determine database path
    db_path = args.db
    if not db_path:
        db_path = _find_latest_kismet_db(config)

    if not db_path:
        print("No Kismet database found. Use --db to specify one, "
              "or ensure logs/kismet/ contains .kismet files.")
        sys.exit(1)

    # Load data
    if '*' in db_path or os.path.isdir(db_path):
        analyzer.analyze_all_databases(db_path)
    else:
        if not os.path.exists(db_path):
            print(f"Database not found: {db_path}")
            sys.exit(1)
        analyzer.analyze_kismet_data(db_path)

    # Run analysis
    analyzer.run_full_analysis()

    # Stalking analysis if requested
    if args.stalking:
        stalkers = analyzer.analyze_for_stalking()
        if stalkers:
            print(f"\nSTALKING CANDIDATES: {len(stalkers)}")
            for s in stalkers:
                print(f"  {s.mac} - Score: {s.stalking_score:.2f} "
                      f"- {', '.join(s.stalking_reasons)}")

    # Generate reports
    report_paths = analyzer.generate_reports(args.output)

    # Print summary
    analyzer.print_summary()

    print("Reports generated:")
    for fmt, path in report_paths.items():
        print(f"  {fmt}: {path}")


if __name__ == "__main__":
    main()
