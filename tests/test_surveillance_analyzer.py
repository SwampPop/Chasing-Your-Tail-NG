import unittest
from datetime import datetime, timedelta
import os

from surveillance_analyzer import SurveillanceAnalyzer
from surveillance_detector import SuspiciousDevice, SurveillanceDetector

class TestSurveillanceAnalyzer(unittest.TestCase):
    """
    Test suite for the SurveillanceAnalyzer class.
    """
    
    def test_analyze_for_stalking(self):
        """
        Tests the stalking analysis logic correctly filters devices.
        """
        # ARRANGE: Create mock data
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        mock_suspicious_devices = [
            # This device IS a stalking candidate (should PASS)
            SuspiciousDevice(
                mac='AA:AA:AA:AA:AA:AA', persistence_score=0.9, appearances=[], reasons=[],
                first_seen=yesterday, last_seen=now, total_appearances=20,
                locations_seen=['Location A', 'Location B', 'Location C']),
            
            # This device IS NOT a stalking candidate (CHANGED: appearances is now too low)
            SuspiciousDevice(
                mac='BB:BB:BB:BB:BB:BB', persistence_score=0.9, appearances=[], reasons=[],
                first_seen=yesterday, last_seen=now, total_appearances=5, # CHANGED from 50
                locations_seen=['Location A']),
                
            # This device IS NOT a stalking candidate (low score)
            SuspiciousDevice(
                mac='CC:CC:CC:CC:CC:CC', persistence_score=0.4, appearances=[], reasons=[],
                first_seen=now - timedelta(hours=2), last_seen=now, total_appearances=3,
                locations_seen=['Location A', 'Location B'])
        ]

        # Temporarily disable the complex __init__ to isolate our test
        original_init = SurveillanceAnalyzer.__init__
        SurveillanceAnalyzer.__init__ = lambda s, c='config.json': None
        analyzer = SurveillanceAnalyzer()
        SurveillanceAnalyzer.__init__ = original_init

        # Manually attach a mock detector that returns our fake data
        class MockDetector:
            def analyze_surveillance_patterns(self):
                return mock_suspicious_devices
        analyzer.detector = MockDetector()
        
        # ACT: Run the function we want to test
        stalking_candidates = analyzer.analyze_for_stalking(min_persistence_score=0.7)
        
        # ASSERT: Check the results
        self.assertEqual(len(stalking_candidates), 1)
        self.assertEqual(stalking_candidates[0].mac, 'AA:AA:AA:AA:AA:AA')
        self.assertTrue(hasattr(stalking_candidates[0], 'stalking_score'))