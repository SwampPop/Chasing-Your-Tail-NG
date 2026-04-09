#!/bin/bash
# CYT Pre-Flight Checklist
# Verifies all systems are ready before starting a monitoring session.
# Run this before launching cyt_gui.py, cyt_tui.py, or chasing_your_tail.py.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/config.json"
PASS=0
FAIL=0
WARN=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$((WARN + 1)); }

echo "═══════════════════════════════════════════════════"
echo "  CYT Pre-Flight Checklist"
echo "═══════════════════════════════════════════════════"
echo ""

# 1. Config file
echo "1. Configuration"
if [ -f "$CONFIG" ]; then
    pass "config.json found"
else
    fail "config.json not found at $CONFIG"
fi

# 2. Python dependencies
echo ""
echo "2. Python Dependencies"
MISSING_DEPS=""
for dep in kivy cryptography requests; do
    if python3 -c "import $dep" 2>/dev/null; then
        pass "$dep installed"
    else
        fail "$dep not installed"
        MISSING_DEPS="$MISSING_DEPS $dep"
    fi
done

# Optional deps
for dep in apprise geopy simplekml folium; do
    if python3 -c "import $dep" 2>/dev/null; then
        pass "$dep installed (optional)"
    else
        warn "$dep not installed (optional — some features disabled)"
    fi
done

# 3. Kismet database
echo ""
echo "3. Kismet Database"
DB_PATH=$(python3 -c "
import json
with open('$CONFIG') as f:
    c = json.load(f)
print(c.get('paths', {}).get('kismet_logs', ''))
" 2>/dev/null || echo "")

if [ -n "$DB_PATH" ]; then
    # shellcheck disable=SC2086
    DB_FILES=$(ls -t $DB_PATH/*.kismet 2>/dev/null | head -1)
    if [ -n "$DB_FILES" ]; then
        DB_AGE=$(python3 -c "
import os, time
age = time.time() - os.path.getmtime('$DB_FILES')
if age < 60: print(f'{age:.0f} seconds')
elif age < 3600: print(f'{age/60:.0f} minutes')
else: print(f'{age/3600:.1f} hours')
")
        pass "Kismet DB found: $(basename "$DB_FILES") (age: $DB_AGE)"
    else
        fail "No .kismet files found in $DB_PATH"
    fi
else
    fail "kismet_logs path not configured in config.json"
fi

# 4. Ignore lists
echo ""
echo "4. Ignore Lists"
IGNORE_DIR="$SCRIPT_DIR/ignore_lists"
if [ -f "$IGNORE_DIR/mac_list.txt" ]; then
    MAC_COUNT=$(grep -cv '^#\|^$' "$IGNORE_DIR/mac_list.txt" 2>/dev/null || echo 0)
    pass "MAC ignore list: $MAC_COUNT entries"
else
    warn "MAC ignore list not found (all devices will be analyzed)"
fi

if [ -f "$IGNORE_DIR/ssid_list.txt" ]; then
    SSID_COUNT=$(grep -cv '^#\|^$' "$IGNORE_DIR/ssid_list.txt" 2>/dev/null || echo 0)
    pass "SSID ignore list: $SSID_COUNT entries"
else
    warn "SSID ignore list not found"
fi

# 5. Credential store
echo ""
echo "5. Credentials"
if [ -d "$SCRIPT_DIR/secure_credentials" ]; then
    pass "Credential store directory exists"
    if [ -f "$SCRIPT_DIR/secure_credentials/encrypted_credentials.json" ]; then
        pass "Encrypted credentials file present"
    else
        warn "No encrypted credentials — Telegram/WiGLE alerts disabled"
    fi
else
    warn "No credential store — remote alerts disabled"
fi

# 6. GPS (check for gpsd on Linux, or serial GPS device)
echo ""
echo "6. GPS"
if command -v gpsd >/dev/null 2>&1; then
    if pgrep gpsd >/dev/null 2>&1; then
        pass "gpsd is running"
    else
        warn "gpsd installed but not running (no location correlation)"
    fi
elif [ "$(uname)" = "Darwin" ]; then
    if ls /dev/tty.usbmodem* >/dev/null 2>&1; then
        pass "USB GPS device detected"
    else
        warn "No GPS device detected (location features disabled)"
    fi
else
    warn "gpsd not installed (location features disabled)"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════"
echo -e "  Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$WARN warnings${NC}"
echo "═══════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo -e "  ${RED}Fix failures before starting a monitoring session.${NC}"
    if [ -n "$MISSING_DEPS" ]; then
        echo "  Install missing deps: pip3 install$MISSING_DEPS"
    fi
    exit 1
else
    echo ""
    echo -e "  ${GREEN}Ready for monitoring.${NC}"
    exit 0
fi
