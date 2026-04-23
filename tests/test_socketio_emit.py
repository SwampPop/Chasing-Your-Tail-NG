"""Tests for the SocketIO emit helpers in watchdog_dashboard.

These exercise the payload shape produced by _emit_system_status,
_emit_device_update, and on_attack_alert — not the network stack. We
monkey-patch watchdog_dashboard.socketio.emit to capture calls.
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import watchdog_dashboard as wd  # noqa: E402


class EmitHelpersTest(unittest.TestCase):

    def setUp(self):
        self._orig_emit = wd.socketio.emit
        self._captured = []
        wd.socketio.emit = lambda event, payload=None, **kw: self._captured.append(
            (event, payload))
        self._orig_stats = dict(wd.scan_stats)
        self._orig_attacks = list(wd.recent_attacks)
        self._orig_state = dict(wd._attack_emit_state)

    def tearDown(self):
        wd.socketio.emit = self._orig_emit
        wd.scan_stats.clear()
        wd.scan_stats.update(self._orig_stats)
        wd.recent_attacks[:] = self._orig_attacks
        wd._attack_emit_state.clear()
        wd._attack_emit_state.update(self._orig_state)

    def test_system_status_shape(self):
        wd.scan_stats.update({
            "operator_lat": 29.95, "operator_lon": -90.06,
            "coverage_area": "CBD", "nearby_alprs": 3,
            "last_update": "12:34:56", "scan_count": 7,
            "start_ts": time.time() - 10,
        })
        wd._emit_system_status(kismet_up=True)
        self.assertEqual(len(self._captured), 1)
        event, payload = self._captured[0]
        self.assertEqual(event, "system_status")
        for key in ("kismet_up", "gps_lock", "gps_lat", "gps_lon",
                    "coverage_area", "nearby_alprs", "last_update",
                    "scan_count", "uptime_s"):
            self.assertIn(key, payload)
        self.assertTrue(payload["kismet_up"])
        self.assertTrue(payload["gps_lock"])
        self.assertEqual(payload["coverage_area"], "CBD")

    def test_device_update_shape(self):
        wd.scan_stats.update({
            "total_devices": 50, "cameras": 2, "alprs": 1,
            "drones": 0, "trackers": 5,
        })
        wd._emit_device_update()
        event, payload = self._captured[-1]
        self.assertEqual(event, "device_update")
        self.assertEqual(payload["count_total"], 50)
        self.assertEqual(payload["count_clean"], 50 - (2 + 1 + 0 + 5))
        self.assertEqual(payload["by_type"], {
            "cameras": 2, "alpr": 1, "drones": 0, "ble_trackers": 5,
        })

    def test_attack_alert_persists_and_emits(self):
        with patch.object(wd.db_logger, "log_attack") as mock_log:
            wd.on_attack_alert({
                "mac": "AA:BB:CC:DD:EE:FF",
                "reason": "Device sending deauth frames!",
                "flags": ["DEAUTH_SOURCE:3", "STRONG_SIGNAL:-42dBm"],
                "signal": -42,
                "duration": 5.0,
                "locations": [],
            })
            mock_log.assert_called_once()
            persisted = mock_log.call_args[0][0]
            self.assertEqual(persisted["attack_type"], "DEAUTH")
            self.assertEqual(persisted["severity"], "critical")
            self.assertEqual(persisted["count"], 3)

        events = [c for c in self._captured if c[0] == "attack_alert"]
        self.assertEqual(len(events), 1)
        payload = events[0][1]
        self.assertEqual(payload["mac"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(payload["attack_type"], "DEAUTH")

        self.assertEqual(len(wd.recent_attacks), 1)
        self.assertEqual(wd.recent_attacks[0]["mac"], "AA:BB:CC:DD:EE:FF")
        self.assertIn("ts_human", wd.recent_attacks[0])

    def test_attack_alert_rate_limit_per_mac(self):
        """Burst of 5 alerts for same MAC → 1 emit; persistence unaffected."""
        wd._attack_emit_state.clear()
        with patch.object(wd.db_logger, "log_attack"):
            for _ in range(5):
                wd.on_attack_alert({
                    "mac": "11:22:33:44:55:66",
                    "reason": "flood",
                    "flags": ["DEAUTH_SOURCE:1"],
                    "signal": -40, "duration": 1.0, "locations": [],
                })
        emits = [c for c in self._captured if c[0] == "attack_alert"]
        self.assertEqual(len(emits), 1, "rate-limit should drop 4 of 5 emits")
        self.assertEqual(len(wd.recent_attacks), 5, "all alerts persisted")

    def test_soft_heuristics_persist_but_do_not_emit(self):
        """BRIEF/STRONG_GHOST/SUSPICIOUS are noise — logged to DB but no banner.

        Guards against the regression where every iPhone probe request tripped
        RANDOMIZED_MAC + BRIEF_APPEARANCE and flashed the attack banner.
        """
        cases = [
            # (flags, signal, expected_attack_type)
            (["RANDOMIZED_MAC", "BRIEF_APPEARANCE:26s"], -55, "BRIEF"),
            (["STRONG_SIGNAL:0dBm"], 0, "STRONG_GHOST"),
            (["RANDOMIZED_MAC"], -75, "SUSPICIOUS"),
        ]
        with patch.object(wd.db_logger, "log_attack") as mock_log:
            for flags, signal, expected_type in cases:
                wd.on_attack_alert({
                    "mac": "AA:AA:AA:00:00:01",
                    "reason": "probe-noise",
                    "flags": flags, "signal": signal,
                    "duration": 30.0, "locations": [],
                })
            self.assertEqual(mock_log.call_count, len(cases),
                             "every soft alert should persist to the DB")

        emits = [c for c in self._captured if c[0] == "attack_alert"]
        self.assertEqual(len(emits), 0,
                         "soft heuristics must not emit to the UI banner")
        self.assertEqual(len(wd.recent_attacks), 0,
                         "soft heuristics must not populate the Active Attacks panel")

    def test_real_attack_types_do_emit(self):
        """DEAUTH, DISASSOC, TARGETING still flash the banner."""
        wd._attack_emit_state.clear()
        with patch.object(wd.db_logger, "log_attack"):
            wd.on_attack_alert({
                "mac": "DE:AD:00:00:00:01", "reason": "deauth",
                "flags": ["DEAUTH_SOURCE:1"], "signal": -50,
                "duration": 1.0, "locations": [],
            })
            wd.on_attack_alert({
                "mac": "DE:AD:00:00:00:02", "reason": "targeting-ours",
                "flags": ["TARGETING_OUR_NETWORKS:myssid"], "signal": -60,
                "duration": 10.0, "locations": [],
            })
        emits = [c for c in self._captured if c[0] == "attack_alert"]
        self.assertEqual(len(emits), 2)
        types = {e[1]["attack_type"] for e in emits}
        self.assertEqual(types, {"DEAUTH", "TARGETING"})

    def test_eventbus_alert_maps_to_deauth(self):
        """A live Kismet ALERT event with DEAUTHFLOOD header drives on_attack_alert
        through the same path as the REST polling AttackerHunter callback."""
        with patch.object(wd.db_logger, "log_attack"):
            wd._handle_eventbus_message("ALERT", {
                "kismet.alert.header": "DEAUTHFLOOD",
                "kismet.alert.text": "Detected a deauth flood from 00:11:22:33:44:55",
                "kismet.alert.source": "",
            })
        emits = [c for c in self._captured if c[0] == "attack_alert"]
        self.assertEqual(len(emits), 1)
        payload = emits[0][1]
        self.assertEqual(payload["attack_type"], "DEAUTH")
        self.assertEqual(payload["severity"], "critical")
        self.assertEqual(payload["mac"], "00:11:22:33:44:55")

    def test_eventbus_timestamp_flips_kismet_status_live(self):
        wd.scan_stats["kismet_status"] = "connecting"
        wd._handle_eventbus_message("TIMESTAMP", {"sec": 1})
        self.assertEqual(wd.scan_stats["kismet_status"], "live")

    def test_classify_attack_variants(self):
        cases = [
            ({"flags": ["DEAUTH_SOURCE:7"], "signal": -60}, ("DEAUTH", "critical", 7)),
            ({"flags": ["TARGETING_OUR_NETWORKS:homewifi"], "signal": -55},
             ("TARGETING", "critical", 1)),
            ({"flags": ["BRIEF_APPEARANCE:45s", "STRONG_SIGNAL:-42dBm"],
              "signal": -42}, ("BRIEF", "high", 1)),
            ({"flags": ["STRONG_SIGNAL:-48dBm"], "signal": -48},
             ("STRONG_GHOST", "high", 1)),
            ({"flags": ["RANDOMIZED_MAC"], "signal": -75},
             ("SUSPICIOUS", "med", 1)),
        ]
        for alert_in, expected in cases:
            with self.subTest(alert=alert_in):
                self.assertEqual(wd._classify_attack(alert_in), expected)


if __name__ == "__main__":
    unittest.main()
