#!/bin/bash
# Kismet Health Monitor Test Script
# Tests all health monitoring scenarios

set -e

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RESET='\033[0m'

echo "========================================================================"
echo "Kismet Health Monitor Test Suite"
echo "========================================================================"
echo ""

# Test 1: Check if Kismet is currently running
echo -e "${COLOR_BLUE}TEST 1: Current Kismet Status${COLOR_RESET}"
echo "Checking if Kismet is currently running..."
if pgrep -x kismet > /dev/null; then
    KISMET_PIDS=$(pgrep -x kismet | tr '\n' ' ')
    echo -e "${COLOR_GREEN}✓ Kismet is running (PIDs: ${KISMET_PIDS})${COLOR_RESET}"
    KISMET_WAS_RUNNING=true
else
    echo -e "${COLOR_RED}✗ Kismet is NOT running${COLOR_RESET}"
    KISMET_WAS_RUNNING=false
fi
echo ""

# Test 2: Check for Kismet database
echo -e "${COLOR_BLUE}TEST 2: Kismet Database Check${COLOR_RESET}"
echo "Looking for Kismet database files..."
DB_FILES=$(find . -name "*.kismet" -type f 2>/dev/null | head -n 5)
if [ -n "$DB_FILES" ]; then
    echo -e "${COLOR_GREEN}✓ Found Kismet database(s):${COLOR_RESET}"
    echo "$DB_FILES" | while read db; do
        SIZE=$(ls -lh "$db" | awk '{print $5}')
        MTIME=$(stat -f "%Sm" "$db" 2>/dev/null || stat -c "%y" "$db" 2>/dev/null)
        echo "  - $db (${SIZE}, modified: ${MTIME})"
    done
else
    echo -e "${COLOR_YELLOW}⚠ No Kismet databases found in current directory${COLOR_RESET}"
fi
echo ""

# Test 3: Run standalone health monitor
echo -e "${COLOR_BLUE}TEST 3: Standalone Health Monitor${COLOR_RESET}"
echo "Running kismet_health_monitor.py standalone test..."
echo "----------------------------------------"
python3 kismet_health_monitor.py
TEST3_EXIT=$?
echo "----------------------------------------"
if [ $TEST3_EXIT -eq 0 ]; then
    echo -e "${COLOR_GREEN}✓ Standalone health monitor executed successfully${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Standalone health monitor failed (exit code: $TEST3_EXIT)${COLOR_RESET}"
fi
echo ""

# Test 4: Verify config.json has health monitoring enabled
echo -e "${COLOR_BLUE}TEST 4: Configuration Check${COLOR_RESET}"
echo "Checking config.json for health monitoring settings..."
if grep -q '"kismet_health"' config.json; then
    echo -e "${COLOR_GREEN}✓ kismet_health section found in config.json${COLOR_RESET}"

    ENABLED=$(python3 -c "import json; print(json.load(open('config.json'))['kismet_health']['enabled'])" 2>/dev/null)
    AUTO_RESTART=$(python3 -c "import json; print(json.load(open('config.json'))['kismet_health']['auto_restart'])" 2>/dev/null)
    CHECK_INTERVAL=$(python3 -c "import json; print(json.load(open('config.json'))['kismet_health']['check_interval_cycles'])" 2>/dev/null)

    echo "  - enabled: $ENABLED"
    echo "  - auto_restart: $AUTO_RESTART"
    echo "  - check_interval_cycles: $CHECK_INTERVAL"

    if [ "$ENABLED" = "True" ]; then
        echo -e "${COLOR_GREEN}✓ Health monitoring is ENABLED${COLOR_RESET}"
    else
        echo -e "${COLOR_YELLOW}⚠ Health monitoring is DISABLED${COLOR_RESET}"
    fi
else
    echo -e "${COLOR_RED}✗ kismet_health section NOT found in config.json${COLOR_RESET}"
fi
echo ""

# Test 5: Check if AlertManager is available
echo -e "${COLOR_BLUE}TEST 5: AlertManager Availability${COLOR_RESET}"
echo "Checking if AlertManager is available..."
if python3 -c "from alert_manager import AlertManager; AlertManager()" 2>/dev/null; then
    echo -e "${COLOR_GREEN}✓ AlertManager is available and can be instantiated${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ AlertManager not available (this is OK - alerts will only be logged)${COLOR_RESET}"
fi
echo ""

# Test 6: Verify all imports work
echo -e "${COLOR_BLUE}TEST 6: Import Test${COLOR_RESET}"
echo "Testing if all health monitoring imports work..."
if python3 -c "from kismet_health_monitor import KismetHealthMonitor; from chasing_your_tail import CYTMonitorApp; print('Imports successful')" 2>&1 | grep -q "Imports successful"; then
    echo -e "${COLOR_GREEN}✓ All imports successful${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Import errors detected${COLOR_RESET}"
    python3 -c "from kismet_health_monitor import KismetHealthMonitor; from chasing_your_tail import CYTMonitorApp"
fi
echo ""

# Summary
echo "========================================================================"
echo "Test Summary"
echo "========================================================================"
echo ""
if [ "$KISMET_WAS_RUNNING" = true ]; then
    echo -e "${COLOR_GREEN}Kismet Status: RUNNING${COLOR_RESET}"
    echo "  → Ready for live health monitoring tests"
    echo ""
    echo "Next steps:"
    echo "  1. Run CYT and watch for health check messages:"
    echo "     python3 chasing_your_tail.py"
    echo ""
    echo "  2. In another terminal, monitor the logs:"
    echo "     tail -f logs/cyt_log_*.log | grep -i 'health\\|kismet'"
    echo ""
    echo "  3. To test failure detection, stop Kismet:"
    echo "     sudo pkill kismet"
    echo ""
else
    echo -e "${COLOR_YELLOW}Kismet Status: NOT RUNNING${COLOR_RESET}"
    echo "  → Start Kismet before testing health monitoring"
    echo ""
    echo "Next steps:"
    echo "  1. Start Kismet:"
    echo "     sudo ./start_kismet_clean.sh wlan0mon"
    echo ""
    echo "  2. Verify Kismet is running:"
    echo "     pgrep kismet"
    echo ""
    echo "  3. Run this test script again to verify health checks"
fi
echo ""
echo "========================================================================"
