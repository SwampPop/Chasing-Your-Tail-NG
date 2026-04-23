"""End-to-end-ish test: a synthetic Kismet deauth alert flows through
AttackerHunter's alert_callback into on_attack_alert and lands in the
watchdog_live.db attacks table.

Uses a temp DB so it doesn't touch the operator's live file.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from attacker_hunter import CONFIG as ATTACKER_CONFIG, AttackerHunter, DeviceTracking  # noqa: E402
from watchdog_reporter import DetectionLogger  # noqa: E402
import watchdog_dashboard as wd  # noqa: E402


class AttackerIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.tmp.close()
        self.db = DetectionLogger(db_path=self.tmp.name)

        self._orig_db = wd.db_logger
        self._orig_emit = wd.socketio.emit
        self._orig_attacks = list(wd.recent_attacks)
        self._orig_state = dict(wd._attack_emit_state)
        wd.db_logger = self.db
        self._captured = []
        wd.socketio.emit = lambda event, payload=None, **kw: self._captured.append(
            (event, payload))
        wd.recent_attacks.clear()
        wd._attack_emit_state.clear()

    def tearDown(self):
        wd.db_logger = self._orig_db
        wd.socketio.emit = self._orig_emit
        wd.recent_attacks[:] = self._orig_attacks
        wd._attack_emit_state.clear()
        wd._attack_emit_state.update(self._orig_state)
        os.unlink(self.tmp.name)

    def test_deauth_alert_callback_writes_to_attacks_table(self):
        """Drive AttackerHunter with a synthetic DEAUTH Kismet alert and
        verify on_attack_alert persists one row."""
        hunter = AttackerHunter(dict(ATTACKER_CONFIG), alert_callback=wd.on_attack_alert)
        hunter.config["alert_sound"] = False

        mac = "DE:AD:BE:EF:00:01"
        tracking = DeviceTracking(
            mac=mac, first_seen=datetime.now(), last_seen=datetime.now()
        )
        tracking.signals.append(-40)
        hunter.devices[mac] = tracking

        synthetic_alerts = [{
            "kismet.alert.header": "DEAUTHFLOOD",
            "kismet.alert.text": f"Device {mac} sent deauth flood",
        }]

        with patch.object(hunter, "save_data"), patch.object(hunter, "log"):
            hunter.process_kismet_alerts(synthetic_alerts)

        rows = self.db.get_recent_attacks()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["mac"], mac)
        self.assertEqual(row["attack_type"], "DEAUTH")
        self.assertEqual(row["severity"], "critical")
        self.assertGreaterEqual(row["count"], 1)

        emits = [c for c in self._captured if c[0] == "attack_alert"]
        self.assertEqual(len(emits), 1)
        self.assertEqual(emits[0][1]["mac"], mac)

    def test_log_attack_schema_roundtrip(self):
        """Direct write via DetectionLogger.log_attack matches the row shape
        on_attack_alert produces. Guards against schema drift."""
        self.db.log_attack({
            "ts": 1700000000.0,
            "mac": "AA:AA:AA:AA:AA:AA",
            "attack_type": "DEAUTH",
            "severity": "critical",
            "reason": "test",
            "signal": -55,
            "count": 4,
            "evidence": {"flags": ["DEAUTH_SOURCE:4"]},
        })
        rows = self.db.get_recent_attacks()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        for col in ("ts", "mac", "attack_type", "severity", "reason",
                    "signal", "count", "evidence"):
            self.assertIn(col, row)
        self.assertEqual(row["count"], 4)


if __name__ == "__main__":
    unittest.main()
