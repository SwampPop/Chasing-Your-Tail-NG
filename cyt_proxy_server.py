#!/usr/bin/env python3
"""
CYT Dashboard Server - Serves dashboard and proxies API requests to VM.
Includes AO (Area of Operation) tracking for device arrivals/departures.
Includes device alias management for naming/categorizing devices.
"""
import os
import json
import subprocess
import time
import requests
from flask import Flask, send_from_directory, request, Response, jsonify
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Configuration
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
VM_API_URL = 'http://10.211.55.10:3000'
API_KEY = '4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y'
VM_NAME = 'CYT-Kali'
ALIASES_FILE = os.path.join(STATIC_DIR, 'device_aliases.json')

# AO Tracker state
_known_devices = {}  # mac -> {last_seen, signal, vendor}
_arrival_log = []    # Recent arrivals
_departure_log = []  # Recent departures
_device_aliases = {} # mac -> {name, category, notes}
DEPARTURE_THRESHOLD = 300  # 5 minutes = departed


# ============ Device Alias Management ============

def load_aliases():
    """Load device aliases from JSON file."""
    global _device_aliases
    try:
        if os.path.exists(ALIASES_FILE):
            with open(ALIASES_FILE, 'r') as f:
                data = json.load(f)
                _device_aliases = data.get('devices', {})
    except Exception as e:
        print(f"Error loading aliases: {e}")
        _device_aliases = {}
    return _device_aliases


def save_aliases():
    """Save device aliases to JSON file."""
    try:
        data = {
            "_comment": "Device aliases for CYT - Add MAC addresses with friendly names",
            "_format": "MAC (uppercase with colons): { name, category, notes }",
            "_categories": ["mine", "household", "neighbor", "guest", "infrastructure", "suspicious", "unknown"],
            "devices": _device_aliases
        }
        with open(ALIASES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving aliases: {e}")
        return False


def get_alias(mac: str) -> dict:
    """Get alias for a MAC address."""
    return _device_aliases.get(mac.upper(), None)


def set_alias(mac: str, name: str, category: str = "unknown", notes: str = ""):
    """Set alias for a MAC address."""
    _device_aliases[mac.upper()] = {
        "name": name,
        "category": category,
        "notes": notes,
        "added": datetime.now().isoformat()
    }
    save_aliases()


# Load aliases on startup
load_aliases()


def vm_exec(command: str, timeout: int = 10) -> str:
    """Execute a command in the VM and return output."""
    try:
        result = subprocess.run(
            ['prlctl', 'exec', VM_NAME, command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def lookup_vendor(mac: str) -> str:
    """Look up vendor from MAC address."""
    try:
        from mac_vendor_lookup import MacLookup
        return MacLookup().lookup(mac)
    except:
        # Check if randomized MAC
        try:
            if mac[1].upper() in ['2', '6', 'A', 'E']:
                return "Randomized"
        except:
            pass
        return "Unknown"


def get_current_devices_from_vm() -> dict:
    """Query VM for current devices from Kismet database."""
    query = """
    sqlite3 /home/parallels/CYT/logs/kismet/*.kismet '
    SELECT devmac, first_time, last_time, strongest_signal, type
    FROM devices
    WHERE last_time > strftime(\"%s\", \"now\") - 300
    ORDER BY last_time DESC
    ' 2>/dev/null
    """
    output = vm_exec(query.strip())

    devices = {}
    if output and not output.startswith("ERROR"):
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    mac = parts[0]
                    devices[mac] = {
                        'mac': mac,
                        'first_time': int(parts[1]) if parts[1] else 0,
                        'last_time': int(parts[2]) if parts[2] else 0,
                        'signal': int(parts[3]) if parts[3] else 0,
                        'type': parts[4] if len(parts) > 4 else 'Unknown',
                        'vendor': lookup_vendor(mac)
                    }
    return devices


def update_ao_tracking():
    """Update arrival/departure tracking."""
    global _known_devices, _arrival_log, _departure_log

    current_time = time.time()
    current_devices = get_current_devices_from_vm()

    new_arrivals = []
    new_departures = []

    # Detect arrivals
    for mac, device in current_devices.items():
        if mac not in _known_devices:
            arrival = {
                'mac': mac,
                'vendor': device['vendor'],
                'signal': device['signal'],
                'timestamp': current_time,
                'time_str': datetime.now().strftime('%H:%M:%S')
            }
            new_arrivals.append(arrival)
            _arrival_log.insert(0, arrival)

        _known_devices[mac] = {
            'last_seen': device['last_time'],
            'signal': device['signal'],
            'vendor': device['vendor']
        }

    # Detect departures
    departed_macs = []
    for mac, info in _known_devices.items():
        if mac not in current_devices:
            time_since_seen = current_time - info['last_seen']
            if time_since_seen > DEPARTURE_THRESHOLD:
                departure = {
                    'mac': mac,
                    'vendor': info['vendor'],
                    'signal': info['signal'],
                    'timestamp': current_time,
                    'time_str': datetime.now().strftime('%H:%M:%S'),
                    'duration_in_ao': int(time_since_seen)
                }
                new_departures.append(departure)
                _departure_log.insert(0, departure)
                departed_macs.append(mac)

    for mac in departed_macs:
        del _known_devices[mac]

    # Keep logs limited to last 100 entries
    _arrival_log = _arrival_log[:100]
    _departure_log = _departure_log[:100]

    return new_arrivals, new_departures


def get_ao_regulars_from_vm() -> list:
    """Get devices that regularly appear in the AO from history database."""
    query = """
    sqlite3 /home/parallels/CYT/cyt_history.db '
    SELECT
        mac,
        COUNT(*) as appearances,
        MIN(timestamp) as first_seen,
        MAX(timestamp) as last_seen
    FROM appearances
    GROUP BY mac
    HAVING appearances >= 5
    ORDER BY appearances DESC
    LIMIT 30
    ' 2>/dev/null
    """
    output = vm_exec(query.strip())

    regulars = []
    if output and not output.startswith("ERROR"):
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    mac = parts[0]
                    appearances = int(parts[1])
                    first_seen = float(parts[2])
                    last_seen = float(parts[3])

                    total_time = max(last_seen - first_seen, 1)
                    apps_per_hour = (appearances / total_time) * 3600

                    if apps_per_hour > 10:
                        pattern = 'constant'
                    elif apps_per_hour > 5:
                        pattern = 'frequent'
                    elif apps_per_hour > 1:
                        pattern = 'occasional'
                    else:
                        pattern = 'rare'

                    regulars.append({
                        'mac': mac,
                        'vendor': lookup_vendor(mac),
                        'appearances': appearances,
                        'first_seen': datetime.fromtimestamp(first_seen).strftime('%H:%M'),
                        'last_seen': datetime.fromtimestamp(last_seen).strftime('%H:%M'),
                        'pattern': pattern,
                        'hours_tracked': round(total_time / 3600, 1)
                    })
    return regulars


# ============ Routes ============

@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'dashboard_ao.html')


@app.route('/dashboard.html')
def dashboard():
    return send_from_directory(STATIC_DIR, 'dashboard_ao.html')


@app.route('/dashboard_local.html')
def dashboard_local():
    return send_from_directory(STATIC_DIR, 'dashboard_local.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# Proxy API endpoints to VM
@app.route('/api/<path:endpoint>')
def proxy_api(endpoint):
    """Proxy API requests to the VM."""
    # Handle local AO endpoints
    if endpoint == 'ao/activity':
        return ao_activity()
    elif endpoint == 'ao/regulars':
        return ao_regulars()
    elif endpoint == 'ao/summary':
        return ao_summary()

    # Proxy to VM
    try:
        headers = {'X-API-Key': API_KEY}
        resp = requests.get(f'{VM_API_URL}/{endpoint}', headers=headers, timeout=5)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 503


# AO Tracking Endpoints
@app.route('/api/ao/activity')
def ao_activity():
    """Get recent AO activity (arrivals/departures)."""
    arrivals, departures = update_ao_tracking()
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'new_arrivals': arrivals,
        'new_departures': departures,
        'recent_arrivals': _arrival_log[:20],
        'recent_departures': _departure_log[:20],
        'currently_tracked': len(_known_devices)
    })


@app.route('/api/ao/regulars')
def ao_regulars():
    """Get AO regulars (frequently seen devices)."""
    regulars = get_ao_regulars_from_vm()
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'regulars': regulars,
        'count': len(regulars)
    })


@app.route('/api/ao/summary')
def ao_summary():
    """Get AO summary statistics."""
    update_ao_tracking()
    regulars = get_ao_regulars_from_vm()
    regular_macs = {r['mac'] for r in regulars}

    # Categorize current devices
    new_devices = []
    known_devices = []

    for mac, info in _known_devices.items():
        device = {
            'mac': mac,
            'vendor': info['vendor'],
            'signal': info['signal']
        }
        if mac in regular_macs:
            known_devices.append(device)
        else:
            new_devices.append(device)

    # Sort by signal strength
    new_devices.sort(key=lambda x: x['signal'], reverse=True)

    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'total_tracked': len(_known_devices),
        'known_count': len(known_devices),
        'new_count': len(new_devices),
        'new_devices': new_devices[:15],
        'arrivals_last_hour': len([a for a in _arrival_log if time.time() - a['timestamp'] < 3600]),
        'departures_last_hour': len([d for d in _departure_log if time.time() - d['timestamp'] < 3600]),
        'regulars_count': len(regulars)
    })


# ============ Device Alias Endpoints ============

@app.route('/api/aliases', methods=['GET'])
def get_aliases():
    """Get all device aliases."""
    load_aliases()  # Reload in case file was edited
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'aliases': _device_aliases,
        'count': len(_device_aliases)
    })


@app.route('/api/aliases/<mac>', methods=['GET'])
def get_device_alias(mac):
    """Get alias for a specific device."""
    alias = get_alias(mac)
    if alias:
        return jsonify({'mac': mac.upper(), 'alias': alias})
    return jsonify({'mac': mac.upper(), 'alias': None}), 404


@app.route('/api/aliases', methods=['POST'])
def add_alias():
    """Add or update a device alias."""
    data = request.get_json()
    if not data or 'mac' not in data or 'name' not in data:
        return jsonify({'error': 'mac and name required'}), 400

    mac = data['mac'].upper()
    name = data['name']
    category = data.get('category', 'unknown')
    notes = data.get('notes', '')

    set_alias(mac, name, category, notes)

    return jsonify({
        'success': True,
        'mac': mac,
        'alias': _device_aliases[mac]
    })


@app.route('/api/aliases/<mac>', methods=['DELETE'])
def delete_alias(mac):
    """Delete a device alias."""
    mac_upper = mac.upper()
    if mac_upper in _device_aliases:
        del _device_aliases[mac_upper]
        save_aliases()
        return jsonify({'success': True, 'mac': mac_upper})
    return jsonify({'error': 'Alias not found'}), 404


@app.route('/api/device/<mac>/identify', methods=['GET'])
def identify_device(mac):
    """Get detailed identification info for a device."""
    mac_upper = mac.upper()

    # Get alias if exists
    alias = get_alias(mac_upper)

    # Get vendor info
    vendor = lookup_vendor(mac_upper)

    # Query Kismet for device details
    query = f"""
    sqlite3 /home/parallels/CYT/logs/kismet/*.kismet "
    SELECT devmac, first_time, last_time, strongest_signal, type,
           substr(device, instr(device, 'last_bssid')+14, 17) as connected_to
    FROM devices
    WHERE devmac = '{mac_upper}'
    " 2>/dev/null
    """
    output = vm_exec(query.strip())

    device_info = None
    if output and not output.startswith("ERROR") and '|' in output:
        parts = output.split('|')
        if len(parts) >= 5:
            device_info = {
                'first_seen': datetime.fromtimestamp(int(parts[1])).strftime('%Y-%m-%d %H:%M:%S') if parts[1] else None,
                'last_seen': datetime.fromtimestamp(int(parts[2])).strftime('%Y-%m-%d %H:%M:%S') if parts[2] else None,
                'signal': int(parts[3]) if parts[3] else 0,
                'type': parts[4] if parts[4] else 'Unknown',
                'connected_to': parts[5] if len(parts) > 5 and parts[5] else None
            }

    # Get appearance history
    history_query = f"""
    sqlite3 /home/parallels/CYT/cyt_history.db "
    SELECT COUNT(*) as appearances,
           MIN(timestamp) as first_seen,
           MAX(timestamp) as last_seen
    FROM appearances
    WHERE mac = '{mac_upper}'
    " 2>/dev/null
    """
    history_output = vm_exec(history_query.strip())

    history = None
    if history_output and not history_output.startswith("ERROR") and '|' in history_output:
        parts = history_output.split('|')
        if len(parts) >= 3 and parts[0]:
            history = {
                'total_appearances': int(parts[0]),
                'tracking_since': datetime.fromtimestamp(float(parts[1])).strftime('%Y-%m-%d %H:%M') if parts[1] else None,
                'last_appearance': datetime.fromtimestamp(float(parts[2])).strftime('%Y-%m-%d %H:%M') if parts[2] else None
            }

    return jsonify({
        'mac': mac_upper,
        'vendor': vendor,
        'alias': alias,
        'device_info': device_info,
        'history': history,
        'identification_tips': get_identification_tips(mac_upper, vendor, device_info, history)
    })


def get_identification_tips(mac: str, vendor: str, device_info: dict, history: dict) -> list:
    """Generate identification tips based on device characteristics."""
    tips = []

    # Signal strength tips
    if device_info and device_info.get('signal'):
        signal = device_info['signal']
        if signal > -40:
            tips.append("Very strong signal - likely in same room or immediately adjacent")
        elif signal > -55:
            tips.append("Strong signal - probably same building/nearby")
        elif signal > -70:
            tips.append("Moderate signal - could be neighbor or nearby outdoor")
        else:
            tips.append("Weak signal - likely far away or through multiple walls")

    # Vendor-based tips
    if vendor:
        if 'Apple' in vendor:
            tips.append("Apple device - check iPhone/iPad/Mac WiFi settings for this MAC")
        elif 'Amazon' in vendor:
            tips.append("Amazon device - likely Echo, Fire TV, or Ring device")
        elif 'Espressif' in vendor:
            tips.append("ESP32/ESP8266 chip - smart home device (plugs, bulbs, sensors)")
        elif 'Randomized' in vendor:
            tips.append("Randomized MAC - modern phone/tablet with privacy feature enabled")
        elif any(x in vendor for x in ['Vantiva', 'HUMAX', 'Arcadyan', 'Sagemcom']):
            tips.append("ISP equipment - likely a neighbor's cable modem or router")

    # Connection-based tips
    if device_info and device_info.get('connected_to'):
        tips.append(f"Connected to BSSID: {device_info['connected_to']} - look up this router")

    # History-based tips
    if history and history.get('total_appearances'):
        apps = history['total_appearances']
        if apps > 50:
            tips.append(f"Seen {apps} times - this is a regular in your area")
        elif apps > 10:
            tips.append(f"Seen {apps} times - appears periodically")
        else:
            tips.append(f"Only seen {apps} times - relatively new to your area")

    # Identification actions
    tips.append("To identify: Turn off your devices one by one and watch which MAC disappears")

    return tips


if __name__ == '__main__':
    print('=' * 50)
    print('CYT Dashboard Server with AO Tracking')
    print('=' * 50)
    print(f'Dashboard:    http://localhost:8080/')
    print(f'API Status:   http://localhost:8080/api/status')
    print(f'AO Activity:  http://localhost:8080/api/ao/activity')
    print(f'AO Regulars:  http://localhost:8080/api/ao/regulars')
    print(f'AO Summary:   http://localhost:8080/api/ao/summary')
    print(f'Aliases:      http://localhost:8080/api/aliases')
    print(f'VM API:       {VM_API_URL}')
    print('=' * 50)
    app.run(host='0.0.0.0', port=8080, debug=False)
