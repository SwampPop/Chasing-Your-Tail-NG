#!/usr/bin/env python3
"""
Spiderweb Core Receiver (Tier 3)
Listens for UDP packets from remote sensors and injects them into the database.
Acts as a central aggregation point for distributed surveillance.
"""
import socket
import json
import sqlite3
import time
import logging
import os

# Configuration
LISTEN_IP = "0.0.0.0" # Listen on all interfaces
LISTEN_PORT = 5555
DB_PATH = "spiderweb.kismet" # Dedicated DB for remote sensors

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database schema if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Schema matches Kismet/CYT standard
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            first_time int,
            last_time int,
            devmac text,
            type text,
            device text,
            min_lat real,
            min_lon real,
            max_lat real,
            max_lon real
        )
    """)
    conn.commit()
    return conn

def construct_kismet_json(mac, ssid, rssi, sensor_id):
    """Recreate the complex Kismet JSON structure so the analyzer can read it"""
    return json.dumps({
        "kismet.device.base.macaddr": mac,
        "kismet.device.base.manuf": "Remote-Capture",
        "kismet.device.base.name": f"Remote-{sensor_id}",
        "kismet.device.base.signal": {
            "kismet.common.signal.last_signal": rssi
        },
        "dot11.device": {
            "dot11.device.probed_ssid_map": [
                {
                    "dot11.probedssid.ssid": ssid,
                    "dot11.probedssid.last_time": int(time.time())
                }
            ],
            "dot11.device.last_probed_ssid_record": {
                "dot11.probedssid.ssid": ssid
            }
        }
    })

def main():
    logger.info(f"🕸️ Spiderweb Core Active. Listening on {LISTEN_IP}:{LISTEN_PORT}")
    logger.info(f"📝 Writing to database: {DB_PATH}")
    
    # Setup Networking
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    
    # Setup Database
    conn = init_db()
    cursor = conn.cursor()
    
    try:
        while True:
            # Wait for data from any Spider Sensor
            data, addr = sock.recvfrom(4096)
            try:
                payload = json.loads(data.decode('utf-8'))
                
                # Extract fields
                sensor = payload.get("sensor", "Unknown")
                mac = payload.get("mac")
                ssid = payload.get("ssid")
                rssi = payload.get("rssi")
                ts = int(payload.get("ts", time.time()))
                
                if not mac or not ssid: continue

                # Log to console so you see the hit
                logger.info(f"[{sensor}] {mac} -> {ssid} ({rssi}dBm)")
                
                # Build Kismet-compatible JSON blob
                device_json = construct_kismet_json(mac, ssid, rssi, sensor)
                
                # Insert into DB
                cursor.execute("""
                    INSERT INTO devices 
                    (first_time, last_time, devmac, type, device, min_lat, min_lon, max_lat, max_lon)
                    VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0)
                """, (ts, ts, mac, "Wi-Fi Client", device_json))
                
                conn.commit()
                
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from {addr}")
            except Exception as e:
                logger.error(f"Error processing packet: {e}")
                
    except KeyboardInterrupt:
        logger.info("Shutting down Spiderweb Core...")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
