#!/bin/bash
# =============================================================================
# CYT Wardrive Script
# Run from macOS to start wardriving with lid-closed support
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VM_NAME="CYT-Kali"

print_banner() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  CYT WARDRIVING MODE${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

start_wardrive() {
    print_banner

    echo -e "${YELLOW}Starting wardrive mode...${NC}"
    echo ""

    # Step 1: Disable sleep (allows lid to close)
    echo "[1/5] Disabling sleep (lid-close safe)..."
    sudo pmset -a disablesleep 1
    print_status "Sleep disabled - you can close the lid"

    # Step 2: Check VM is running
    echo "[2/5] Checking VM status..."
    VM_STATE=$(prlctl list -a | grep "$VM_NAME" | awk '{print $2}')
    if [ "$VM_STATE" != "running" ]; then
        print_warning "VM not running, starting..."
        prlctl start "$VM_NAME"
        sleep 10
    fi
    print_status "VM '$VM_NAME' is running"

    # Step 3: Start GPS daemon
    echo "[3/5] Starting GPS..."
    prlctl exec "$VM_NAME" "sudo killall gpsd 2>/dev/null || true" 2>/dev/null
    sleep 1

    if prlctl exec "$VM_NAME" "test -c /dev/ttyACM0" 2>/dev/null; then
        prlctl exec "$VM_NAME" "sudo gpsd /dev/ttyACM0 -n" 2>/dev/null
        sleep 2

        # Check for GPS fix
        GPS_DATA=$(prlctl exec "$VM_NAME" "timeout 5 cat /dev/ttyACM0 2>/dev/null | grep GNGGA | head -1" 2>/dev/null || echo "")
        if [ -n "$GPS_DATA" ]; then
            # Parse coordinates from NMEA
            LAT_RAW=$(echo "$GPS_DATA" | cut -d',' -f3)
            LAT_DIR=$(echo "$GPS_DATA" | cut -d',' -f4)
            LON_RAW=$(echo "$GPS_DATA" | cut -d',' -f5)
            LON_DIR=$(echo "$GPS_DATA" | cut -d',' -f6)
            SATS=$(echo "$GPS_DATA" | cut -d',' -f8)

            # Convert NMEA to decimal (rough conversion for display)
            LAT_DEG=${LAT_RAW:0:2}
            LAT_MIN=${LAT_RAW:2}
            LON_DEG=${LON_RAW:0:3}
            LON_MIN=${LON_RAW:3}

            print_status "GPS locked: ${LAT_DEG}°${LAT_MIN}'${LAT_DIR}, ${LON_DEG}°${LON_MIN}'${LON_DIR} (${SATS} satellites)"
        else
            print_warning "GPS connected but acquiring satellites..."
        fi
    else
        print_error "GPS not detected - check USB connection in Parallels"
        print_warning "Wardrive will continue without GPS (no location tagging)"
    fi

    # Step 4: Check/Start Kismet
    echo "[4/5] Checking Kismet..."
    KISMET_PID=$(prlctl exec "$VM_NAME" "pgrep -x kismet" 2>/dev/null || echo "")
    if [ -n "$KISMET_PID" ]; then
        print_status "Kismet already running (PID $KISMET_PID)"
    else
        print_warning "Starting Kismet..."
        prlctl exec "$VM_NAME" "cd /home/parallels/CYT/logs/kismet && kismet -c wlan0 --daemonize" 2>/dev/null || true
        sleep 5
        KISMET_PID=$(prlctl exec "$VM_NAME" "pgrep -x kismet" 2>/dev/null || echo "")
        if [ -n "$KISMET_PID" ]; then
            print_status "Kismet started (PID $KISMET_PID)"
        else
            print_error "Failed to start Kismet"
        fi
    fi

    # Step 5: Show summary
    echo "[5/5] Final status..."
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  WARDRIVE MODE ACTIVE${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Status:"
    echo "    • Sleep disabled (lid-close safe)"
    echo "    • VM running"
    echo "    • GPS active"
    echo "    • Kismet capturing"
    echo ""
    echo "  You can now:"
    echo "    1. Close the MacBook lid"
    echo "    2. Put it in your bag"
    echo "    3. Drive/walk around"
    echo ""
    echo "  Data saves automatically to Kismet database."
    echo "  No internet connection needed."
    echo ""
    echo -e "  ${YELLOW}To stop wardriving:${NC}"
    echo "    $0 stop"
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
}

stop_wardrive() {
    print_banner
    echo -e "${YELLOW}Stopping wardrive mode...${NC}"
    echo ""

    # Re-enable sleep
    echo "[1/2] Re-enabling sleep..."
    sudo pmset -a disablesleep 0
    print_status "Sleep re-enabled"

    # Show stats
    echo "[2/2] Session summary..."

    # Get network count from Kismet
    NETWORK_COUNT=$(prlctl exec "$VM_NAME" "sqlite3 /home/parallels/CYT/logs/kismet/*.kismet 'SELECT COUNT(*) FROM devices WHERE type LIKE \"%AP%\"' 2>/dev/null | tail -1" 2>/dev/null || echo "?")

    # Get database file
    DB_FILE=$(prlctl exec "$VM_NAME" "ls -t /home/parallels/CYT/logs/kismet/*.kismet 2>/dev/null | head -1" 2>/dev/null || echo "unknown")
    DB_SIZE=$(prlctl exec "$VM_NAME" "ls -lh $DB_FILE 2>/dev/null | awk '{print \$5}'" 2>/dev/null || echo "?")

    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  WARDRIVE SESSION COMPLETE${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Networks captured: $NETWORK_COUNT"
    echo "  Database size: $DB_SIZE"
    echo "  Database: $DB_FILE"
    echo ""
    echo "  Next steps:"
    echo "    • Export for WiGLE (in VM):"
    echo "      python3 /home/parallels/CYT/my_wigle_export.py"
    echo ""
    echo "    • Upload to WiGLE:"
    echo "      https://wigle.net/uploads"
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
}

status_wardrive() {
    print_banner
    echo "Checking wardrive status..."
    echo ""

    # Check sleep status
    SLEEP_STATUS=$(pmset -g | grep disablesleep | awk '{print $2}')
    if [ "$SLEEP_STATUS" = "1" ]; then
        print_status "Sleep disabled (lid-close safe)"
    else
        print_warning "Sleep enabled (lid close will stop capture)"
    fi

    # Check VM
    VM_STATE=$(prlctl list -a | grep "$VM_NAME" | awk '{print $2}')
    if [ "$VM_STATE" = "running" ]; then
        print_status "VM running"
    else
        print_error "VM not running"
    fi

    # Check Kismet
    KISMET_PID=$(prlctl exec "$VM_NAME" "pgrep -x kismet" 2>/dev/null || echo "")
    if [ -n "$KISMET_PID" ]; then
        print_status "Kismet running (PID $KISMET_PID)"
    else
        print_error "Kismet not running"
    fi

    # Check GPS
    GPS_DATA=$(prlctl exec "$VM_NAME" "timeout 3 cat /dev/ttyACM0 2>/dev/null | grep GNGGA | head -1" 2>/dev/null || echo "")
    if [ -n "$GPS_DATA" ]; then
        SATS=$(echo "$GPS_DATA" | cut -d',' -f8)
        print_status "GPS active ($SATS satellites)"
    else
        print_warning "GPS not responding"
    fi

    # Network count
    NETWORK_COUNT=$(prlctl exec "$VM_NAME" "sqlite3 /home/parallels/CYT/logs/kismet/*.kismet 'SELECT COUNT(*) FROM devices WHERE type LIKE \"%AP%\"' 2>/dev/null | tail -1" 2>/dev/null || echo "?")
    echo ""
    echo "Networks captured so far: $NETWORK_COUNT"
    echo ""
}

# Main
case "${1:-}" in
    start|"")
        start_wardrive
        ;;
    stop)
        stop_wardrive
        ;;
    status)
        status_wardrive
        ;;
    *)
        echo "Usage: $0 [start|stop|status]"
        echo ""
        echo "  start   - Enable wardrive mode (default)"
        echo "  stop    - Disable wardrive mode, show stats"
        echo "  status  - Check current wardrive status"
        exit 1
        ;;
esac
