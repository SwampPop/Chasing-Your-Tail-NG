#!/usr/bin/env python3
"""
WATCHDOG Live Dashboard — Real-time surveillance device detection.

Pulls live device data from Kismet's REST API, runs WATCHDOG detection
(camera OUI, SSID, drone, ALPR), and serves an interactive web dashboard.

Usage:
    python3 watchdog_dashboard.py --kismet-url http://kali-ip:2501 --port 5002

Requires Kismet running with API access.
"""
import argparse
import json
import logging
import os
import threading
import time
from datetime import datetime
from types import SimpleNamespace

import requests
from flask import Flask, render_template_string
from flask_socketio import SocketIO

from alpr_context import ALPRContext
from ble_tracker_detector import BLETrackerDetector
from camera_detector import CameraDetector
from drone_signature_matcher import get_matcher as get_drone_matcher
from watchdog_reporter import DetectionLogger

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
detector = CameraDetector()
drone_matcher = get_drone_matcher()
ble_detector = BLETrackerDetector()
alpr_ctx = ALPRContext()
db_logger = DetectionLogger(db_path="watchdog_live.db")
scan_stats = {
    "total_devices": 0,
    "cameras": 0,
    "alprs": 0,
    "drones": 0,
    "trackers": 0,
    "operator_lat": None,
    "operator_lon": None,
    "coverage_area": None,
    "nearby_alprs": 0,
    "last_update": "",
    "kismet_status": "connecting",
}
recent_detections = []
all_devices = []

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>WATCHDOG Live Dashboard</title>
<meta http-equiv="refresh" content="10">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0a0a0a; color: #c0c0c0; font-family: 'Courier New', monospace; padding: 15px; }
h1 { color: #00ff41; font-size: 22px; margin-bottom: 3px; }
.subtitle { color: #555; font-size: 12px; margin-bottom: 15px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 15px; }
.stat { background: #111; border: 1px solid #333; border-radius: 6px; padding: 12px; text-align: center; }
.stat .num { font-size: 28px; font-weight: bold; }
.stat .label { font-size: 10px; color: #666; text-transform: uppercase; }
.green { color: #00ff41; }
.red { color: #ff4444; }
.orange { color: #ff8800; }
.cyan { color: #00bcd4; }
.yellow { color: #ffaa00; }
.purple { color: #aa44ff; }
.panel { background: #111; border: 1px solid #333; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.panel h2 { color: #00aaff; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid #222; padding-bottom: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: #666; padding: 4px 6px; border-bottom: 1px solid #333; }
td { padding: 4px 6px; border-bottom: 1px solid #1a1a1a; }
.alert-row { background: #1a0000; }
.alert-row td { color: #ff4444; }
.drone-row { background: #1a1000; }
.drone-row td { color: #ff8800; }
.camera-row { background: #001a1a; }
.camera-row td { color: #00bcd4; }
.badge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
.badge-alpr { background: #ff4444; color: white; }
.badge-camera { background: #00bcd4; color: black; }
.badge-drone { background: #ff8800; color: black; }
.badge-tracker { background: #aa44ff; color: white; }
.badge-clear { background: #00ff41; color: black; }
.kismet-status { position: absolute; top: 15px; right: 15px; }
.blink { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0.3; } }
</style>
</head>
<body>

<div class="kismet-status">
    <span class="badge {% if kismet_status == 'live' %}badge-clear{% else %}badge-alpr{% endif %}">
        KISMET: {{ kismet_status | upper }}
    </span>
</div>

<h1>WATCHDOG LIVE DASHBOARD</h1>
<div class="subtitle">Surveillance Device Detection | {{ last_update }} | Kismet: {{ kismet_url }}</div>
{% if operator_lat and operator_lon %}
<div class="subtitle">
    GPS: {{ "%.4f"|format(operator_lat) }}, {{ "%.4f"|format(operator_lon) }}
    {% if coverage_area %} | Area: <span class="yellow">{{ coverage_area }}</span>{% endif %}
    {% if nearby_alprs %} | <span class="red">{{ nearby_alprs }} known ALPR{{ 's' if nearby_alprs != 1 else '' }} within 200m</span>{% endif %}
</div>
{% endif %}

<div class="grid">
    <div class="stat"><div class="num cyan">{{ total_devices }}</div><div class="label">Total Devices</div></div>
    <div class="stat"><div class="num {% if cameras > 0 %}red{% else %}green{% endif %}">{{ cameras }}</div><div class="label">Cameras</div></div>
    <div class="stat"><div class="num {% if alprs > 0 %}red{% else %}green{% endif %}">{{ alprs }}</div><div class="label">ALPR</div></div>
    <div class="stat"><div class="num {% if drones > 0 %}orange{% else %}green{% endif %}">{{ drones }}</div><div class="label">Drones</div></div>
    <div class="stat"><div class="num {% if trackers > 0 %}purple{% else %}green{% endif %}">{{ trackers }}</div><div class="label">BLE Trackers</div></div>
    <div class="stat"><div class="num green">{{ clean }}</div><div class="label">Clean</div></div>
</div>

{% if detections %}
<div class="panel" style="border-color: #ff4444;">
    <h2 style="color: #ff4444;">DETECTIONS ({{ detections|length }})</h2>
    <table>
        <tr><th>Type</th><th>Manufacturer</th><th>MAC</th><th>SSID</th><th>RSSI</th><th>CH</th><th>Conf</th><th>Method</th></tr>
        {% for d in detections %}
        <tr class="{% if d.device_type == 'alpr' %}alert-row{% elif d.device_type == 'drone' %}drone-row{% else %}camera-row{% endif %}">
            <td><span class="badge badge-{{ d.device_type }}">{{ d.device_type | upper }}</span></td>
            <td>{{ d.manufacturer }}</td>
            <td>{{ d.mac }}</td>
            <td>{{ d.ssid or '-' }}</td>
            <td>{{ d.rssi }} dBm</td>
            <td>{{ d.channel }}</td>
            <td>{{ "%.0f"|format(d.confidence * 100) }}%</td>
            <td>{{ d.detection_method }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% else %}
<div class="panel" style="border-color: #00ff41;">
    <h2 style="color: #00ff41;">ALL CLEAR</h2>
    <p style="color: #00ff41; text-align: center; padding: 20px;">No surveillance devices detected in current scan</p>
</div>
{% endif %}

<div class="panel">
    <h2>ALL DEVICES ({{ all_devices|length }} shown, {{ total_devices }} total)</h2>
    <table>
        <tr><th>MAC</th><th>Manufacturer</th><th>Type</th><th>Name/SSID</th><th>RSSI</th><th>CH</th><th>Status</th></tr>
        {% for d in all_devices[:50] %}
        <tr>
            <td>{{ d.mac }}</td>
            <td>{{ d.manuf }}</td>
            <td>{{ d.type }}</td>
            <td>{{ d.name }}</td>
            <td>{{ d.signal }} dBm</td>
            <td>{{ d.channel }}</td>
            <td>{% if d.flagged %}<span class="badge badge-{{ d.flag_type }}">{{ d.flag_type | upper }}</span>{% else %}<span style="color:#333;">clean</span>{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
</div>

<div class="subtitle" style="text-align: center; margin-top: 10px;">
    WATCHDOG / CYT-NG / ARES-1 | Auto-refresh: 10s | Phase 1: Passive Detection Only
</div>
</body>
</html>
"""


def fetch_kismet_devices(kismet_url, username, password, last_seconds=30):
    """Fetch recent devices from Kismet REST API.

    Supports two modes:
    - Direct HTTP (when Kismet is reachable from Mac)
    - prlctl exec bridge (when Kismet is in Parallels VM with no routable IP)
    """
    # Try direct HTTP first
    try:
        url = f"{kismet_url}/devices/last-time/-{last_seconds}/devices.json"
        resp = requests.get(url, auth=(username, password), timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

    # Fallback: prlctl exec bridge (Parallels VM)
    try:
        import subprocess
        cmd = [
            'prlctl', 'exec', 'Kali Linux 2025.2 ARM64',
            'curl', '-s', '-u', f'{username}:{password}',
            f'http://localhost:2501/devices/last-time/-{last_seconds}/devices.json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        logger.debug(f"prlctl exec fallback failed: {e}")

    return []


def fetch_kismet_gps(kismet_url, username, password):
    """Fetch current GPS position from Kismet. Returns (lat, lon) or (None, None)."""
    try:
        url = f"{kismet_url}/gps/location.json"
        resp = requests.get(url, auth=(username, password), timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get('kismet.common.location.lat')
            lon = data.get('kismet.common.location.lon')
            if lat and lon:
                return float(lat), float(lon)
    except Exception:
        pass

    try:
        import subprocess
        cmd = [
            'prlctl', 'exec', 'Kali Linux 2025.2 ARM64',
            'curl', '-s', '-u', f'{username}:{password}',
            'http://localhost:2501/gps/location.json',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            lat = data.get('kismet.common.location.lat')
            lon = data.get('kismet.common.location.lon')
            if lat and lon:
                return float(lat), float(lon)
    except Exception as e:
        logger.debug(f"prlctl exec GPS fallback failed: {e}")

    return None, None


def _extract_device_location(dev):
    """Pull (lat, lon) from a Kismet device record, tolerating shape variance."""
    loc = dev.get('kismet.device.base.location') or {}
    for key in ('kismet.common.location.avg_loc', 'kismet.common.location.last_loc', None):
        node = loc.get(key) if key else loc
        if not isinstance(node, dict):
            continue
        lat = node.get('kismet.common.location.lat')
        lon = node.get('kismet.common.location.lon')
        if lat and lon:
            try:
                return float(lat), float(lon)
            except (TypeError, ValueError):
                continue
        geopoint = node.get('kismet.common.location.geopoint')
        if isinstance(geopoint, (list, tuple)) and len(geopoint) >= 2:
            try:
                # Kismet geopoint follows GeoJSON convention: [lon, lat]
                return float(geopoint[1]), float(geopoint[0])
            except (TypeError, ValueError):
                continue
    return 0.0, 0.0


def process_devices(devices):
    """Run WATCHDOG detection on Kismet device list."""
    global recent_detections, all_devices, scan_stats

    detections = []
    device_list = []
    camera_count = 0
    alpr_count = 0
    drone_count = 0
    tracker_count = 0

    for dev in devices:
        mac = dev.get('kismet.device.base.macaddr', '')
        name = dev.get('kismet.device.base.name', '')
        manuf = dev.get('kismet.device.base.manuf', 'Unknown')
        signal = dev.get('kismet.device.base.signal', {}).get(
            'kismet.common.signal.last_signal', -100
        )
        channel = dev.get('kismet.device.base.channel', '0')
        dtype = dev.get('kismet.device.base.type', 'Unknown')
        phy = dev.get('kismet.device.base.phyname', '')

        try:
            ch_int = int(str(channel).split(',')[0]) if channel else 0
        except (ValueError, TypeError):
            ch_int = 0

        flagged = False
        flag_type = ""

        if phy == 'BTLE':
            lat, lon = _extract_device_location(dev)
            ble_det = ble_detector.process_ble_advertisement(
                mac=mac, name=name, rssi=signal,
                latitude=lat, longitude=lon,
            )
            if ble_det:
                detections.append(SimpleNamespace(
                    device_type='tracker',
                    manufacturer=ble_det.description,
                    mac=ble_det.mac,
                    ssid=f"{'FOLLOWING ' if ble_det.is_following else ''}{ble_det.tracker_type}",
                    rssi=ble_det.rssi,
                    channel='BLE',
                    confidence=1.0 if ble_det.is_following else 0.5,
                    detection_method='ble_persistence' if ble_det.is_following else 'ble_signature',
                ))
                flagged = True
                flag_type = 'tracker'
                tracker_count += 1
        else:
            # Run WATCHDOG camera detection
            cam_det = detector.detect(mac, name, signal, ch_int)

            # Also check drone signatures
            drone_result = drone_matcher.classify_device(mac, name)

            if cam_det:
                detections.append(cam_det)
                db_logger.log_detection(cam_det)
                flagged = True
                flag_type = cam_det.device_type
                if cam_det.device_type == 'camera':
                    camera_count += 1
                elif cam_det.device_type == 'alpr':
                    alpr_count += 1
            elif drone_result['is_drone']:
                flagged = True
                flag_type = 'drone'
                drone_count += 1

        device_list.append({
            'mac': mac,
            'name': name,
            'manuf': manuf,
            'signal': signal,
            'channel': channel,
            'type': dtype,
            'flagged': flagged,
            'flag_type': flag_type,
        })

    # Sort: flagged devices first, then by signal strength
    device_list.sort(key=lambda x: (not x['flagged'], x['signal']), reverse=False)
    device_list.sort(key=lambda x: x['flagged'], reverse=True)

    recent_detections = detections
    all_devices = device_list
    scan_stats.update({
        'total_devices': len(devices),
        'cameras': camera_count,
        'alprs': alpr_count,
        'drones': drone_count,
        'trackers': tracker_count,
        'last_update': datetime.now().strftime('%H:%M:%S'),
        'kismet_status': 'live',
    })


@app.route('/')
def dashboard():
    total = scan_stats['total_devices']
    flagged = (scan_stats['cameras'] + scan_stats['alprs']
               + scan_stats['drones'] + scan_stats['trackers'])
    return render_template_string(
        DASHBOARD_HTML,
        total_devices=total,
        cameras=scan_stats['cameras'],
        alprs=scan_stats['alprs'],
        drones=scan_stats['drones'],
        trackers=scan_stats['trackers'],
        clean=max(total - flagged, 0),
        detections=recent_detections,
        all_devices=all_devices,
        last_update=scan_stats['last_update'],
        kismet_status=scan_stats['kismet_status'],
        kismet_url=app.config.get('KISMET_URL', ''),
        coverage_area=scan_stats['coverage_area'],
        nearby_alprs=scan_stats['nearby_alprs'],
        operator_lat=scan_stats['operator_lat'],
        operator_lon=scan_stats['operator_lon'],
    )


def scan_loop(kismet_url, username, password, interval=10):
    """Background thread: continuously fetch and process Kismet data."""
    while True:
        devices = fetch_kismet_devices(kismet_url, username, password)
        if devices:
            process_devices(devices)

            lat, lon = fetch_kismet_gps(kismet_url, username, password)
            if lat is not None and lon is not None:
                summary = alpr_ctx.get_context_summary(lat, lon)
                scan_stats.update({
                    'operator_lat': lat,
                    'operator_lon': lon,
                    'coverage_area': summary.get('coverage_area'),
                    'nearby_alprs': summary.get('nearby_cameras', 0),
                })

            logger.info(
                f"Scan: {len(devices)} devices, "
                f"{scan_stats['cameras']} cameras, "
                f"{scan_stats['alprs']} ALPR, "
                f"{scan_stats['drones']} drones, "
                f"{scan_stats['trackers']} trackers"
            )
        else:
            scan_stats['kismet_status'] = 'disconnected'
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="WATCHDOG Live Dashboard")
    parser.add_argument('--kismet-url', default='http://localhost:2501',
                        help='Kismet REST API URL')
    parser.add_argument('--kismet-user', default='kismet',
                        help='Kismet username')
    parser.add_argument('--kismet-pass', default='watchdog2026',
                        help='Kismet password')
    parser.add_argument('--port', type=int, default=5002,
                        help='Dashboard port')
    parser.add_argument('--interval', type=int, default=10,
                        help='Scan interval in seconds')
    args = parser.parse_args()

    app.config['KISMET_URL'] = args.kismet_url

    # Start background scan thread
    scan_thread = threading.Thread(
        target=scan_loop,
        args=(args.kismet_url, args.kismet_user, args.kismet_pass, args.interval),
        daemon=True,
    )
    scan_thread.start()

    print(f"\n{'='*60}")
    print(f"  WATCHDOG LIVE DASHBOARD")
    print(f"  Kismet: {args.kismet_url}")
    print(f"  Dashboard: http://localhost:{args.port}")
    print(f"  Scan interval: {args.interval}s")
    print(f"  Camera OUIs: {len(detector.camera_ouis)}")
    print(f"  ALPR patterns: {len(detector.alpr_ssid_patterns)}")
    print(f"{'='*60}\n")

    bind_host = os.getenv("BIND_HOST", "127.0.0.1")
    socketio.run(app, host=bind_host, port=args.port, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
