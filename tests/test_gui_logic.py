import os
import sqlite3
import tempfile
import time
import unittest

from lib import gui_logic


class TestGuiLogic(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self._create_device_db(
            self.db_path,
            ("AA:AA:AA:AA:AA:AA", "Wi-Fi Client",
             '{"kismet.device.base.channel":"6","kismet.device.base.manuf":"TestCorp"}',
             time.time() - 30, None, None, -48),
        )

    def tearDown(self):
        os.unlink(self.db_path)

    def _create_device_db(self, path, *rows):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE devices (
                devmac TEXT,
                type TEXT,
                device TEXT,
                last_time REAL,
                min_lat REAL,
                min_lon REAL,
                strongest_signal INTEGER
            )
        """)
        for row in rows:
            cursor.execute("INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?)", row)
        conn.commit()
        conn.close()

    def test_get_dashboard_stats_marks_recent_db_active(self):
        stats = gui_logic.get_dashboard_stats(self.db_path, freshness_minutes=5)
        self.assertEqual(stats["db_status"], "CONNECTED")
        self.assertEqual(stats["device_count"], 1)
        self.assertEqual(stats["db_freshness"], "ACTIVE")
        self.assertIsNotNone(stats["db_age_minutes"])
        self.assertEqual(
            gui_logic.get_dashboard_health_summary(stats),
            "Telemetry Healthy",
        )
        self.assertEqual(
            gui_logic.get_dashboard_health_label(stats),
            "HEALTHY",
        )

    def test_get_dashboard_stats_marks_old_db_stale(self):
        old_mtime = time.time() - (15 * 60)
        os.utime(self.db_path, (old_mtime, old_mtime))

        stats = gui_logic.get_dashboard_stats(self.db_path, freshness_minutes=5)
        self.assertEqual(stats["db_status"], "CONNECTED")
        self.assertEqual(stats["db_freshness"], "STALE")
        self.assertGreaterEqual(stats["db_age_minutes"], 15)
        self.assertEqual(
            gui_logic.get_dashboard_health_summary(stats),
            "Telemetry Stale",
        )
        self.assertIn("15", gui_logic.get_dashboard_health_detail(stats))

    def test_get_live_device_feed_returns_recent_devices(self):
        devices = gui_logic.get_live_device_feed(self.db_path, time_window=120)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["mac"], "AA:AA:AA:AA:AA:AA")
        self.assertEqual(devices[0]["channel"], "6")
        self.assertEqual(devices[0]["manufacturer"], "TestCorp")

    def test_find_latest_db_path_returns_existing_db(self):
        latest, pattern = gui_logic.find_latest_db_path(self.db_path)
        self.assertEqual(latest, self.db_path)
        self.assertEqual(pattern, self.db_path)

    def test_find_latest_db_path_uses_fallback_when_glob_empty(self):
        missing_pattern = self.db_path + ".missing"
        latest, pattern = gui_logic.find_latest_db_path(
            missing_pattern, fallback_path=self.db_path)
        self.assertEqual(latest, self.db_path)
        self.assertEqual(pattern, missing_pattern)

    def test_dashboard_health_copy_for_missing_database(self):
        stats = gui_logic.get_dashboard_stats("NOT_FOUND", freshness_minutes=5)
        self.assertEqual(gui_logic.get_dashboard_health_summary(stats), "Telemetry Offline")
        self.assertEqual(gui_logic.get_dashboard_health_label(stats), "OFFLINE")
        self.assertIn("No active Kismet database", gui_logic.get_dashboard_health_detail(stats))

    def test_latest_db_selection_feeds_normalized_live_devices(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            older_db = os.path.join(temp_dir, "older.kismet")
            newer_db = os.path.join(temp_dir, "newer.kismet")
            now = time.time()

            self._create_device_db(
                older_db,
                ("11:11:11:11:11:11", "Wi-Fi Client",
                 '{"kismet.device.base.channel":"1","kismet.device.base.manuf":"OlderCorp"}',
                 now - 60, None, None, -70),
            )
            self._create_device_db(
                newer_db,
                ("22:22:22:22:22:22", "Wi-Fi AP",
                 '{"kismet.device.base.channel":"11","kismet.device.base.manuf":"NewerCorp"}',
                 now - 10, None, None, -42),
            )

            os.utime(older_db, (now - 120, now - 120))
            os.utime(newer_db, (now, now))

            latest, pattern = gui_logic.find_latest_db_path(temp_dir)
            self.assertEqual(latest, newer_db)
            self.assertTrue(pattern.endswith("*.kismet"))

            devices = gui_logic.get_live_device_feed(latest, time_window=120)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]["mac"], "22:22:22:22:22:22")
            self.assertEqual(devices[0]["channel"], "11")
            self.assertEqual(devices[0]["manufacturer"], "NewerCorp")
            self.assertEqual(devices[0]["type"], "Wi-Fi AP")
