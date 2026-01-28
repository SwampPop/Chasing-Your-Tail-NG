#!/usr/bin/env python3
"""CYT API Server with CORS support for dashboard access - Standalone version."""
import logging
import time
import glob
import os
import sqlite3
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration - auto-detect paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KISMET_LOGS_DIR = os.path.join(SCRIPT_DIR, 'logs', 'kismet')
API_KEY = '4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y'

def get_latest_db():
    pattern = os.path.join(KISMET_LOGS_DIR, '*.kismet')
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({'error': 'Invalid API key'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/status')
@require_api_key
def status():
    db_path = get_latest_db()
    if not db_path:
        return jsonify({'error': 'No database', 'alert_level': 'GREEN',
                       'traffic_5m': 0, 'traffic_15m': 0, 'drones_detected': 0,
                       'drone_list': [], 'map_pins': []}), 200

    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cur = conn.cursor()
        now = time.time()

        # Count devices by time window
        cur.execute('SELECT COUNT(*) FROM devices WHERE last_time > ?', (now - 300,))
        traffic_5m = cur.fetchone()[0]

        cur.execute('SELECT COUNT(*) FROM devices WHERE last_time > ?', (now - 900,))
        traffic_15m = cur.fetchone()[0]

        # Check for drone OUIs (DJI, Parrot, 3DR, Autel, Yuneec)
        drone_ouis = ['60:60:1F', '34:D2:62', '90:03:B7', '00:1C:27', '00:12:1C',
                      'A0:14:3D', '60:60:1F', '88:28:B3']
        drone_count = 0
        drone_list = []
        for oui in drone_ouis:
            cur.execute('SELECT devmac FROM devices WHERE UPPER(devmac) LIKE ?',
                       (oui.upper() + '%',))
            for row in cur.fetchall():
                drone_list.append(row[0])
                drone_count += 1

        # Get close contacts (strong signal > -60 dBm)
        cur.execute('''SELECT devmac, strongest_signal FROM devices
                      WHERE strongest_signal > -60 AND strongest_signal != 0 AND last_time > ?
                      ORDER BY strongest_signal DESC LIMIT 50''', (now - 300,))
        pins = [{'id': row[0], 'signal': row[1]} for row in cur.fetchall()]

        # If no strong signals, get recent devices anyway
        if not pins:
            cur.execute('''SELECT devmac, strongest_signal FROM devices
                          WHERE last_time > ? ORDER BY last_time DESC LIMIT 50''', (now - 300,))
            pins = [{'id': row[0], 'signal': row[1]} for row in cur.fetchall()]

        # Determine alert level
        # Threshold: 300 devices/5min (residential baseline ~200)
        alert_level = 'GREEN'
        if drone_count > 0:
            alert_level = 'RED'
        elif traffic_5m > 300:
            alert_level = 'YELLOW'

        conn.close()

        return jsonify({
            'alert_level': alert_level,
            'traffic_5m': traffic_5m,
            'traffic_15m': traffic_15m,
            'drones_detected': drone_count,
            'drone_list': drone_list,
            'map_pins': pins
        })
    except Exception as e:
        logger.error(f'Status error: {e}')
        return jsonify({'error': str(e), 'alert_level': 'GREEN',
                       'traffic_5m': 0, 'traffic_15m': 0, 'drones_detected': 0,
                       'drone_list': [], 'map_pins': []}), 200

@app.route('/targets')
@require_api_key
def targets():
    db_path = get_latest_db()
    if not db_path:
        return jsonify({'stalker_count': 0, 'stalker_macs': []})

    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cur = conn.cursor()
        now = time.time()

        # Devices seen 15-20 mins ago
        cur.execute('SELECT devmac FROM devices WHERE last_time BETWEEN ? AND ?',
                   (now - 1200, now - 900))
        old_devices = set(row[0] for row in cur.fetchall())

        # Devices seen in last 5 mins
        cur.execute('SELECT devmac FROM devices WHERE last_time > ?', (now - 300,))
        recent_devices = set(row[0] for row in cur.fetchall())

        stalkers = list(old_devices.intersection(recent_devices))
        conn.close()

        return jsonify({
            'stalker_count': len(stalkers),
            'stalker_macs': stalkers
        })
    except Exception as e:
        logger.error(f'Targets error: {e}')
        return jsonify({'stalker_count': 0, 'stalker_macs': []})

@app.route('/health')
def health():
    db_path = get_latest_db()
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'database': db_path,
        'kismet_logs_dir': KISMET_LOGS_DIR
    })

if __name__ == '__main__':
    print(f'CYT API Server with CORS')
    print(f'Kismet logs: {KISMET_LOGS_DIR}')
    print(f'Starting on 0.0.0.0:3000')
    app.run(host='0.0.0.0', port=3000, debug=False)
