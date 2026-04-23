"""Tests for kismet_eventbus.KismetEventbusClient.

Does NOT talk to a real Kismet. A fake WebSocket stub stands in for the
websocket-client `create_connection` return value, letting us verify the
subscribe payload, event dispatch, and reconnect-after-drop behavior
without networking.
"""
import json
import os
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import kismet_eventbus as eb  # noqa: E402


class FakeWebSocket:
    """Stands in for a connected websocket-client WebSocket."""

    def __init__(self, script):
        """script: iterable of strings/exceptions the client will receive
        on successive recv() calls. An exception type gets raised from recv()."""
        self._script = list(script)
        self.sent = []
        self._closed = False

    def send(self, data):
        self.sent.append(data)

    def recv(self):
        if self._closed:
            raise eb.websocket.WebSocketConnectionClosedException("closed")
        if not self._script:
            # Idle: block briefly so the client doesn't busy-loop, then
            # behave like the server dropped the socket.
            time.sleep(0.05)
            raise eb.websocket.WebSocketConnectionClosedException("eof")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        self._closed = True


class EventbusClientTest(unittest.TestCase):

    def setUp(self):
        self._connects = queue.Queue()
        self._connect_count = 0

    def _make_create_connection(self, scripts):
        """Return a fake create_connection(url, header=..., timeout=...).

        Each call consumes one script and returns a FakeWebSocket wired to it.
        Extra calls (e.g. reconnects) reuse the last script so the test can
        keep driving the loop."""
        def _fake(url, header=None, timeout=None):
            self._connect_count += 1
            script = scripts.pop(0) if scripts else []
            ws = FakeWebSocket(script)
            self._connects.put(ws)
            return ws
        return _fake

    def test_subscribes_to_topics_on_connect(self):
        events = []
        client = eb.KismetEventbusClient(
            "http://example:2501", "u", "p",
            dispatch_fn=lambda t, p: events.append((t, p)),
            topics=("ALERT", "TIMESTAMP"),
        )
        scripts = [[
            json.dumps({"TIMESTAMP": {"sec": 1}}),
            json.dumps({"ALERT": {"header": "DEAUTHFLOOD"}}),
        ]]
        with patch.object(eb.websocket, "create_connection",
                          side_effect=self._make_create_connection(scripts)):
            client.start()
            # Wait for both events, then shut down.
            deadline = time.time() + 2.0
            while len(events) < 2 and time.time() < deadline:
                time.sleep(0.02)
            client.stop(join_timeout=2.0)

        self.assertEqual(len(events), 2)
        topics_seen = [t for (t, _) in events]
        self.assertIn("TIMESTAMP", topics_seen)
        self.assertIn("ALERT", topics_seen)

        ws = self._connects.get_nowait()
        # Two SUBSCRIBE frames sent on connect.
        self.assertEqual(len(ws.sent), 2)
        parsed = [json.loads(f) for f in ws.sent]
        self.assertIn({"SUBSCRIBE": "ALERT"}, parsed)
        self.assertIn({"SUBSCRIBE": "TIMESTAMP"}, parsed)

    def test_dispatch_receives_structured_payload(self):
        captured = []
        client = eb.KismetEventbusClient(
            "http://example:2501", "u", "p",
            dispatch_fn=lambda t, p: captured.append((t, p)),
            topics=("ALERT",),
        )
        scripts = [[json.dumps({"ALERT": {"kismet.alert.header": "DEAUTHFLOOD",
                                          "kismet.alert.text": "mac AA:BB"}})]]
        with patch.object(eb.websocket, "create_connection",
                          side_effect=self._make_create_connection(scripts)):
            client.start()
            deadline = time.time() + 1.0
            while not captured and time.time() < deadline:
                time.sleep(0.02)
            client.stop(join_timeout=2.0)

        self.assertEqual(len(captured), 1)
        topic, payload = captured[0]
        self.assertEqual(topic, "ALERT")
        self.assertEqual(payload["kismet.alert.header"], "DEAUTHFLOOD")

    def test_reconnects_after_drop(self):
        """First script drops after one event → client reconnects → second
        script provides a second event → ensures stop() halts the loop."""
        captured = []
        client = eb.KismetEventbusClient(
            "http://example:2501", "u", "p",
            dispatch_fn=lambda t, p: captured.append(t),
            topics=("ALERT",),
        )
        scripts = [
            [json.dumps({"ALERT": {"seq": 1}})],   # then connection drops
            [json.dumps({"ALERT": {"seq": 2}})],   # after reconnect
        ]
        # Shrink backoff so the test doesn't sit around.
        with patch.object(eb, "_BACKOFF_SEQUENCE", (0.01,)), \
             patch.object(eb.websocket, "create_connection",
                          side_effect=self._make_create_connection(scripts)):
            client.start()
            deadline = time.time() + 3.0
            while len(captured) < 2 and time.time() < deadline:
                time.sleep(0.05)
            client.stop(join_timeout=2.0)

        self.assertGreaterEqual(self._connect_count, 2,
                                "client should have reconnected at least once")
        self.assertEqual(captured[:2], ["ALERT", "ALERT"])

    def test_stop_is_clean_even_without_start(self):
        client = eb.KismetEventbusClient(
            "http://example:2501", "u", "p",
            dispatch_fn=lambda t, p: None,
        )
        # Calling stop without start should not raise.
        client.stop(join_timeout=0.5)
        self.assertFalse(client.is_connected())

    def test_ws_url_rewrites_scheme(self):
        client = eb.KismetEventbusClient(
            "http://host:2501", "u", "p", dispatch_fn=lambda *a: None,
        )
        self.assertEqual(client._ws_url(), "ws://host:2501/eventbus/events.ws")
        client2 = eb.KismetEventbusClient(
            "https://proxy.example/", "u", "p", dispatch_fn=lambda *a: None,
        )
        self.assertEqual(client2._ws_url(),
                         "wss://proxy.example/eventbus/events.ws")

    def test_dispatch_exception_does_not_kill_socket(self):
        captured = []
        def bad_first_time(topic, payload):
            captured.append(topic)
            if len(captured) == 1:
                raise RuntimeError("handler explodes once")

        client = eb.KismetEventbusClient(
            "http://example:2501", "u", "p",
            dispatch_fn=bad_first_time, topics=("ALERT",),
        )
        scripts = [[
            json.dumps({"ALERT": {"seq": 1}}),
            json.dumps({"ALERT": {"seq": 2}}),
        ]]
        with patch.object(eb.websocket, "create_connection",
                          side_effect=self._make_create_connection(scripts)):
            client.start()
            deadline = time.time() + 1.5
            while len(captured) < 2 and time.time() < deadline:
                time.sleep(0.02)
            client.stop(join_timeout=2.0)

        self.assertEqual(len(captured), 2,
                         "second event must still be dispatched after a handler raise")


if __name__ == "__main__":
    unittest.main()
