"""Tests for surveillance_detector.py — persistence scoring edge cases."""
import unittest
import time

from surveillance_detector import (
    SurveillanceDetector, DeviceAppearance, SuspiciousDevice
)


def _make_config(**overrides):
    base = {'detection_thresholds': {
        'min_appearances': 3,
        'time_span_hours_min': 1.0,
        'appearance_frequency_threshold': 0.5,
        'persistence_score_high': 0.8,
        'persistence_score_critical': 0.9,
    }}
    base['detection_thresholds'].update(overrides)
    return base


class TestSurveillanceDetector(unittest.TestCase):

    def test_empty_appearances_returns_nothing(self):
        detector = SurveillanceDetector(_make_config())
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(results, [])

    def test_below_min_appearances_not_flagged(self):
        detector = SurveillanceDetector(_make_config(min_appearances=5))
        now = time.time()
        for i in range(4):
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now + i * 3600, "loc_a")
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(results, [])

    def test_identical_timestamps_no_division_by_zero(self):
        """All appearances at the same timestamp should not crash."""
        detector = SurveillanceDetector(_make_config())
        now = time.time()
        for _ in range(5):
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now, "loc_a")
        # Should return without error, no suspicious devices
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(results, [])

    def test_time_span_below_minimum_returns_zero(self):
        """Appearances within min_time_span_hours should not flag."""
        detector = SurveillanceDetector(
            _make_config(time_span_hours_min=2.0))
        now = time.time()
        # 3 appearances over 1 hour (below 2-hour minimum)
        for i in range(3):
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now + i * 1200, "loc_a")
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(results, [])

    def test_persistent_device_flagged(self):
        """Device appearing frequently over time should be flagged."""
        detector = SurveillanceDetector(_make_config())
        now = time.time()
        # 6 appearances over 2 hours = 3/hour rate
        for i in range(6):
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now + i * 1200, "loc_a")
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(len(results), 1)
        self.assertGreater(results[0].persistence_score, 0.5)

    def test_multi_location_bonus(self):
        """Device seen across locations should get a score boost."""
        detector = SurveillanceDetector(_make_config())
        now = time.time()
        # 3 at location A, 3 at location B, over 2 hours
        for i in range(3):
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now + i * 1200, "loc_a")
        for i in range(3):
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now + 3600 + i * 1200, "loc_b")

        results = detector.analyze_surveillance_patterns()
        self.assertEqual(len(results), 1)
        device = results[0]
        self.assertEqual(len(device.locations_seen), 2)
        # Multi-location bonus should push score higher
        self.assertGreater(device.persistence_score, 0.5)

    def test_score_capped_at_one(self):
        """Persistence score should never exceed 1.0."""
        detector = SurveillanceDetector(_make_config())
        now = time.time()
        # 100 appearances over 2 hours = extreme rate
        for i in range(100):
            loc = "loc_a" if i < 50 else "loc_b"
            detector.add_device_appearance(
                "AA:BB:CC:DD:EE:FF", now + i * 72, loc)
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(len(results), 1)
        self.assertLessEqual(results[0].persistence_score, 1.0)

    def test_low_appearance_rate_not_flagged(self):
        """Device with low appearance rate (< 0.5/hour) should not flag."""
        detector = SurveillanceDetector(_make_config())
        now = time.time()
        # 3 appearances over 24 hours = 0.125/hour
        detector.add_device_appearance(
            "AA:BB:CC:DD:EE:FF", now, "loc_a")
        detector.add_device_appearance(
            "AA:BB:CC:DD:EE:FF", now + 43200, "loc_a")
        detector.add_device_appearance(
            "AA:BB:CC:DD:EE:FF", now + 86400, "loc_a")
        results = detector.analyze_surveillance_patterns()
        self.assertEqual(results, [])

    def test_multiple_devices_sorted_by_score(self):
        """Results should be sorted by persistence score descending."""
        detector = SurveillanceDetector(_make_config())
        now = time.time()
        # Device A: moderate rate
        for i in range(4):
            detector.add_device_appearance(
                "AA:AA:AA:AA:AA:AA", now + i * 1800, "loc_a")
        # Device B: high rate + multi-location
        for i in range(10):
            loc = "loc_a" if i < 5 else "loc_b"
            detector.add_device_appearance(
                "BB:BB:BB:BB:BB:BB", now + i * 720, loc)
        results = detector.analyze_surveillance_patterns()
        if len(results) >= 2:
            self.assertGreaterEqual(
                results[0].persistence_score,
                results[1].persistence_score)


if __name__ == '__main__':
    unittest.main()
