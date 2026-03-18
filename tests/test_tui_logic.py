import unittest
from collections import deque

from cyt_tui import CYTTerminalUI, DeviceRow
from lib.gui_logic import get_dashboard_health_label


class _BehavioralDetectorStub:
    def __init__(self, scores=None):
        self.scores = scores or {}

    def analyze_device(self, mac):
        return self.scores.get(mac, 0.0), {}


class _MonitorStub:
    def __init__(self):
        self.ignore_list = set()
        self.five_ten_min_ago_macs = set()
        self.ten_fifteen_min_ago_macs = set()
        self.fifteen_twenty_min_ago_macs = set()
        self.behavioral_detector = _BehavioralDetectorStub()
        self._drone_macs = set()

    def check_drone_threat(self, mac):
        return mac in self._drone_macs


class _DBStub:
    def __init__(self, devices):
        self.devices = devices

    def get_live_devices(self, time_window_seconds):
        return list(self.devices)


class TestCYTTUILogic(unittest.TestCase):
    def setUp(self):
        self.ui = CYTTerminalUI()
        self.ui.monitor = _MonitorStub()
        self.ui.config = {
            "behavioral_drone_detection": {
                "confidence_threshold": 0.6
            }
        }
        self.ui.alert_lines = deque(maxlen=50)

    def test_get_threat_level_prioritizes_drone_then_behavioral_then_persistent(self):
        self.ui.monitor._drone_macs.add("AA")
        self.assertEqual(self.ui._get_threat_level("AA", {}, None, 0.6), "drone")

        self.assertEqual(self.ui._get_threat_level("BB", {}, 0.8, 0.6), "behavioral")

        self.ui.monitor.five_ten_min_ago_macs.add("CC")
        self.ui.monitor.ten_fifteen_min_ago_macs.add("CC")
        self.ui.monitor.fifteen_twenty_min_ago_macs.add("CC")
        self.assertEqual(self.ui._get_threat_level("CC", {}, None, 0.6), "persistent")

    def test_apply_filters_sorts_by_threat_then_signal(self):
        rows = [
            DeviceRow(mac="1", signal=-70, threat="", dev_type="Wi-Fi Client"),
            DeviceRow(mac="2", signal=-80, threat="persistent", dev_type="Wi-Fi Client"),
            DeviceRow(mac="3", signal=-50, threat="drone", dev_type="Wi-Fi Client"),
            DeviceRow(mac="4", signal=-40, threat="behavioral", dev_type="Wi-Fi Client"),
        ]
        self.ui.filter_mode = "all"
        self.ui.sort_mode = "threat"
        filtered = self.ui._apply_filters(rows)
        self.assertEqual([r.mac for r in filtered], ["3", "4", "2", "1"])

    def test_apply_filters_supports_signal_top_and_device_categories(self):
        rows = [
            DeviceRow(mac="ap1", signal=-80, threat="", dev_type="Wi-Fi AP"),
            DeviceRow(mac="cli1", signal=-40, threat="", dev_type="Wi-Fi Client"),
            DeviceRow(mac="cli2", signal=-60, threat="", dev_type="Station"),
        ]

        self.ui.filter_mode = "signal_top"
        self.ui.top_n_limit = 2
        top_rows = self.ui._apply_filters(list(rows))
        self.assertEqual([r.mac for r in top_rows], ["cli1", "cli2"])

        self.ui.filter_mode = "ap"
        self.ui.sort_mode = "signal"
        ap_rows = self.ui._apply_filters(list(rows))
        self.assertEqual([r.mac for r in ap_rows], ["ap1"])

        self.ui.filter_mode = "client"
        client_rows = self.ui._apply_filters(list(rows))
        self.assertEqual([r.mac for r in client_rows], ["cli1", "cli2"])

    def test_filter_cycle_and_alert_counts(self):
        seen = []
        for _ in range(5):
            seen.append(self.ui.filter_mode)
            self.ui._cycle_filter_mode()
        self.assertEqual(seen, ["all", "threats", "signal_top", "ap", "client"])
        self.assertEqual(self.ui.filter_mode, "all")

        self.ui.alert_lines.extend([
            "[12:00:00] CRIT: A",
            "[12:00:01] WARN: B",
            "[12:00:02] INFO: C",
            "[12:00:03] something else",
        ])
        counts = self.ui._count_alert_levels()
        self.assertEqual(counts, {"CRIT": 1, "WARN": 1, "INFO": 2})

    def test_db_freshness_formatting(self):
        self.ui.dashboard_stats = {"db_freshness": "ACTIVE", "db_age_minutes": 2}
        self.assertEqual(self.ui._format_db_freshness(), "ACTIVE (2 min)")

        self.ui.dashboard_stats = {"db_freshness": "UNKNOWN", "db_age_minutes": None}
        self.assertEqual(self.ui._format_db_freshness(), "UNKNOWN")

    def test_db_status_attr_mapping(self):
        self.assertEqual(
            self.ui._db_status_style("CONNECTED", "ACTIVE"),
            "healthy",
        )
        self.assertEqual(
            self.ui._db_status_style("CONNECTED", "STALE"),
            "warning",
        )
        self.assertEqual(
            self.ui._db_status_style("DISCONNECTED", "ERROR"),
            "error",
        )
        self.assertEqual(
            get_dashboard_health_label({"db_status": "CONNECTED", "db_freshness": "ACTIVE"}),
            "HEALTHY",
        )
        self.assertEqual(
            get_dashboard_health_label({"db_status": "CONNECTED", "db_freshness": "STALE"}),
            "STALE",
        )
        self.assertEqual(
            get_dashboard_health_label({"db_status": "DISCONNECTED", "db_freshness": "UNKNOWN"}),
            "OFFLINE",
        )

    def test_stale_db_maps_to_warning_style(self):
        self.ui.dashboard_stats = {
            "db_status": "CONNECTED",
            "db_freshness": "STALE",
            "db_age_minutes": 12,
        }
        self.assertEqual(self.ui._format_db_freshness(), "STALE (12 min)")
        self.assertEqual(
            self.ui._db_status_style(
                self.ui.dashboard_stats["db_status"],
                self.ui.dashboard_stats["db_freshness"],
            ),
            "warning",
        )

    def test_db_status_style_differs_by_health(self):
        self.assertNotEqual(
            self.ui._db_status_style("CONNECTED", "ACTIVE"),
            self.ui._db_status_style("DISCONNECTED", "ERROR"),
        )
        self.assertNotEqual(
            self.ui._db_status_style("CONNECTED", "STALE"),
            self.ui._db_status_style("CONNECTED", "ACTIVE"),
        )

    def test_alerts_header_text_surfaces_telemetry_problems(self):
        self.ui.dashboard_stats = {
            "db_status": "CONNECTED",
            "db_freshness": "ACTIVE",
        }
        self.assertEqual(self.ui._alerts_header_text(), "=== RECENT ALERTS ===")

        self.ui.dashboard_stats = {
            "db_status": "CONNECTED",
            "db_freshness": "STALE",
        }
        self.assertIn("TELEMETRY STALE", self.ui._alerts_header_text())

        self.ui.dashboard_stats = {
            "db_status": "DISCONNECTED",
            "db_freshness": "UNKNOWN",
        }
        self.assertIn("TELEMETRY OFFLINE", self.ui._alerts_header_text())

    def test_fetch_device_list_uses_live_feed_records_and_tracks_behavioral_hits(self):
        self.ui.monitor.behavioral_detector = _BehavioralDetectorStub({
            "AA:AA:AA:AA:AA:AA": 0.9,
            "BB:BB:BB:BB:BB:BB": 0.2,
        })
        devices = [
            {
                "mac": "AA:AA:AA:AA:AA:AA",
                "signal": -45,
                "channel": "6",
                "type": "Wi-Fi Client",
                "manufacturer": "TestCorp",
                "last_seen": 1_700_000_000,
                "device_data": {},
            },
            {
                "mac": "BB:BB:BB:BB:BB:BB",
                "signal": -65,
                "channel": "11",
                "type": "Wi-Fi AP",
                "manufacturer": "VendorName",
                "last_seen": 1_700_000_100,
                "device_data": {},
            },
        ]

        rows = self.ui._fetch_device_list(_DBStub(devices))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].mac, "AA:AA:AA:AA:AA:AA")
        self.assertEqual(rows[0].threat, "behavioral")
        self.assertIn("AA:AA:AA:AA:AA:AA", self.ui.behavioral_threats)


if __name__ == "__main__":
    unittest.main()
