#!/usr/bin/env python3
"""
Test Data Generator for Chasing Your Tail
Creates a valid Kismet-style SQLite database with:
1. A "Stalker" device (follows you across time)
2. A DJI Drone (to trigger Red Alerts)
3. Random background noise
"""

import sqlite3
import json
import time
import random
import os

# Configuration
DB_NAME = "test_capture.kismet"
NUM_NOISE_DEVICES = 50

# MAC Addresses
DRONE_MAC = "60:60:1F:AA:BB:CC"  # DJI Prefix
STALKER_MAC = "00:11:22:33:44:55" # Generic Stalker
PHONE_MAC = "A8:BB:CC:DD:EE:FF"   # Random iPhone

def create_schema(cursor):
    # Create the table structure Kismet uses
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

def generate_device_json(mac, ssid, manuf, signal):
    """Create the nested JSON structure Kismet uses"""
    return json.dumps({
        "kismet.device.base.macaddr": mac,
        "kismet.device.base.manuf": manuf,
        "kismet.device.base.signal": {
            "kismet.common.signal.last_signal": signal
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

def insert_device(cursor, mac, type, manuf, ssid, lat, lon, time_offset=0):
    ts = int(time.time()) - time_offset
    json_data = generate_device_json(mac, ssid, manuf, -50)
    
    cursor.execute("""
        INSERT INTO devices 
        (first_time, last_time, devmac, type, device, min_lat, min_lon, max_lat, max_lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, ts, mac, type, json_data, lat, lon, lat, lon))

def main():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Removed old {DB_NAME}")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    create_schema(c)

    print("Generating Data...")

    # 1. Inject DRONE (The Threat)
    # DJI OUI: 60:60:1F
    print(f"-> Injecting DJI Drone ({DRONE_MAC})...")
    insert_device(c, DRONE_MAC, "Wi-Fi AP", "DJI Technology", "Drone-Video-Feed", 29.9511, -90.0715)

    # 2. Inject STALKER (Persistence)
    # We inject this device multiple times at different timestamps/locations
    print(f"-> Injecting Stalker ({STALKER_MAC}) following you...")
    # 10 mins ago
    insert_device(c, STALKER_MAC, "Wi-Fi Client", "Google", "Home_WiFi", 29.9520, -90.0720, 600)
    # 5 mins ago
    insert_device(c, STALKER_MAC, "Wi-Fi Client", "Google", "Home_WiFi", 29.9530, -90.0730, 300)
    # Now
    insert_device(c, STALKER_MAC, "Wi-Fi Client", "Google", "Home_WiFi", 29.9540, -90.0740, 0)

    # 3. Inject Noise
    print(f"-> Injecting {NUM_NOISE_DEVICES} random devices...")
    for i in range(NUM_NOISE_DEVICES):
        mac = f"02:00:00:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}"
        ssid = random.choice(["Starbucks", "Xfinity", "Marriott_Guest", "iPhone"])
        insert_device(c, mac, "Wi-Fi Client", "Unknown", ssid, 29.95 + (i*0.001), -90.07 + (i*0.001))

    conn.commit()
    conn.close()
    print(f"\n[SUCCESS] Created {DB_NAME} with fake surveillance data.")
    print(f"Run this command to test: python3 probe_analyzer.py --local --db {DB_NAME}")

if __name__ == "__main__":
    main()
