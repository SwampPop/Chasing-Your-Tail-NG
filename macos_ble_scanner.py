#!/usr/bin/env python3
"""
Mac-native BLE scanner — feeds BLETrackerDetector from the Mac's built-in
Bluetooth radio via bleak/CoreBluetooth. No USB dongle required.

Completes the `bleak` half of ble_tracker_detector.py (its docstring advertises
both Kismet-sourced and bleak-sourced BLE input; the Kismet half is wired in
watchdog_dashboard.py but starves when the Kali VM has no BT passthrough).

Design notes:
- bleak.BleakScanner requires its own asyncio event loop. Flask-SocketIO's
  eventlet/gevent loop is not compatible. We run the scanner in a dedicated
  daemon thread with a fresh loop (asyncio.new_event_loop).
- Detector writes from this thread are serialized with the shared Lock the
  Flask HTTP path also acquires, so concurrent Kismet + host-BLE input is
  safe if BT passthrough is ever added to the Kali VM.
- On macOS, bleak returns the device.address as a per-host stable UUID (not
  the true BLE MAC). Apple hides the MAC at the OS level. The UUID is stable
  per-(host, peripheral) which is sufficient for persistence/following
  detection, but will not match OUI lookups or Kismet's `kismet.device.base.macaddr`
  for the same peripheral. Treat these as different entities for now.
- GPS is sourced by calling watchdog_dashboard.fetch_kismet_gps() — reuses the
  u-blox → gpsd → Kismet chain already running in the Kali VM. Result is
  cached briefly to avoid hammering the Kismet REST API on every advert.
- First run triggers the macOS TCC Bluetooth prompt for python3/Terminal.
  Grant it once; after that, no UI.

References:
- flock-radar/scripts/ble_scan_mac.py — validator that proved the radio works
- ble_tracker_detector.py — consumer
- watchdog_dashboard.py:243 fetch_kismet_gps — GPS source
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Callable, Optional, Tuple

try:
    from bleak import BleakScanner
except ImportError as e:
    raise ImportError(
        "bleak is required for macOS BLE scanning. "
        "Install with: pip3 install 'bleak>=0.22'"
    ) from e

logger = logging.getLogger(__name__)


GpsFetcher = Callable[[], Tuple[Optional[float], Optional[float]]]


class MacOSBLEScanner:
    """Feeds BLE advertisements from the Mac's built-in radio into a
    BLETrackerDetector."""

    def __init__(
        self,
        ble_detector,
        detector_lock: threading.Lock,
        gps_fetcher: Optional[GpsFetcher] = None,
        gps_cache_seconds: float = 2.0,
    ):
        """
        Args:
            ble_detector: Shared BLETrackerDetector instance.
            detector_lock: Lock guarding all writes to ble_detector. The
                Flask/HTTP scan loop in watchdog_dashboard.py must acquire
                the same lock before calling ble_detector.process_ble_advertisement().
            gps_fetcher: Zero-arg callable returning (lat, lon) or (None, None).
                Typically a partial over watchdog_dashboard.fetch_kismet_gps.
                If None, observations are emitted with lat=0, lon=0.
            gps_cache_seconds: Minimum seconds between GPS fetch calls.
        """
        self._detector = ble_detector
        self._lock = detector_lock
        self._gps_fetcher = gps_fetcher
        self._gps_cache_seconds = max(0.0, float(gps_cache_seconds))

        self._gps_cache: Tuple[Optional[float], Optional[float]] = (None, None)
        self._gps_cache_ts: float = 0.0
        self._gps_cache_lock = threading.Lock()

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._started = threading.Event()

    def start(self) -> None:
        """Start the scanner in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("MacOSBLEScanner.start() called but already running")
            return

        self._thread = threading.Thread(
            target=self._run_in_new_loop,
            name="MacOSBLEScanner",
            daemon=True,
        )
        self._thread.start()
        self._started.wait(timeout=5.0)
        logger.info("MacOSBLEScanner started")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the scanner to stop and wait for the thread to exit."""
        if not self._thread or not self._thread.is_alive():
            return

        loop = self._loop
        stop_event = self._stop_event
        if loop is not None and stop_event is not None:
            loop.call_soon_threadsafe(stop_event.set)

        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning("MacOSBLEScanner thread did not exit within %.1fs", timeout)
        else:
            logger.info("MacOSBLEScanner stopped")

    def _run_in_new_loop(self) -> None:
        """Thread entry point — creates a fresh asyncio loop and runs the scanner."""
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        self._stop_event = asyncio.Event()
        self._started.set()
        try:
            loop.run_until_complete(self._scan_until_stopped())
        except Exception as e:
            logger.exception("MacOSBLEScanner crashed: %s", e)
        finally:
            try:
                loop.close()
            except Exception:
                pass
            self._loop = None

    async def _scan_until_stopped(self) -> None:
        """Start BleakScanner and wait for stop_event."""
        scanner = BleakScanner(detection_callback=self._on_advertisement)
        try:
            await scanner.start()
        except Exception as e:
            logger.error(
                "BleakScanner.start() failed — ensure macOS has granted Bluetooth "
                "permission to this process (System Settings → Privacy & Security "
                "→ Bluetooth): %s", e
            )
            return

        try:
            await self._stop_event.wait()
        finally:
            try:
                await scanner.stop()
            except Exception as e:
                logger.debug("BleakScanner.stop() raised: %s", e)

    def _on_advertisement(self, device, adv) -> None:
        """Per-advertisement callback — called from the asyncio loop thread."""
        try:
            mac = device.address  # On macOS this is a stable per-host UUID, not a MAC.
            name = adv.local_name or ""
            rssi = adv.rssi if adv.rssi is not None else -100

            mfr_items = list(adv.manufacturer_data.items()) if adv.manufacturer_data else []
            if mfr_items:
                company_id, mfr_bytes = mfr_items[0]
            else:
                company_id, mfr_bytes = 0, None

            service_uuids = list(adv.service_uuids or [])

            lat, lon = self._get_gps()

            with self._lock:
                detection = self._detector.process_ble_advertisement(
                    mac=mac,
                    name=name,
                    company_id=company_id,
                    service_uuids=service_uuids,
                    rssi=rssi,
                    manufacturer_data=bytes(mfr_bytes) if mfr_bytes else None,
                    latitude=lat if lat is not None else 0.0,
                    longitude=lon if lon is not None else 0.0,
                )

            if detection is not None:
                logger.debug(
                    "host-BLE hit: %s mac=%s rssi=%d name=%r",
                    detection.tracker_type, mac, rssi, name,
                )
        except Exception as e:
            logger.exception("MacOSBLEScanner callback failed: %s", e)

    def _get_gps(self) -> Tuple[Optional[float], Optional[float]]:
        """Return cached or freshly-fetched (lat, lon)."""
        if self._gps_fetcher is None:
            return None, None

        now = time.time()
        with self._gps_cache_lock:
            if now - self._gps_cache_ts < self._gps_cache_seconds:
                return self._gps_cache

        try:
            lat, lon = self._gps_fetcher()
        except Exception as e:
            logger.debug("GPS fetcher raised: %s", e)
            lat, lon = None, None

        with self._gps_cache_lock:
            self._gps_cache = (lat, lon)
            self._gps_cache_ts = now
        return lat, lon


def build_kismet_gps_fetcher(kismet_url: str, username: str, password: str) -> GpsFetcher:
    """Return a zero-arg GPS fetcher bound to watchdog_dashboard.fetch_kismet_gps."""
    from watchdog_dashboard import fetch_kismet_gps

    def _fetch() -> Tuple[Optional[float], Optional[float]]:
        return fetch_kismet_gps(kismet_url, username, password)

    return _fetch
