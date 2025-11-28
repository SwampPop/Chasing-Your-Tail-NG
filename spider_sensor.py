#!/usr/bin/env python3
"""
Spiderweb Sensor Node (Tier 3)
Lightweight Packet Capture & Forwarding.
Runs on: Raspberry Pi Zero 2 W
"""
import time
import json
import socket
import logging
from scapy.all import sniff, Dot11ProbeReq

# Configuration
CORE_IP = "192.168.1.50"  # REPLACE with your Mac/Pi 5 IP Address
CORE_PORT = 5555
SENSOR_ID = "Garage_Sensor"

# Networking
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def packet_handler(pkt):
    if pkt.haslayer(Dot11ProbeReq):
        try:
            # Extract Data
            mac = pkt.addr2
            ssid = pkt.info.decode('utf-8', 'ignore')
            rssi = pkt.dBm_AntSignal if hasattr(pkt, 'dBm_AntSignal') else -100

            if not ssid:
                return  # Ignore hidden probes

            # Build Payload
            payload = {
                "sensor": SENSOR_ID,
                "mac": mac,
                "ssid": ssid,
                "rssi": rssi,
                "ts": time.time()
            }

            # Send to Core
            message = json.dumps(payload).encode('utf-8')
            sock.sendto(message, (CORE_IP, CORE_PORT))

            # Local log (optional, disable to save SD card)
            # logging.info(f"Forwarded: {mac} -> {ssid} ({rssi}dBm)")

        except Exception:
            pass


def main():
    print(f"🕷️ Spider Sensor '{SENSOR_ID}' Active.")
    print(f"📡 Forwarding Probes to {CORE_IP}:{CORE_PORT}")

    # Note: Interface must be in Monitor Mode before running!
    # Usually: 'wlan1' for external Alfa card
    try:
        sniff(iface="wlan1", prn=packet_handler, store=0)
    except Exception as e:
        print(f"Error: {e}")
        print("Did you enable Monitor Mode? (airmon-ng start wlan1)")


if __name__ == "__main__":
    main()
