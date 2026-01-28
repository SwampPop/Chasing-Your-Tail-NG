#!/bin/bash
# Wardriving Startup Script for CYT
# Run this in the VM before heading out

set -e

echo "========================================"
echo "  CYT Wardriving Setup"
echo "========================================"

# Check GPS device
if [ ! -c /dev/ttyACM0 ]; then
    echo "ERROR: GPS device not found at /dev/ttyACM0"
    echo "  1. Unplug GPS USB"
    echo "  2. Plug back in"
    echo "  3. Parallels menu: Devices → USB → u-blox → Connect"
    exit 1
fi

# Start gpsd
echo "[1/4] Starting GPS daemon..."
sudo killall gpsd 2>/dev/null || true
sudo gpsd /dev/ttyACM0 -n
sleep 2

# Verify GPS fix
echo "[2/4] Checking GPS fix..."
GPS_CHECK=$(gpspipe -w -n 5 2>/dev/null | grep -c '"mode":3' || echo "0")
if [ "$GPS_CHECK" -gt 0 ]; then
    echo "  ✓ GPS has 3D fix"
else
    echo "  ⚠ GPS acquiring satellites (may take 1-2 minutes outdoors)"
    echo "    You can start driving - fix will come"
fi

# Check Kismet
echo "[3/4] Checking Kismet..."
if pgrep -x kismet > /dev/null; then
    echo "  ✓ Kismet running (PID $(pgrep -x kismet))"
else
    echo "  Starting Kismet..."
    cd /home/parallels/CYT/logs/kismet
    kismet -c wlan0 --daemonize
    sleep 3
    echo "  ✓ Kismet started"
fi

# Show status
echo "[4/4] Status Check..."
echo ""
echo "========================================"
echo "  WARDRIVING READY"
echo "========================================"
echo ""
echo "GPS:    $(gpspipe -w -n 1 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"lat\",\"acquiring\")}°N, {d.get(\"lon\",\"acquiring\")}°W') if 'lat' in d else print('Acquiring...')" 2>/dev/null || echo 'Acquiring satellites...')"
echo "Kismet: http://localhost:2501"
echo "DB:     $(ls -t /home/parallels/CYT/logs/kismet/*.kismet 2>/dev/null | head -1)"
echo ""
echo "Tips:"
echo "  - GPS works best with clear sky view"
echo "  - Keep laptop lid open (antenna needs exposure)"
echo "  - No internet needed while driving"
echo "  - Data saves automatically every 30 seconds"
echo ""
echo "When done:"
echo "  - Networks with GPS stored in Kismet database"
echo "  - Export for WiGLE: python3 my_wigle_export.py"
echo ""
