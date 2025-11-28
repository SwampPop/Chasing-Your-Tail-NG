#!/usr/bin/env python3
"""
Integrated Surveillance Analysis Tool for CYT
"""
import argparse
import glob
import json
import logging
import os
import time
from datetime import datetime
import sqlite3
import math

from surveillance_detector import (SurveillanceDetector,
                                     load_appearances_from_kismet,
                                     SuspiciousDevice)
from gps_tracker import (GPSTracker, KMLExporter,
                         simulate_gps_data)
from secure_credentials import secure_config_loader
from report_generator import ReportGenerator

# ... (The rest of the full surveillance_analyzer.py script goes here)
# Make sure the version you have in your project includes the following method
# inside the SurveillanceAnalyzer class.


class SurveillanceAnalyzer:
    # ... (all the other methods like __init__, analyze_kismet_data, etc.)

    def analyze_for_stalking(
            self, min_persistence_score: float = 0.7) -> list:
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
    # ... (the rest of the class)
