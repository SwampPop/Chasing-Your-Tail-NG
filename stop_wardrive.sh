#!/bin/bash
# CYT Wardriving Stop Script - macOS
# Restores normal power settings after wardriving

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CYT WARDRIVE STOP SCRIPT                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

get_vm_kismet_logs_dir() {
    python3 - <<'PY' "$SCRIPT_DIR/config.json"
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as handle:
    config = json.load(handle)

paths = config.get("paths", {})
print(paths.get("kismet_logs_vm") or "/home/parallels/CYT/logs/kismet")
PY
}

# ============================================
# STEP 1: Re-enable macOS sleep
# ============================================
echo -e "${BLUE}▶ Step 1: Restoring macOS power settings...${NC}"

sudo pmset -a disablesleep 0
echo -e "${GREEN}   ✓${NC} System sleep re-enabled"

sudo pmset -a displaysleep 10
echo -e "${GREEN}   ✓${NC} Display sleep restored (10 min)"

# Kill caffeinate
if [ -f /tmp/cyt_caffeinate.pid ]; then
    CAFF_PID=$(cat /tmp/cyt_caffeinate.pid)
    kill $CAFF_PID 2>/dev/null && echo -e "${GREEN}   ✓${NC} Caffeinate stopped" || true
    rm /tmp/cyt_caffeinate.pid
fi
pkill caffeinate 2>/dev/null || true

# ============================================
# STEP 2: Show capture statistics
# ============================================
echo ""
echo -e "${BLUE}▶ Step 2: Wardrive Statistics...${NC}"

# Get stats from Kismet
STATS=$(prlctl exec CYT-Kali "curl -s --user kismet:${KISMET_PASS:?KISMET_PASS env var must be set} 'http://localhost:2501/devices/views/all/count.json'" 2>/dev/null)
DEVICE_COUNT=$(echo "$STATS" | grep -o '[0-9]*' | head -1)
echo "   Total devices captured: ${GREEN}${DEVICE_COUNT:-unknown}${NC}"

# Find the latest kismet database
VM_KISMET_LOGS="$(get_vm_kismet_logs_dir)"
LATEST_DB=$(prlctl exec CYT-Kali "ls -t \"$VM_KISMET_LOGS\"/*.kismet 2>/dev/null | head -1")
if [ -n "$LATEST_DB" ]; then
    echo "   Latest capture file: $LATEST_DB"
fi

# ============================================
# STEP 3: Export options
# ============================================
echo ""
echo -e "${BLUE}▶ Step 3: Export Options...${NC}"
echo ""
echo "   To export for WiGLE upload:"
echo "     ${YELLOW}cd ~/my_projects/0_active_projects/Chasing-Your-Tail-NG${NC}"
echo "     ${YELLOW}python3 my_wigle_export.py${NC}"
echo ""
echo "   To view in Kismet Web UI:"
echo "     Open browser to http://localhost:2501 (in VM)"
echo ""

# ============================================
# STEP 4: Cleanup options
# ============================================
echo -e "${BLUE}▶ Step 4: Services Status...${NC}"

# Check what's still running
echo -n "   Kismet: "
if prlctl exec CYT-Kali "pgrep kismet" > /dev/null 2>&1; then
    echo -e "${GREEN}running${NC} (stop with: prlctl exec CYT-Kali 'sudo pkill kismet')"
else
    echo -e "${YELLOW}stopped${NC}"
fi

echo -n "   gpsd: "
if pgrep gpsd > /dev/null; then
    echo -e "${GREEN}running${NC} (stop with: sudo pkill gpsd)"
else
    echo -e "${YELLOW}stopped${NC}"
fi

echo -n "   VM: "
VM_STATUS=$(prlctl list -a 2>/dev/null | grep CYT-Kali | awk '{print $2}')
echo -e "${GREEN}${VM_STATUS}${NC}"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ${GREEN}WARDRIVE SESSION COMPLETE${NC}                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Normal power settings restored. Lid close will now sleep."
echo ""
