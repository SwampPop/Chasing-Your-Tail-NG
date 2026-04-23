"""Kismet eventbus subscription client.

Subscribes to Kismet's `/eventbus/events.ws` websocket and dispatches each
server-pushed event to per-topic callbacks. The payoff vs REST polling is
sub-second alert latency — a DEAUTH flood fires the UI banner the moment
Kismet tags it, not up to ten seconds later.

Transport model:
    ws://host:port/eventbus/events.ws + HTTP Basic auth
    client → server : {"SUBSCRIBE": "<TOPIC>"} per topic
    server → client : {"<TOPIC>": {<payload>}} for each event

A dedicated receive thread owns the socket and calls back into the caller's
dispatch_fn on the dashboard's main thread indirectly (Flask-SocketIO emit
is thread-safe; DetectionLogger manages its own sqlite connections). Drops
trigger exponential-backoff reconnect so the client is resilient to Kismet
restarts, VM pauses, and the known Parallels bridge hiccup.

Not wired by default — watchdog_dashboard.py enables it via --eventbus.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
from typing import Callable, Iterable, Optional

try:
    import websocket  # websocket-client >=1.8
except ImportError:  # pragma: no cover — import guard
    websocket = None

logger = logging.getLogger(__name__)

# Topics worth subscribing to for Phase 1.
# ALERT covers DEAUTHFLOOD, DISASSOCFLOOD, APSPOOF, KARMA, BEACONRATE, etc.
# TIMESTAMP is a 1-Hz heartbeat — useful for liveness signaling.
DEFAULT_TOPICS = ("ALERT", "TIMESTAMP")

# Backoff schedule in seconds: 1, 2, 5, 10, 30, then stay at 30.
_BACKOFF_SEQUENCE = (1, 2, 5, 10, 30)


class KismetEventbusClient:
    """Thread-owning websocket subscription to Kismet's eventbus.

    Usage:
        client = KismetEventbusClient(
            "http://10.0.0.5:2501", "kismet", "password",
            dispatch_fn=lambda topic, payload: ...,
        )
        client.start()
        ...
        client.stop()

    start() returns immediately; a background thread owns the socket and
    calls dispatch_fn(topic, payload) for each event. dispatch_fn runs on
    the receive thread — keep it quick or hand off.
    """

    def __init__(
        self,
        kismet_url: str,
        username: str,
        password: str,
        dispatch_fn: Callable[[str, dict], None],
        topics: Iterable[str] = DEFAULT_TOPICS,
        connect_timeout: float = 5.0,
    ):
        if websocket is None:
            raise RuntimeError(
                "websocket-client not installed. "
                "Run: pip install 'websocket-client>=1.8'"
            )
        self.kismet_url = kismet_url.rstrip("/")
        self.username = username
        self.password = password
        self.dispatch_fn = dispatch_fn
        self.topics = tuple(topics)
        self.connect_timeout = connect_timeout

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._ws: Optional[websocket.WebSocket] = None
        self._lock = threading.Lock()
        self._last_event_ts: float = 0.0
        self._connected: bool = False

    # ---- Public API ----

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="kismet-eventbus", daemon=True,
        )
        self._thread.start()

    def stop(self, join_timeout: float = 5.0) -> None:
        self._stop.set()
        with self._lock:
            ws = self._ws
            self._ws = None
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=join_timeout)
            self._thread = None

    def is_connected(self) -> bool:
        return self._connected

    def last_event_ts(self) -> float:
        return self._last_event_ts

    # ---- Internal ----

    def _ws_url(self) -> str:
        """Transform http://host:port → ws://host:port/eventbus/events.ws.

        Kept tolerant of https:// too, just in case someone proxies Kismet
        behind TLS termination."""
        base = self.kismet_url
        if base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        return base + "/eventbus/events.ws"

    def _auth_header(self) -> list:
        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        return [f"Authorization: Basic {token}"]

    def _connect_once(self) -> "websocket.WebSocket":
        ws = websocket.create_connection(
            self._ws_url(),
            header=self._auth_header(),
            timeout=self.connect_timeout,
        )
        for topic in self.topics:
            ws.send(json.dumps({"SUBSCRIBE": topic}))
        return ws

    def _run(self) -> None:
        backoff_idx = 0
        while not self._stop.is_set():
            try:
                ws = self._connect_once()
                with self._lock:
                    self._ws = ws
                self._connected = True
                backoff_idx = 0
                logger.info("kismet eventbus connected: topics=%s",
                            ",".join(self.topics))
                self._receive_loop(ws)
            except Exception as e:
                logger.warning("kismet eventbus connect/recv failed: %s", e)
            finally:
                self._connected = False
                with self._lock:
                    ws = self._ws
                    self._ws = None
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass

            if self._stop.is_set():
                break

            wait = _BACKOFF_SEQUENCE[min(backoff_idx, len(_BACKOFF_SEQUENCE) - 1)]
            backoff_idx += 1
            logger.info("kismet eventbus reconnecting in %ss", wait)
            if self._stop.wait(timeout=wait):
                break

    def _receive_loop(self, ws: "websocket.WebSocket") -> None:
        while not self._stop.is_set():
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except (websocket.WebSocketConnectionClosedException, OSError):
                return
            if not raw:
                return
            try:
                msg = json.loads(raw)
            except (ValueError, TypeError):
                logger.debug("kismet eventbus: dropping non-json frame")
                continue
            if not isinstance(msg, dict):
                continue
            self._last_event_ts = time.time()
            for topic, payload in msg.items():
                try:
                    self.dispatch_fn(topic, payload)
                except Exception as e:  # never let a handler kill the socket
                    logger.exception("eventbus dispatch_fn failed on %s: %s",
                                     topic, e)
