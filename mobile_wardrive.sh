#!/bin/bash
# Mobile Wardriving Setup Script
# Starts Kismet with GPS integration for WiFi/BLE mapping
#
# Requirements:
# - USB GPS receiver (e.g., GlobalSat BU-353S4)
# - gpsd installed (sudo apt install gpsd gpsd-clients)
# - WiFi adapter in monitor mode

set -e  # Exit on error

# Configuration
WIFI_INTERFACE="wlan0mon"
GPS_DEVICE="/dev/ttyUSB0"  # Adjust for your GPS receiver
KISMET_LOG_DIR="./wardrive_logs"
SESSION_NAME="wardrive_$(date +%Y%m%d_%H%M%S)"

echo "[*] Mobile Wardriving Setup"
echo "================================"

# Check if running as root (required for Kismet)
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] This script must be run as root (sudo)"
   exit 1
fi

# Create log directory
mkdir -p "$KISMET_LOG_DIR"
echo "[+] Log directory: $KISMET_LOG_DIR"

# Step 1: Set up WiFi adapter in monitor mode
echo "[*] Setting up WiFi adapter..."
if ! ip link show "$WIFI_INTERFACE" &> /dev/null; then
    echo "[*] Monitor interface not found. Creating..."

    # Kill interfering processes
    airmon-ng check kill &> /dev/null || true

    # Enable monitor mode
    BASE_INTERFACE="${WIFI_INTERFACE%mon}"  # Remove 'mon' suffix
    airmon-ng start "$BASE_INTERFACE"

    echo "[+] Monitor mode enabled: $WIFI_INTERFACE"
else
    echo "[+] Monitor interface already exists: $WIFI_INTERFACE"
fi

# Step 2: Set up GPS daemon
echo "[*] Starting GPS daemon..."

# Stop existing gpsd instances
killall gpsd 2>/dev/null || true
sleep 1

# Start gpsd with GPS device
gpsd -n -N -D 2 "$GPS_DEVICE"
sleep 2

# Verify GPS is working
echo "[*] Waiting for GPS fix (this may take 30-60 seconds)..."
timeout 60s gpspipe -w -n 10 > /dev/null 2>&1 || {
    echo "[WARN] GPS fix not acquired. Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "[*] Aborted by user."
        exit 1
    fi
}

# Check GPS status
gpsmon -n 5 &
GPS_PID=$!
sleep 2
kill $GPS_PID 2>/dev/null || true

echo "[+] GPS daemon running on $GPS_DEVICE"

# Step 3: Start Kismet with GPS integration
echo "[*] Starting Kismet..."

# Create Kismet config override for this session
cat > /tmp/kismet_wardrive.conf <<EOF
# Wardriving session configuration
server_name=Wardrive_${SESSION_NAME}
logprefix=${KISMET_LOG_DIR}/${SESSION_NAME}

# GPS configuration
gps=gpsd:host=localhost,port=2947
gps_reconnect=true

# Data sources (WiFi adapter)
source=${WIFI_INTERFACE}:name=wardrive_wifi

# Logging
log_types=kismet,pcapng,gpsxml
log_title=${SESSION_NAME}

# Performance tuning (for mobile operation)
keep_location_cloud_history=true
keep_per_device_location_history=true
alertbacklog=50
EOF

# Start Kismet with custom config
kismet -c "${WIFI_INTERFACE}" --override /tmp/kismet_wardrive.conf &
KISMET_PID=$!

echo "[+] Kismet started (PID: $KISMET_PID)"
echo "[+] Access Web UI: http://localhost:2501"

# Step 4: Monitor session
echo ""
echo "================================"
echo "Wardriving Session Active"
echo "================================"
echo "Session: $SESSION_NAME"
echo "Logs: $KISMET_LOG_DIR"
echo "GPS: $GPS_DEVICE"
echo "WiFi: $WIFI_INTERFACE"
echo ""
echo "Press Ctrl+C to stop session"
echo "================================"

# Trap Ctrl+C to cleanly shut down
trap cleanup INT

cleanup() {
    echo ""
    echo "[*] Stopping wardriving session..."

    # Stop Kismet
    echo "[*] Stopping Kismet..."
    kill $KISMET_PID 2>/dev/null || true
    sleep 2

    # Stop GPS daemon
    echo "[*] Stopping GPS daemon..."
    killall gpsd 2>/dev/null || true

    # Disable monitor mode (optional)
    # airmon-ng stop "$WIFI_INTERFACE"

    # Clean up temp config
    rm -f /tmp/kismet_wardrive.conf

    echo "[+] Session data saved to: $KISMET_LOG_DIR"
    echo "[+] Process with CYT:"
    echo "    python3 surveillance_analyzer.py --db ${KISMET_LOG_DIR}/${SESSION_NAME}-1.kismet"

    exit 0
}

# Wait indefinitely (until Ctrl+C)
wait $KISMET_PID
