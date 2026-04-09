"""Tests for gps_tracker.py — GPS tracking, clustering, and KML export."""
import unittest
import os
import tempfile

from gps_tracker import GPSTracker, GPSLocation, KMLExporter


def _make_config(**gps_overrides):
    gps = {
        'location_threshold_meters': 100,
        'session_timeout_seconds': 600,
    }
    gps.update(gps_overrides)
    return {'gps_settings': gps}


class TestGPSTracker(unittest.TestCase):

    def test_no_gps_reading_returns_none_for_device(self):
        tracker = GPSTracker(_make_config())
        result = tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        self.assertIsNone(result)

    def test_add_reading_sets_current_location(self):
        tracker = GPSTracker(_make_config())
        loc_id = tracker.add_gps_reading(40.7128, -74.0060)
        self.assertIsNotNone(loc_id)
        self.assertIsNotNone(tracker.current_location)

    def test_device_added_to_current_session(self):
        tracker = GPSTracker(_make_config())
        tracker.add_gps_reading(40.7128, -74.0060)
        result = tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        self.assertIsNotNone(result)
        self.assertIn("AA:BB:CC:DD:EE:FF",
                       tracker.current_location.devices_seen)

    def test_duplicate_device_not_added_twice(self):
        tracker = GPSTracker(_make_config())
        tracker.add_gps_reading(40.7128, -74.0060)
        tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        self.assertEqual(
            tracker.current_location.devices_seen.count("AA:BB:CC:DD:EE:FF"),
            1)

    def test_identical_coordinates_zero_distance(self):
        tracker = GPSTracker(_make_config())
        loc = GPSLocation(latitude=40.7128, longitude=-74.0060)
        dist = tracker._calculate_distance(loc, loc)
        self.assertAlmostEqual(dist, 0.0, places=5)

    def test_known_distance_calculation(self):
        """NYC to Chicago is ~1145km."""
        tracker = GPSTracker(_make_config())
        nyc = GPSLocation(latitude=40.7128, longitude=-74.0060)
        chi = GPSLocation(latitude=41.8781, longitude=-87.6298)
        dist = tracker._calculate_distance(nyc, chi)
        self.assertAlmostEqual(dist, 1_145_000, delta=50_000)

    def test_nearby_readings_cluster_together(self):
        tracker = GPSTracker(
            _make_config(location_threshold_meters=200))
        id1 = tracker.add_gps_reading(40.7128, -74.0060)
        # ~50m away — should cluster
        id2 = tracker.add_gps_reading(40.7132, -74.0060)
        self.assertEqual(id1, id2)

    def test_distant_readings_create_separate_sessions(self):
        tracker = GPSTracker(
            _make_config(location_threshold_meters=100))
        id1 = tracker.add_gps_reading(40.7128, -74.0060)
        # ~1km away — should NOT cluster
        id2 = tracker.add_gps_reading(40.7228, -74.0060)
        self.assertNotEqual(id1, id2)

    def test_devices_across_locations_empty(self):
        tracker = GPSTracker(_make_config())
        result = tracker.get_devices_across_locations()
        self.assertEqual(result, {})

    def test_devices_across_locations_single_location(self):
        tracker = GPSTracker(_make_config())
        tracker.add_gps_reading(40.7128, -74.0060)
        tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        result = tracker.get_devices_across_locations()
        # Device at single location should NOT appear
        self.assertEqual(result, {})

    def test_devices_across_multiple_locations(self):
        tracker = GPSTracker(
            _make_config(location_threshold_meters=100))
        tracker.add_gps_reading(40.7128, -74.0060)
        tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        # Move to distant location
        tracker.add_gps_reading(41.8781, -87.6298)
        tracker.add_device_at_current_location("AA:BB:CC:DD:EE:FF")
        result = tracker.get_devices_across_locations()
        self.assertIn("AA:BB:CC:DD:EE:FF", result)
        self.assertEqual(len(result["AA:BB:CC:DD:EE:FF"]), 2)

    def test_named_location(self):
        tracker = GPSTracker(_make_config())
        loc_id = tracker.add_gps_reading(
            40.7128, -74.0060, location_name="French Quarter")
        self.assertEqual(loc_id, "French_Quarter")


class TestKMLExporter(unittest.TestCase):

    def test_fallback_template_when_missing(self):
        exporter = KMLExporter(template_path="/nonexistent/template.kml")
        self.assertTrue(exporter.using_fallback)
        self.assertIn("kml", exporter.kml_template)

    def test_valid_template_loads(self):
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'template.kml')
        if os.path.exists(template_path):
            exporter = KMLExporter(template_path=template_path)
            self.assertFalse(exporter.using_fallback)


if __name__ == '__main__':
    unittest.main()
