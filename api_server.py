#!/usr/bin/env python3
"""
CYT API Server (Phase 4)
Provides a REST API for mobile apps (iPhone) to query the system status.

SECURITY: Requires API key authentication via X-API-Key header.
Generate key: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
Set environment variable: export CYT_API_KEY="your_generated_key"
"""
import logging
import time
import json
import os
from functools import wraps
from flask import Flask, jsonify, request
from secure_database import SecureKismetDB
from secure_credentials import secure_config_loader
from secure_main_logic import SecureCYTMonitor

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Config
config, _ = secure_config_loader('config.json')

# API Key Authentication
def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.getenv('CYT_API_KEY')

        if not expected_key:
            logger.error("CYT_API_KEY environment variable not set!")
            return jsonify({"error": "Server configuration error - API key not configured"}), 500

        if not api_key:
            logger.warning(f"API request without key from {request.remote_addr}")
            return jsonify({"error": "API key required. Set X-API-Key header"}), 401

        if api_key != expected_key:
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({"error": "Invalid API key"}), 403

        return f(*args, **kwargs)
    return decorated_function

# Helper to find the latest DB
def get_latest_db():
    db_pattern = config['paths']['kismet_logs']
    if os.path.isdir(db_pattern):
        db_pattern = os.path.join(db_pattern, "*.kismet")
    
    import glob
    files = glob.glob(db_pattern)
    # Filter out directories just in case
    files = [f for f in files if os.path.isfile(f)]
    
    if not files:
        if os.path.exists("test_capture.kismet"):
            return "test_capture.kismet"
        if os.path.exists("spiderweb.kismet"):
            return "spiderweb.kismet"
        return None
    return max(files, key=os.path.getctime)

@app.route('/')
def index():
    """Health Check - Public endpoint"""
    return jsonify({
        "system": "Chasing Your Tail NG",
        "status": "Online",
        "version": "2.3-API",
        "auth_required": True
    })

@app.route('/status')
@require_api_key
def get_status():
    db_path = get_latest_db()
    if not db_path:
        return jsonify({"error": "No Database Found"}), 500

    try:
        with SecureKismetDB(db_path) as db:
            now = time.time()
            
            # 1. Check for Drones (Last 60 seconds)
            recent_devices = db.get_devices_by_time_range(now - 60, now)
            drones = []
            threat_pins = [] # New list for Map Pins
            
            DRONE_OUI_PREFIXES = ["60:60:1F", "34:D2:62", "90:03:B7", "00:1C:27"] 
            
            for dev in recent_devices:
                mac = dev['mac'].upper()
                lat = dev.get('lat', 0.0)
                lon = dev.get('lon', 0.0)
                
                # Identify Drones
                if any(mac.startswith(prefix) for prefix in DRONE_OUI_PREFIXES):
                    drones.append(mac)
                    # Add to map pins
                    threat_pins.append({
                        "id": mac,
                        "lat": lat,
                        "lon": lon,
                        "type": "DRONE"
                    })
                
                # Identify Stalkers (Simplification for demo: any signal > -50dBm is "Close")
                # In real version, link this to persistence logic
                try:
                    rssi = dev['device_data']['kismet.device.base.signal']['kismet.common.signal.last_signal']
                    if rssi > -50: 
                        threat_pins.append({
                            "id": mac,
                            "lat": lat,
                            "lon": lon,
                            "type": "CLOSE_CONTACT"
                        })
                except:
                    pass

            # 2. Activity Counts
            count_5m = len(db.get_mac_addresses_by_time_range(now - 300, now))
            count_15m = len(db.get_mac_addresses_by_time_range(now - 900, now))

            status_color = "GREEN"
            if drones: status_color = "RED"
            elif count_5m > 50: status_color = "YELLOW"

            return jsonify({
                "alert_level": status_color,
                "drones_detected": len(drones),
                "drone_list": drones,
                "traffic_5m": count_5m,
                "traffic_15m": count_15m,
                "map_pins": threat_pins  # <--- The new data field
            })

    except Exception as e:
        logger.error(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/targets')
@require_api_key
def get_targets():
    """
    Returns specific persistent targets (The 'Stalkers').
    Note: This is a simplified check for the API demo.
    Requires authentication via X-API-Key header.
    """
    # For Phase 4 demo, we'll just return raw count of 'old' devices
    # In Phase 5, we connect this to the actual persistence engine results
    db_path = get_latest_db()
    if not db_path: return jsonify({"error": "No DB"}), 500
    
    with SecureKismetDB(db_path) as db:
        now = time.time()
        # Devices seen 20 mins ago AND 5 mins ago
        old = set(db.get_mac_addresses_by_time_range(now - 1200, now - 900)) # 15-20m ago
        recent = set(db.get_mac_addresses_by_time_range(now - 300, now))    # 0-5m ago
        
        stalkers = list(old.intersection(recent))
        
        return jsonify({
            "stalker_count": len(stalkers),
            "stalker_macs": stalkers
        })

if __name__ == "__main__":
    # Host='0.0.0.0' makes it accessible to other devices on your Wi-Fi (like your iPhone)
    app.run(host='100.103.210.110', port=8080, debug=True)
