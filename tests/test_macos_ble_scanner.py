"""Tests for macos_ble_scanner.py — callback logic, GPS caching, thread safety.

Does NOT exercise the real CoreBluetooth radio. bleak's BleakScanner is not
started; we call _on_advertisement() directly with mock objects shaped like
bleak.BLEDevice and bleak.AdvertisementData.
"""
import os
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

# Ensure project root on path (tests/ is a sibling of the module).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ble_tracker_detector import BLETrackerDetector  # noqa: E402

try:
    from macos_ble_scanner import MacOSBLEScanner  # noqa: E402
except ImportError:
    # bleak may not be installed in every test environment.
    MacOSBLEScanner = None


def _make_adv(local_name="", rssi=-60, manufacturer_data=None, service_uuids=None):
    """Build a mock object shaped like bleak.AdvertisementData."""
    return SimpleNamespace(
        local_name=local_name,
        rssi=rssi,
        manufacturer_data=manufacturer_data or {},
        service_uuids=service_uuids or [],
    )


def _make_device(address):
    """Build a mock object shaped like bleak.BLEDevice."""
    return SimpleNamespace(address=address)


@unittest.skipIf(MacOSBLEScanner is None, "bleak not installed")
class TestAdvertisementCallback(unittest.TestCase):

    def setUp(self):
        self.detector = BLETrackerDetector()
        self.lock = threading.Lock()

    def test_apple_findmy_ad_classifies_as_apple_findmy(self):
        scanner = MacOSBLEScanner(self.detector, self.lock, gps_fetcher=None)
        # Apple company ID 0x004C, manufacturer data starting with 0x12 (Find My type)
        adv = _make_adv(
            manufacturer_data={0x004C: bytes([0x12, 0x19, 0x00, 0x00])},
            rssi=-55,
        )
        device = _make_device("AA-BB-CC-DD-EE-FF")
        scanner._on_advertisement(device, adv)

        self.assertIn("AA-BB-CC-DD-EE-FF", self.detector.trackers)
        tracker = self.detector.trackers["AA-BB-CC-DD-EE-FF"]
        self.assertEqual(tracker.tracker_type, "apple_findmy")
        self.assertEqual(tracker.rssi, -55)

    def test_tile_ad_classifies_by_name_pattern(self):
        scanner = MacOSBLEScanner(self.detector, self.lock, gps_fetcher=None)
        adv = _make_adv(local_name="Tile", rssi=-70)
        device = _make_device("11-22-33-44-55-66")
        scanner._on_advertisement(device, adv)

        tracker = self.detector.trackers.get("11-22-33-44-55-66")
        self.assertIsNotNone(tracker)
        self.assertEqual(tracker.tracker_type, "tile")

    def test_non_tracker_ad_ignored(self):
        scanner = MacOSBLEScanner(self.detector, self.lock, gps_fetcher=None)
        # Random non-matching manufacturer data (DREO device from field test)
        adv = _make_adv(
            local_name="DREOsh09w38",
            manufacturer_data={0x4648: b"\x01\x02\x03"},
            rssi=-80,
        )
        device = _make_device("AA-BB-CC-DD-EE-FF")
        scanner._on_advertisement(device, adv)
        self.assertEqual(len(self.detector.trackers), 0)

    def test_gps_fetcher_populates_location(self):
        calls = []

        def fake_gps():
            calls.append(time.time())
            return 30.1234, -90.5678

        scanner = MacOSBLEScanner(
            self.detector, self.lock,
            gps_fetcher=fake_gps, gps_cache_seconds=0.0,
        )
        adv = _make_adv(
            manufacturer_data={0x004C: bytes([0x12, 0x19, 0x00, 0x00])},
            rssi=-55,
        )
        device = _make_device("AA-BB-CC-DD-EE-FF")
        scanner._on_advertisement(device, adv)

        tracker = self.detector.trackers["AA-BB-CC-DD-EE-FF"]
        self.assertEqual(tracker.locations, [(30.1234, -90.5678)])
        self.assertEqual(len(calls), 1)

    def test_gps_cache_prevents_hammering(self):
        calls = []

        def fake_gps():
            calls.append(time.time())
            return 30.0, -90.0

        scanner = MacOSBLEScanner(
            self.detector, self.lock,
            gps_fetcher=fake_gps, gps_cache_seconds=5.0,
        )
        adv = _make_adv(
            manufacturer_data={0x004C: bytes([0x12, 0x00])},
            rssi=-55,
        )
        for i in range(10):
            scanner._on_advertisement(_make_device(f"AA-{i:02d}"), adv)

        # 10 callbacks within 5-second cache window → exactly 1 GPS fetch
        self.assertEqual(len(calls), 1)

    def test_gps_fetcher_exception_falls_back_to_zero(self):
        def raising_gps():
            raise RuntimeError("Kismet unreachable")

        scanner = MacOSBLEScanner(
            self.detector, self.lock,
            gps_fetcher=raising_gps, gps_cache_seconds=0.0,
        )
        adv = _make_adv(
            manufacturer_data={0x004C: bytes([0x12, 0x00])},
            rssi=-55,
        )
        device = _make_device("AA-BB-CC-DD-EE-FF")
        scanner._on_advertisement(device, adv)  # must not raise

        # Tracker still registered, just without location
        self.assertIn("AA-BB-CC-DD-EE-FF", self.detector.trackers)
        self.assertEqual(self.detector.trackers["AA-BB-CC-DD-EE-FF"].locations, [])

    def test_detector_lock_is_held_during_write(self):
        """Callback must acquire the shared lock before touching the detector."""
        lock = threading.Lock()
        scanner = MacOSBLEScanner(self.detector, lock, gps_fetcher=None)

        # Hold the lock on another thread; callback must block until released.
        release = threading.Event()
        acquired_signal = threading.Event()

        def hold():
            with lock:
                acquired_signal.set()
                release.wait(timeout=2.0)

        holder = threading.Thread(target=hold, daemon=True)
        holder.start()
        self.assertTrue(acquired_signal.wait(timeout=1.0))

        callback_done = threading.Event()

        def invoke():
            adv = _make_adv(
                manufacturer_data={0x004C: bytes([0x12, 0x00])}, rssi=-55,
            )
            scanner._on_advertisement(_make_device("AA"), adv)
            callback_done.set()

        invoker = threading.Thread(target=invoke, daemon=True)
        invoker.start()

        # Give the invoker a chance to race — it must still be blocked on the lock.
        time.sleep(0.1)
        self.assertFalse(callback_done.is_set(),
                         "callback did not wait on the shared lock")

        release.set()
        holder.join(timeout=1.0)
        invoker.join(timeout=1.0)
        self.assertTrue(callback_done.is_set())


@unittest.skipIf(MacOSBLEScanner is None, "bleak not installed")
class TestWatchdogDashboardDrain(unittest.TestCase):
    """Validate that host-BLE detections reach the dashboard's UI structures.

    Covers the gap where the scanner updated ble_detector.trackers but the
    dashboard's `detections` / `scan_stats['trackers']` never saw them.
    """

    def setUp(self):
        import watchdog_dashboard as wd
        self.wd = wd
        # Reset module-level state
        wd.ble_detector.clear()
        wd.recent_detections = []
        wd.all_devices = []
        wd.scan_stats.update({
            'total_devices': 0, 'cameras': 0, 'alprs': 0, 'drones': 0,
            'trackers': 0, 'last_update': '', 'kismet_status': 'connecting',
        })

    def _inject_tracker(self, mac="AA-BB-CC", subtype=0x12):
        scanner = MacOSBLEScanner(
            self.wd.ble_detector, self.wd.ble_detector_lock, gps_fetcher=None,
        )
        adv = _make_adv(
            manufacturer_data={0x004C: bytes([subtype, 0x19, 0x00, 0x00])},
            rssi=-55,
        )
        scanner._on_advertisement(_make_device(mac), adv)

    def test_process_devices_drains_host_ble_trackers(self):
        self._inject_tracker(mac="HOST-TRACKER-1")
        self.wd.process_devices([])  # Kismet returned no devices this cycle
        macs = {d.mac for d in self.wd.recent_detections}
        self.assertIn("HOST-TRACKER-1", macs)
        self.assertEqual(self.wd.scan_stats['trackers'], 1)

    def test_drain_dedups_against_kismet_ble(self):
        """If the same MAC is reported by both Kismet and the host scanner,
        the dashboard should show it once, not twice."""
        # 1. Host scanner finds the tracker
        self._inject_tracker(mac="SHARED-MAC")
        # 2. Kismet also sees the same MAC as a BTLE device
        kismet_dev = {
            'kismet.device.base.macaddr': 'SHARED-MAC',
            'kismet.device.base.name': '',
            'kismet.device.base.manuf': 'Apple',
            'kismet.device.base.signal': {'kismet.common.signal.last_signal': -60},
            'kismet.device.base.channel': '37',
            'kismet.device.base.type': 'BTLE Device',
            'kismet.device.base.phyname': 'BTLE',
        }
        self.wd.process_devices([kismet_dev])
        macs = [d.mac for d in self.wd.recent_detections]
        self.assertEqual(macs.count("SHARED-MAC"), 1)

    def test_drain_only_path_when_kismet_down(self):
        self._inject_tracker(mac="HOST-ONLY-1")
        self._inject_tracker(mac="HOST-ONLY-2")
        self.wd._drain_host_ble_only()
        macs = {d.mac for d in self.wd.recent_detections}
        self.assertEqual(macs, {"HOST-ONLY-1", "HOST-ONLY-2"})
        self.assertEqual(self.wd.scan_stats['trackers'], 2)
        self.assertEqual(self.wd.scan_stats['kismet_status'], 'disconnected')


@unittest.skipIf(MacOSBLEScanner is None, "bleak not installed")
class TestBLEPersistence(unittest.TestCase):
    """Validate that host-BLE tracker detections are written to watchdog_live.db."""

    def setUp(self):
        import tempfile
        import watchdog_dashboard as wd
        from watchdog_reporter import DetectionLogger
        self.wd = wd
        # Point db_logger at an isolated temp DB
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp_db.close()
        self._original_logger = wd.db_logger
        wd.db_logger = DetectionLogger(db_path=self.tmp_db.name)
        wd.ble_detector.clear()
        wd.recent_detections = []

    def tearDown(self):
        import os
        self.wd.db_logger = self._original_logger
        try:
            os.unlink(self.tmp_db.name)
        except OSError:
            pass

    def _inject_tracker(self, mac):
        scanner = MacOSBLEScanner(
            self.wd.ble_detector, self.wd.ble_detector_lock, gps_fetcher=None,
        )
        adv = _make_adv(
            manufacturer_data={0x004C: bytes([0x12, 0x19, 0x00, 0x00])},
            rssi=-55,
        )
        scanner._on_advertisement(_make_device(mac), adv)

    def _db_rows(self):
        import sqlite3
        conn = sqlite3.connect(self.tmp_db.name)
        conn.row_factory = sqlite3.Row
        rows = list(conn.execute("SELECT * FROM detections"))
        conn.close()
        return rows

    def test_persisted_on_kismet_down_drain(self):
        self._inject_tracker(mac="PERSIST-1")
        self.wd._drain_host_ble_only()
        rows = self._db_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['mac'], "PERSIST-1")
        self.assertEqual(row['device_type'], 'tracker')
        self.assertEqual(row['manufacturer'],
                         'Apple Find My (AirTag/AirPods/FindMy accessory)')
        self.assertEqual(row['detection_method'], 'ble_signature')

    def test_persisted_on_process_devices_drain(self):
        self._inject_tracker(mac="PERSIST-2")
        self.wd.process_devices([])
        rows = self._db_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['mac'], "PERSIST-2")

    def test_repeat_drain_upserts_not_duplicates(self):
        self._inject_tracker(mac="REPEAT")
        self.wd.process_devices([])
        self.wd.process_devices([])
        self.wd.process_devices([])
        rows = self._db_rows()
        self.assertEqual(len(rows), 1)
        # seen_count grows via DetectionLogger's UPDATE path
        self.assertGreaterEqual(rows[0]['seen_count'], 3)


if __name__ == '__main__':
    unittest.main()
