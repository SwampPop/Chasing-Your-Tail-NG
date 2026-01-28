#!/usr/bin/env python3
"""
CYT Dashboard Server - Serves dashboard and proxies API requests to VM.
Includes AO (Area of Operation) tracking for device arrivals/departures.
Includes device alias management for naming/categorizing devices.

Security: API endpoints require authentication via X-API-Key header or
          ?api_key query parameter. Set CYT_DASHBOARD_API_KEY env var.
"""
import os
import re
import json
import subprocess
import time
import logging
import requests
import functools
from typing import Dict, List, Optional, Tuple, Any
from flask import Flask, send_from_directory, request, Response, jsonify
from flask_cors import CORS
from datetime import datetime

from vendor_lookup import lookup_vendor  # Shared vendor lookup utility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Restrict CORS to localhost only (security fix)
CORS(app, origins=['http://localhost:8080', 'http://127.0.0.1:8080'])

# ============ Configuration Constants ============

# Server configuration (from environment)
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
VM_API_URL = os.getenv('CYT_VM_API_URL', 'http://10.211.55.10:3000')
VM_API_KEY = os.getenv('CYT_VM_API_KEY', '')
DASHBOARD_API_KEY = os.getenv('CYT_DASHBOARD_API_KEY', '')
VM_NAME = os.getenv('CYT_VM_NAME', 'CYT-Kali')
ALIASES_FILE = os.path.join(STATIC_DIR, 'device_aliases.json')

# VM database paths
VM_KISMET_DB_DIR = '/home/parallels/CYT/logs/kismet'
VM_HISTORY_DB_PATH = '/home/parallels/CYT/cyt_history.db'

# Cached latest Kismet DB path
_cached_kismet_db: Optional[str] = None
_kismet_db_cache_time: float = 0
KISMET_DB_CACHE_TTL = 60  # Refresh cache every 60 seconds

# AO Tracker thresholds
DEPARTURE_THRESHOLD_SECONDS = 300  # 5 minutes without seeing = departed
MAX_LOG_ENTRIES = 100  # Maximum entries in arrival/departure logs
MIN_APPEARANCES_FOR_REGULAR = 5  # Minimum appearances to be considered "regular"
MAX_REGULARS_DISPLAYED = 30  # Maximum regulars to return

# Pattern classification thresholds (appearances per hour)
PATTERN_CONSTANT_THRESHOLD = 10  # Seen almost every scan
PATTERN_FREQUENT_THRESHOLD = 5
PATTERN_OCCASIONAL_THRESHOLD = 1

# Signal strength thresholds (dBm)
SIGNAL_VERY_STRONG = -40  # Same room
SIGNAL_STRONG = -55  # Same building
SIGNAL_MODERATE = -70  # Neighbor/nearby

# Input validation limits
MAX_ALIAS_NAME_LENGTH = 100
MAX_ALIAS_NOTES_LENGTH = 500

# Valid device categories
VALID_CATEGORIES = frozenset([
    'mine', 'household', 'neighbor', 'guest',
    'infrastructure', 'suspicious', 'unknown'
])

# MAC address validation pattern (security: prevent injection)
MAC_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')


def validate_mac(mac: str) -> bool:
    """Validate MAC address format to prevent injection attacks."""
    if not mac or not isinstance(mac, str):
        return False
    return bool(MAC_PATTERN.match(mac))


def require_api_key(f):
    """Decorator to require API key authentication for endpoints."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth if no key is configured (development mode)
        if not DASHBOARD_API_KEY:
            return f(*args, **kwargs)

        # Check header first, then query param
        provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not provided_key:
            return jsonify({'error': 'API key required. Set X-API-Key header or api_key param.'}), 401

        if provided_key != DASHBOARD_API_KEY:
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)
    return decorated_function

# AO Tracker state
_known_devices: Dict[str, Dict[str, Any]] = {}  # mac -> {last_seen, signal, vendor}
_arrival_log: List[Dict[str, Any]] = []  # Recent arrivals
_departure_log: List[Dict[str, Any]] = []  # Recent departures
_device_aliases: Dict[str, Dict[str, Any]] = {}  # mac -> {name, category, notes}


# ============ Device Alias Management ============

def load_aliases():
    """Load device aliases from JSON file."""
    global _device_aliases
    try:
        if os.path.exists(ALIASES_FILE):
            with open(ALIASES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _device_aliases = data.get('devices', {})
                logger.info(f"Loaded {len(_device_aliases)} device aliases")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in aliases file: {e}")
        _device_aliases = {}
    except (IOError, OSError) as e:
        logger.error(f"Error reading aliases file: {e}")
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
        with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(_device_aliases)} device aliases")
        return True
    except (IOError, OSError) as e:
        logger.error(f"Error saving aliases file: {e}")
        return False
    except TypeError as e:
        logger.error(f"Error serializing aliases to JSON: {e}")
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
    except subprocess.TimeoutExpired:
        logger.warning(f"VM command timed out after {timeout}s: {command[:50]}...")
        return "ERROR: Command timed out"
    except subprocess.SubprocessError as e:
        logger.error(f"VM subprocess error: {e}")
        return f"ERROR: {e}"
    except OSError as e:
        logger.error(f"VM exec OS error (prlctl not found?): {e}")
        return f"ERROR: {e}"


def get_latest_kismet_db() -> Optional[str]:
    """Get the most recent Kismet database file from the VM."""
    global _cached_kismet_db, _kismet_db_cache_time

    # Use cached value if recent
    if _cached_kismet_db and (time.time() - _kismet_db_cache_time < KISMET_DB_CACHE_TTL):
        return _cached_kismet_db

    # Find the latest .kismet file
    cmd = f"ls -t {VM_KISMET_DB_DIR}/*.kismet 2>/dev/null | head -1"
    result = vm_exec(cmd)

    if result and not result.startswith("ERROR") and result.strip():
        _cached_kismet_db = result.strip()
        _kismet_db_cache_time = time.time()
        logger.debug(f"Latest Kismet DB: {_cached_kismet_db}")
        return _cached_kismet_db

    logger.warning(f"No Kismet DB found in {VM_KISMET_DB_DIR}")
    return None


def get_current_devices_from_vm() -> Dict[str, Dict[str, Any]]:
    """Query VM for current devices from Kismet database."""
    kismet_db = get_latest_kismet_db()
    if not kismet_db:
        logger.warning("No Kismet DB available")
        return {}

    query = f"""
    sqlite3 '{kismet_db}' '
    SELECT devmac, first_time, last_time, strongest_signal, type
    FROM devices
    WHERE last_time > strftime("%s", "now") - {DEPARTURE_THRESHOLD_SECONDS}
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


def update_ao_tracking() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Update arrival/departure tracking.

    Returns:
        Tuple of (new_arrivals, new_departures) lists
    """
    global _known_devices, _arrival_log, _departure_log

    current_time = time.time()
    current_devices = get_current_devices_from_vm()

    new_arrivals: List[Dict[str, Any]] = []
    new_departures: List[Dict[str, Any]] = []

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
    departed_macs: List[str] = []
    for mac, info in _known_devices.items():
        if mac not in current_devices:
            time_since_seen = current_time - info['last_seen']
            if time_since_seen > DEPARTURE_THRESHOLD_SECONDS:
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

    # Keep logs limited
    _arrival_log = _arrival_log[:MAX_LOG_ENTRIES]
    _departure_log = _departure_log[:MAX_LOG_ENTRIES]

    return new_arrivals, new_departures


def get_ao_regulars_from_vm() -> List[Dict[str, Any]]:
    """Get devices that regularly appear in the AO from history database."""
    query = f"""
    sqlite3 {VM_HISTORY_DB_PATH} '
    SELECT
        mac,
        COUNT(*) as appearances,
        MIN(timestamp) as first_seen,
        MAX(timestamp) as last_seen
    FROM appearances
    GROUP BY mac
    HAVING appearances >= {MIN_APPEARANCES_FOR_REGULAR}
    ORDER BY appearances DESC
    LIMIT {MAX_REGULARS_DISPLAYED}
    ' 2>/dev/null
    """
    output = vm_exec(query.strip())

    regulars: List[Dict[str, Any]] = []
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

                    pattern = _classify_appearance_pattern(apps_per_hour)

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


def _classify_appearance_pattern(apps_per_hour: float) -> str:
    """Classify device appearance pattern based on frequency.

    Args:
        apps_per_hour: Number of appearances per hour

    Returns:
        Pattern classification string
    """
    if apps_per_hour > PATTERN_CONSTANT_THRESHOLD:
        return 'constant'
    elif apps_per_hour > PATTERN_FREQUENT_THRESHOLD:
        return 'frequent'
    elif apps_per_hour > PATTERN_OCCASIONAL_THRESHOLD:
        return 'occasional'
    else:
        return 'rare'


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


# Kismet UI proxy - reverse proxy to VM's Kismet web interface
VM_KISMET_URL = os.getenv('CYT_VM_KISMET_URL', 'http://10.211.55.10:2501')

@app.route('/kismet/')
@app.route('/kismet/<path:subpath>')
def proxy_kismet(subpath=''):
    """Proxy requests to Kismet UI on the VM."""
    try:
        # Build target URL
        target_url = f'{VM_KISMET_URL}/{subpath}'
        if request.query_string:
            target_url += f'?{request.query_string.decode()}'

        # Forward the request
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for key, value in request.headers if key.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=10
        )

        # Build response, fixing any absolute URLs in HTML content
        content = resp.content
        content_type = resp.headers.get('Content-Type', '')

        if 'text/html' in content_type:
            # Rewrite absolute URLs to go through proxy
            content = content.replace(b'href="/', b'href="/kismet/')
            content = content.replace(b'src="/', b'src="/kismet/')
            content = content.replace(b"href='/", b"href='/kismet/")
            content = content.replace(b"src='/", b"src='/kismet/")

        # Build response headers (exclude hop-by-hop headers)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(content, resp.status_code, headers)
    except requests.exceptions.RequestException as e:
        logger.error(f"Kismet proxy error: {e}")
        return f"<h1>Cannot connect to Kismet</h1><p>Error: {e}</p><p>VM Kismet URL: {VM_KISMET_URL}</p>", 503


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
    elif endpoint == 'attacks':
        return get_attacks()
    elif endpoint == 'watchlist':
        return get_watchlist()

    # Proxy to VM
    try:
        headers = {'X-API-Key': VM_API_KEY} if VM_API_KEY else {}
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
    mac_upper = mac.upper()

    # SECURITY: Validate MAC address format
    if not validate_mac(mac_upper):
        return jsonify({'error': 'Invalid MAC address format'}), 400

    alias = get_alias(mac_upper)
    if alias:
        return jsonify({'mac': mac_upper, 'alias': alias})
    return jsonify({'mac': mac_upper, 'alias': None}), 404


@app.route('/api/aliases', methods=['POST'])
@require_api_key
def add_alias():
    """Add or update a device alias."""
    data = request.get_json()
    if not data or 'mac' not in data or 'name' not in data:
        return jsonify({'error': 'mac and name required'}), 400

    mac = data['mac'].upper()

    # SECURITY: Validate MAC address format
    if not validate_mac(mac):
        return jsonify({'error': 'Invalid MAC address format'}), 400

    # SECURITY: Sanitize inputs (limit length, strip dangerous chars)
    name = str(data['name'])[:MAX_ALIAS_NAME_LENGTH].strip()
    if not name:
        return jsonify({'error': 'Name cannot be empty'}), 400

    category = data.get('category', 'unknown')
    if category not in VALID_CATEGORIES:
        category = 'unknown'

    notes = str(data.get('notes', ''))[:MAX_ALIAS_NOTES_LENGTH].strip()

    set_alias(mac, name, category, notes)

    return jsonify({
        'success': True,
        'mac': mac,
        'alias': _device_aliases[mac]
    })


@app.route('/api/aliases/<mac>', methods=['DELETE'])
@require_api_key
def delete_alias(mac):
    """Delete a device alias."""
    mac_upper = mac.upper()

    # SECURITY: Validate MAC address format
    if not validate_mac(mac_upper):
        return jsonify({'error': 'Invalid MAC address format'}), 400

    if mac_upper in _device_aliases:
        del _device_aliases[mac_upper]
        save_aliases()
        return jsonify({'success': True, 'mac': mac_upper})
    return jsonify({'error': 'Alias not found'}), 404


# ============ Attack Monitoring Endpoints ============

# Attack types and their severity levels
ATTACK_TYPES = {
    'DEAUTHFLOOD': {'severity': 'critical', 'description': 'Deauthentication flood attack'},
    'DISASSOCFLOOD': {'severity': 'critical', 'description': 'Disassociation flood attack'},
    'DEAUTHCODEINVALID': {'severity': 'high', 'description': 'Invalid deauth reason code'},
    'DISCONCODEINVALID': {'severity': 'medium', 'description': 'Invalid disconnection code'},
    'BSSTIMESTAMP': {'severity': 'medium', 'description': 'BSS timestamp anomaly'},
    'PROBECHANNEL': {'severity': 'low', 'description': 'Probe on wrong channel'},
    'APSPOOF': {'severity': 'critical', 'description': 'Access point spoofing detected'},
    'WEPCRACK': {'severity': 'critical', 'description': 'WEP cracking attempt'},
    'WPSBRUTE': {'severity': 'high', 'description': 'WPS brute force attack'},
}

ACTIVE_ATTACK_WINDOW = 300  # 5 minutes - considered "active"
RECENT_ATTACK_WINDOW = 3600  # 1 hour - considered "recent"


@app.route('/api/attacks', methods=['GET'])
def get_attacks():
    """Get attack information including active attacks, recent attacks, and known threat actors."""
    import sqlite3

    kismet_db = get_latest_kismet_db()
    current_time = time.time()

    active_attacks = []
    recent_attacks = []

    if kismet_db:
        # Query for recent alerts from Kismet
        query = f"""
        sqlite3 'file:{kismet_db}?mode=ro' "
        SELECT ts_sec, devmac, header, aux
        FROM alerts
        WHERE ts_sec > {int(current_time - RECENT_ATTACK_WINDOW)}
        ORDER BY ts_sec DESC
        LIMIT 100
        " 2>/dev/null
        """
        output = vm_exec(query.strip(), timeout=15)

        if output and not output.startswith("ERROR"):
            for line in output.split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        ts = int(parts[0]) if parts[0] else 0
                        mac = parts[1] if parts[1] else 'UNKNOWN'
                        header = parts[2] if parts[2] else 'UNKNOWN'
                        aux = parts[3] if len(parts) > 3 else ''

                        attack_info = ATTACK_TYPES.get(header, {'severity': 'unknown', 'description': header})
                        age_seconds = current_time - ts

                        attack_entry = {
                            'timestamp': ts,
                            'time_str': datetime.fromtimestamp(ts).strftime('%H:%M:%S'),
                            'time_ago': format_time_ago(age_seconds),
                            'mac': mac,
                            'type': header,
                            'severity': attack_info['severity'],
                            'description': attack_info['description'],
                            'details': aux,
                            'vendor': lookup_vendor(mac) if mac != 'UNKNOWN' else None
                        }

                        if age_seconds <= ACTIVE_ATTACK_WINDOW:
                            active_attacks.append(attack_entry)
                        else:
                            recent_attacks.append(attack_entry)

    # Get known threat actors from watchlist
    watchlist_db = os.path.join(STATIC_DIR, 'watchlist.db')
    threat_actors = []

    if os.path.exists(watchlist_db):
        try:
            conn = sqlite3.connect(watchlist_db)
            cur = conn.cursor()
            cur.execute('SELECT mac, ssid, reason FROM watchlist')

            for row in cur.fetchall():
                mac, ssid, reason = row
                reason_lower = reason.lower() if reason else ''
                ssid_lower = ssid.lower() if ssid else ''

                # Only include actual threat actors
                is_attacker = any(kw in reason_lower for kw in
                    ['deauthflood', 'flood source', 'spoof', 'malicious', 'attacker', 'suspect'])
                is_attacker = is_attacker or 'attacker' in ssid_lower

                is_protective = 'your network' in reason_lower or 'your router' in reason_lower

                if is_attacker and not is_protective:
                    threat_actors.append({
                        'mac': mac.upper(),
                        'ssid': ssid,
                        'reason': reason,
                        'vendor': lookup_vendor(mac)
                    })

            conn.close()
        except Exception as e:
            logger.error(f'Error reading watchlist for attacks: {e}')

    # Aggregate attack statistics
    attack_macs = set()
    attack_types_seen = {}
    for attack in active_attacks + recent_attacks:
        attack_macs.add(attack['mac'])
        attack_type = attack['type']
        attack_types_seen[attack_type] = attack_types_seen.get(attack_type, 0) + 1

    # Determine overall threat status
    if active_attacks and any(a['severity'] == 'critical' for a in active_attacks):
        threat_status = 'ACTIVE_CRITICAL'
    elif active_attacks:
        threat_status = 'ACTIVE'
    elif recent_attacks and any(a['severity'] == 'critical' for a in recent_attacks):
        threat_status = 'RECENT_CRITICAL'
    elif recent_attacks:
        threat_status = 'RECENT'
    else:
        threat_status = 'CLEAR'

    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'threat_status': threat_status,
        'active_attacks': active_attacks,
        'active_count': len(active_attacks),
        'recent_attacks': recent_attacks[:20],  # Limit to 20 most recent
        'recent_count': len(recent_attacks),
        'unique_attackers': len(attack_macs),
        'attack_types': attack_types_seen,
        'threat_actors': threat_actors,
        'windows': {
            'active_minutes': ACTIVE_ATTACK_WINDOW // 60,
            'recent_minutes': RECENT_ATTACK_WINDOW // 60
        }
    })


def format_time_ago(seconds: float) -> str:
    """Format seconds into human-readable time ago string."""
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m ago"


@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """Get all watchlist entries for dashboard color coding."""
    import sqlite3
    watchlist_db = os.path.join(STATIC_DIR, 'watchlist.db')

    if not os.path.exists(watchlist_db):
        return jsonify({'watched_macs': [], 'attacker_macs': [], 'count': 0})

    try:
        conn = sqlite3.connect(watchlist_db)
        cur = conn.cursor()
        cur.execute('SELECT mac, ssid, reason FROM watchlist')

        watched = []
        attackers = []

        for row in cur.fetchall():
            mac, ssid, reason = row
            entry = {'mac': mac.upper(), 'ssid': ssid, 'reason': reason}

            # Classify as attacker only if explicitly marked as threat
            reason_lower = reason.lower() if reason else ''
            ssid_lower = ssid.lower() if ssid else ''

            # Explicit attacker indicators
            is_attacker = any(kw in reason_lower for kw in ['deauthflood', 'flood source', 'spoof', 'malicious', 'attacker'])
            is_attacker = is_attacker or 'attacker' in ssid_lower

            # Exclude "monitor for attacks" - that's protective monitoring, not an attacker
            is_protective = 'your network' in reason_lower or 'your router' in reason_lower or 'neighbor monitoring' in reason_lower or 'victim' in reason_lower

            if is_attacker and not is_protective:
                attackers.append(entry)
            else:
                watched.append(entry)

        conn.close()

        return jsonify({
            'watched_macs': [e['mac'] for e in watched],
            'attacker_macs': [e['mac'] for e in attackers],
            'watched_details': watched,
            'attacker_details': attackers,
            'count': len(watched) + len(attackers)
        })
    except Exception as e:
        logger.error(f'Watchlist error: {e}')
        return jsonify({'watched_macs': [], 'attacker_macs': [], 'count': 0})


@app.route('/api/device/<mac>/identify', methods=['GET'])
@require_api_key
def identify_device(mac):
    """Get detailed identification info for a device."""
    mac_upper = mac.upper()

    # SECURITY: Validate MAC address format to prevent SQL injection
    if not validate_mac(mac_upper):
        return jsonify({'error': 'Invalid MAC address format'}), 400

    # Get alias if exists
    alias = get_alias(mac_upper)

    # Get vendor info
    vendor = lookup_vendor(mac_upper)

    # Query Kismet for device details
    kismet_db = get_latest_kismet_db()
    device_info = None
    if kismet_db:
        query = f"""
        sqlite3 '{kismet_db}' "
        SELECT devmac, first_time, last_time, strongest_signal, type,
               substr(device, instr(device, 'last_bssid')+14, 17) as connected_to
        FROM devices
        WHERE devmac = '{mac_upper}'
        " 2>/dev/null
        """
        output = vm_exec(query.strip())
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
    sqlite3 {VM_HISTORY_DB_PATH} "
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


def get_identification_tips(
    mac: str,
    vendor: Optional[str],
    device_info: Optional[Dict[str, Any]],
    history: Optional[Dict[str, Any]]
) -> List[str]:
    """Generate identification tips based on device characteristics.

    Args:
        mac: MAC address of the device
        vendor: Vendor name from OUI lookup
        device_info: Device info from Kismet database
        history: Appearance history from CYT database

    Returns:
        List of identification tip strings
    """
    tips: List[str] = []

    # Signal strength tips
    if device_info and device_info.get('signal'):
        signal = device_info['signal']
        if signal > SIGNAL_VERY_STRONG:
            tips.append("Very strong signal - likely in same room or immediately adjacent")
        elif signal > SIGNAL_STRONG:
            tips.append("Strong signal - probably same building/nearby")
        elif signal > SIGNAL_MODERATE:
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
    print('=' * 60)
    print('CYT Dashboard Server with AO Tracking')
    print('=' * 60)
    print(f'Dashboard:    http://localhost:8080/')
    print(f'API Status:   http://localhost:8080/api/status')
    print(f'AO Activity:  http://localhost:8080/api/ao/activity')
    print(f'AO Regulars:  http://localhost:8080/api/ao/regulars')
    print(f'AO Summary:   http://localhost:8080/api/ao/summary')
    print(f'Aliases:      http://localhost:8080/api/aliases')
    print(f'VM API:       {VM_API_URL}')
    print('-' * 60)
    print('SECURITY CONFIGURATION:')
    if DASHBOARD_API_KEY:
        print(f'  Dashboard API Key: ENABLED (set via CYT_DASHBOARD_API_KEY)')
    else:
        print(f'  Dashboard API Key: DISABLED (development mode)')
        print(f'  Set CYT_DASHBOARD_API_KEY env var to enable authentication')
    if VM_API_KEY:
        print(f'  VM API Key: ENABLED (set via CYT_VM_API_KEY)')
    else:
        print(f'  VM API Key: NOT SET')
    print(f'  CORS: Restricted to localhost:8080')
    print('=' * 60)
    app.run(host='0.0.0.0', port=8080, debug=False)
