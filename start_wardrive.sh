#!/bin/bash
# CYT Wardriving Startup Script - macOS
# Configures macOS and VM for lid-closed wardriving
# Run this on macOS BEFORE closing the lid

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CYT WARDRIVE STARTUP SCRIPT                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ============================================
# STEP 1: Prevent macOS sleep (lid-closed mode)
# ============================================
echo -e "${BLUE}▶ Step 1: Configuring macOS for lid-closed operation...${NC}"

# Kill any existing caffeinate from previous runs
pkill -f "caffeinate.*wardrive" 2>/dev/null || true

# Disable system sleep via pmset (requires sudo)
echo "   Disabling system sleep (requires password)..."
sudo pmset -a disablesleep 1
echo -e "${GREEN}   ✓${NC} System sleep disabled"

# Also prevent display sleep assertions
sudo pmset -a displaysleep 0
echo -e "${GREEN}   ✓${NC} Display sleep disabled"

# ============================================
# STEP 2: Check/Start gpsd on macOS
# ============================================
echo ""
echo -e "${BLUE}▶ Step 2: Checking GPS daemon on macOS...${NC}"

GPS_DEVICE="/dev/cu.usbmodem1401"

# Check for GPS device
if [ ! -c "$GPS_DEVICE" ]; then
    # Try to find alternate device
    ALT_DEVICE=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
    if [ -n "$ALT_DEVICE" ]; then
        GPS_DEVICE="$ALT_DEVICE"
        echo -e "${YELLOW}   ⚠${NC} Using alternate device: $GPS_DEVICE"
    else
        echo -e "${RED}   ✗${NC} GPS device not found!"
        echo "      Make sure GPS is connected to macOS (not VM)"
        echo "      In Parallels: Devices → USB → u-blox → Disconnect from VM"
    fi
fi

if pgrep gpsd > /dev/null; then
    echo -e "${GREEN}   ✓${NC} gpsd already running"
else
    if [ -c "$GPS_DEVICE" ]; then
        echo "   Starting gpsd on $GPS_DEVICE..."
        sudo /opt/homebrew/opt/gpsd/sbin/gpsd -n -G "$GPS_DEVICE"
        sleep 2
        if pgrep gpsd > /dev/null; then
            echo -e "${GREEN}   ✓${NC} gpsd started (serving on port 2947)"
        else
            echo -e "${RED}   ✗${NC} Failed to start gpsd"
        fi
    fi
fi

# Test GPS fix
echo -n "   GPS status: "
GPS_DATA=$(/opt/homebrew/bin/gpspipe -w -n 5 2>/dev/null | grep TPV | tail -1)
if [ -n "$GPS_DATA" ]; then
    GPS_MODE=$(echo "$GPS_DATA" | grep -o '"mode":[0-9]' | grep -o '[0-9]')
    GPS_LAT=$(echo "$GPS_DATA" | grep -o '"lat":[0-9.-]*' | cut -d: -f2)
    GPS_LON=$(echo "$GPS_DATA" | grep -o '"lon":[0-9.-]*' | cut -d: -f2)
    case $GPS_MODE in
        3) echo -e "${GREEN}3D fix${NC} (${GPS_LAT}°N, ${GPS_LON}°W)" ;;
        2) echo -e "${YELLOW}2D fix${NC} (${GPS_LAT}°N, ${GPS_LON}°W)" ;;
        1) echo -e "${YELLOW}No fix yet - acquiring satellites${NC}" ;;
        *) echo -e "${YELLOW}Initializing...${NC}" ;;
    esac
else
    echo -e "${RED}No GPS data received${NC}"
fi

# ============================================
# STEP 3: Check VM status
# ============================================
echo ""
echo -e "${BLUE}▶ Step 3: Checking Kali VM...${NC}"

VM_STATUS=$(prlctl list -a 2>/dev/null | grep CYT-Kali | awk '{print $2}')
if [ "$VM_STATUS" = "running" ]; then
    echo -e "${GREEN}   ✓${NC} CYT-Kali VM is running"
else
    echo -e "${YELLOW}   ⚠${NC} CYT-Kali VM is $VM_STATUS - starting..."
    prlctl start CYT-Kali
    echo "   Waiting for VM to boot..."
    sleep 15
fi

# ============================================
# STEP 4: Check/Start Kismet in VM
# ============================================
echo ""
echo -e "${BLUE}▶ Step 4: Checking Kismet in VM...${NC}"

KISMET_PID=$(prlctl exec CYT-Kali "pgrep -x kismet" 2>/dev/null || true)
if [ -n "$KISMET_PID" ]; then
    echo -e "${GREEN}   ✓${NC} Kismet is running (PID: $KISMET_PID)"
else
    echo "   Starting Kismet..."
    prlctl exec CYT-Kali "sudo /usr/bin/kismet -c wlan0 --daemonize" 2>/dev/null
    sleep 5
    KISMET_PID=$(prlctl exec CYT-Kali "pgrep -x kismet" 2>/dev/null || true)
    if [ -n "$KISMET_PID" ]; then
        echo -e "${GREEN}   ✓${NC} Kismet started (PID: $KISMET_PID)"
    else
        echo -e "${RED}   ✗${NC} Failed to start Kismet"
    fi
fi

# Check Kismet GPS (connecting to macOS gpsd)
echo -n "   Kismet GPS: "
sleep 2
KISMET_GPS=$(prlctl exec CYT-Kali "curl -s --user kismet:cyt2026 'http://localhost:2501/gps/location.json'" 2>/dev/null)
KISMET_FIX=$(echo "$KISMET_GPS" | grep -o '"kismet.common.location.fix":[0-9]*' | grep -o '[0-9]*' || echo "0")
KISMET_LAT=$(echo "$KISMET_GPS" | grep -o '"kismet.common.location.geopoint":\[[0-9.-]*,[0-9.-]*\]' | grep -o '\[[^]]*\]' || echo "[0,0]")

if [ "$KISMET_FIX" = "3" ]; then
    echo -e "${GREEN}3D fix${NC} $KISMET_LAT"
elif [ "$KISMET_FIX" = "2" ]; then
    echo -e "${YELLOW}2D fix${NC} $KISMET_LAT"
else
    echo -e "${YELLOW}Acquiring (fix: $KISMET_FIX)${NC}"
fi

# ============================================
# STEP 5: Check WiFi adapter
# ============================================
echo ""
echo -e "${BLUE}▶ Step 5: Checking WiFi adapter in VM...${NC}"

WIFI_INFO=$(prlctl exec CYT-Kali "iwconfig wlan0 2>/dev/null" || true)
WIFI_MODE=$(echo "$WIFI_INFO" | grep -o "Mode:[A-Za-z]*" | cut -d: -f2)
WIFI_FREQ=$(echo "$WIFI_INFO" | grep -o "Frequency:[0-9.]*" | cut -d: -f2)

if [ "$WIFI_MODE" = "Monitor" ]; then
    echo -e "${GREEN}   ✓${NC} WiFi adapter in Monitor mode (${WIFI_FREQ} GHz)"
else
    echo -e "${RED}   ✗${NC} WiFi adapter mode: $WIFI_MODE (should be Monitor)"
    echo "      Run in VM: sudo airmon-ng start wlan0"
fi

# ============================================
# STEP 6: Start caffeinate in background
# ============================================
echo ""
echo -e "${BLUE}▶ Step 6: Starting background keep-awake...${NC}"

# Create a marker file so we can track this session
WARDRIVE_SESSION="/tmp/cyt_wardrive_session_$$"
touch "$WARDRIVE_SESSION"

# Start caffeinate that will keep running
nohup caffeinate -dimsu -w $$ > /dev/null 2>&1 &
CAFFEINATE_PID=$!
echo $CAFFEINATE_PID > /tmp/cyt_caffeinate.pid
echo -e "${GREEN}   ✓${NC} Caffeinate running (PID: $CAFFEINATE_PID)"

# ============================================
# SUMMARY
# ============================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  ${GREEN}WARDRIVE READY${NC}                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  ${GREEN}✓${NC} macOS sleep disabled (lid can be closed)"
echo "  ${GREEN}✓${NC} GPS running on macOS → VM via network"
echo "  ${GREEN}✓${NC} Kismet capturing WiFi networks"
echo ""
echo "  ${BLUE}You can now close the laptop lid and go wardriving!${NC}"
echo ""
echo "  When done, run:"
echo "    ${YELLOW}./stop_wardrive.sh${NC}"
echo ""
echo "  Kismet Web UI (while lid open):"
echo "    http://localhost:2501 (in VM)"
echo ""
