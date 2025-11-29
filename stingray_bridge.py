#!/usr/bin/env python3
"""
Stingray Bridge (RayHunter Integration)
Connects to an external RayHunter device (Orbic Hotspot) via USB/Network.
Polls for IMSI Catcher alerts and forwards them to the CYT Alert System.
"""
import requests
import time
import logging
import json
from datetime import datetime
from alert_manager import AlertManager

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# RayHunter API Endpoint (Default for USB Tethering)
RAYHUNTER_URL = "http://192.168.225.1:8080/api/v1/status" 

class StingrayBridge:
    def __init__(self):
        self.alerter = AlertManager()
        self.last_alert_time = 0
        self.cooldown = 60  # Seconds between alerts to avoid spamming

    def check_rayhunter(self):
        try:
            # Ask the Orbic hotspot for status
            response = requests.get(RAYHUNTER_URL, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse the Threat Level
                # RayHunter usually returns 'events' or 'pawn_status'
                # Note: This JSON structure depends on specific RayHunter version
                threat_detected = data.get("threat_detected", False)
                events = data.get("events", [])
                
                if threat_detected or len(events) > 0:
                    self.trigger_alert(data)
                else:
                    # Optional: Log heartbeat
                    # logger.debug("Cellular Spectrum Clean")
                    pass
                    
        except requests.exceptions.ConnectionError:
            # This is normal if the device isn't plugged in yet
            # logger.debug("RayHunter device not connected.")
            pass
        except Exception as e:
            logger.error(f"Bridge Error: {e}")

    def trigger_alert(self, data):
        now = time.time()
        if now - self.last_alert_time > self.cooldown:
            
            description = "IMSI Catcher Detected"
            details = data.get("current_cell", {}).get("desc", "Unknown Tower")
            
            # 1. Console Log
            print(f"\033[91m[!!!] STINGRAY DETECTED [!!!]\n   Details: {details}\033[0m")
            
            # 2. Phone/Audio Alert
            msg = f"🚨 CELLULAR THREAT: {description}\nDetails: {details}"
            self.alerter.send_alert(msg)
            
            self.last_alert_time = now

    def run(self):
        logger.info("Stingray Bridge Active. Waiting for RayHunter device...")
        logger.info(f"Polling: {RAYHUNTER_URL}")
        
        try:
            while True:
                self.check_rayhunter()
                time.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            logger.info("Stopping Bridge...")

if __name__ == "__main__":
    bridge = StingrayBridge()
    bridge.run()
