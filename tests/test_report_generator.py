import unittest
from datetime import datetime
from collections import defaultdict

# We need to import the classes we are testing and the data structures it depends on
from report_generator import ReportGenerator
from surveillance_detector import SuspiciousDevice, DeviceAppearance

class TestReportGenerator(unittest.TestCase):
    """
    Test suite for the ReportGenerator class.
    """

    def setUp(self):
        """
        This method is called before each test. It sets up mock (fake) data
        that mimics the output of the SurveillanceDetector.
        """
        # ARRANGE: Create mock data
        now = datetime.now()
        
        # Create a history of all device sightings
        self.all_appearances = [
            DeviceAppearance('AA:AA:AA:AA:AA:AA', now.timestamp() - 300, 'Location A', [], 'Wi-Fi Client'),
            DeviceAppearance('AA:AA:AA:AA:AA:AA', now.timestamp() - 200, 'Location B', [], 'Wi-Fi Client'),
            DeviceAppearance('BB:BB:BB:BB:BB:BB', now.timestamp() - 100, 'Location A', [], 'Wi-Fi AP'),
        ]
        
        # Create a history grouped by MAC address
        self.device_history = defaultdict(list)
        for app in self.all_appearances:
            self.device_history[app.mac].append(app)
            
        # Create a list of devices that the detector has flagged as suspicious
        self.suspicious_devices = [
            SuspiciousDevice(
                mac='AA:AA:AA:AA:AA:AA',
                persistence_score=0.8,
                appearances=self.device_history['AA:AA:AA:AA:AA:AA'],
                reasons=['Followed across 2 different locations'],
                first_seen=now, last_seen=now, total_appearances=2,
                locations_seen=['Location A', 'Location B']
            )
        ]
        
        # Define the thresholds the reporter will use
        self.thresholds = {'min_appearances': 3}

    def test_generate_analysis_statistics(self):
        """
        Tests if the reporter calculates summary statistics correctly.
        """
        # ACT: Create an instance of the ReportGenerator.
        # Its __init__ method automatically calculates the stats.
        reporter = ReportGenerator(
            suspicious_devices=self.suspicious_devices,
            all_appearances=self.all_appearances,
            device_history=self.device_history,
            thresholds=self.thresholds
        )
        
        # ASSERT: Check if the calculated stats match our mock data
        self.assertEqual(reporter.stats['total_appearances'], 3)
        self.assertEqual(reporter.stats['unique_devices'], 2)
        self.assertEqual(reporter.stats['unique_locations'], 2)
        
        # Test the multi-location calculation (1 out of 2 devices was multi-location)
        self.assertEqual(reporter.stats['multi_location_rate'], 0.5)