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
for dep in cryptography requests; do
    if python3 -c "import $dep" 2>/dev/null; then
        pass "$dep installed"
    else
        fail "$dep not installed"
        MISSING_DEPS="$MISSING_DEPS $dep"
    fi
done

# GUI dep — required on macOS, optional on Linux (TUI/CLI work without it)
if python3 -c "import kivy" 2>/dev/null; then
    pass "kivy installed (GUI available)"
elif [ "$(uname)" = "Darwin" ]; then
    fail "kivy not installed (required for GUI on macOS)"
    MISSING_DEPS="$MISSING_DEPS kivy"
else
    warn "kivy not installed (GUI unavailable — use TUI or CLI instead)"
fi

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
import json, platform
with open('$CONFIG') as f:
    c = json.load(f)
paths = c.get('paths', {})
if platform.system() == 'Linux':
    print(paths.get('kismet_logs_vm') or paths.get('kismet_logs', ''))
else:
    print(paths.get('kismet_logs', ''))
" 2>/dev/null || echo "")

if [ -n "$DB_PATH" ]; then
    DB_FILES=$(find "$DB_PATH" -maxdepth 1 -name "*.kismet" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    # macOS fallback (find -printf not available)
    # Use xargs -r so ls is NOT called when find returns nothing
    # (without -r, xargs runs "ls -t" with no args, which lists the
    #  current directory and can return unrelated files like HANDOFF.md)
    if [ -z "$DB_FILES" ]; then
        DB_FILES=$(find "$DB_PATH" -maxdepth 1 -name "*.kismet" -type f 2>/dev/null | xargs -r ls -t 2>/dev/null | head -1)
    fi
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
    MAC_COUNT=$(grep -Ev '^#|^$' "$IGNORE_DIR/mac_list.txt" 2>/dev/null | wc -l | tr -d ' ')
    pass "MAC ignore list: $MAC_COUNT entries"
else
    warn "MAC ignore list not found (all devices will be analyzed)"
fi

if [ -f "$IGNORE_DIR/ssid_list.txt" ]; then
    SSID_COUNT=$(grep -Ev '^#|^$' "$IGNORE_DIR/ssid_list.txt" 2>/dev/null | wc -l | tr -d ' ')
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

# 7. Kismet log directory
echo ""
echo "7. Kismet Log Directory"
if [ -n "$DB_PATH" ]; then
    if [ -d "$DB_PATH" ]; then
        pass "Log directory exists: $DB_PATH"
    else
        warn "Log directory missing — creating now: $DB_PATH"
        mkdir -p "$DB_PATH" && pass "Log directory created" || fail "Could not create log directory"
    fi
else
    warn "kismet_logs path not configured in config.json"
fi

# 8. Wireless interface & monitor mode
echo ""
echo "8. Wireless Interface"
KISMET_IFACE=$(python3 -c "
import json
with open('$CONFIG') as f:
    c = json.load(f)
print(c.get('kismet_health', {}).get('interface', 'wlan0'))
" 2>/dev/null || echo "wlan0")

KISMET_RUNNING=false
if pgrep -x kismet >/dev/null 2>&1 || pgrep -f "kismet" >/dev/null 2>&1; then
    KISMET_RUNNING=true
    pass "Kismet process is running"
else
    warn "Kismet is not running — start it before launching the TUI"
fi

# When Kismet is already running it owns the wireless interface and may have
# renamed it (e.g. wlan0 -> wlan0mon) or virtualized it via the driver.
# In that case 'ip link show wlan0' returns nothing, which is expected.
# Strategy: check for a monitor-mode interface via 'iw dev'; only FAIL if
# Kismet is NOT running AND the interface is gone.
MONITOR_IFACE=$(iw dev 2>/dev/null | awk '/Interface/{iface=$2} /type monitor/{print iface; exit}')

if ip link show "$KISMET_IFACE" >/dev/null 2>&1; then
    # Interface still visible (Kismet not yet started, or managed mode)
    if iw dev "$KISMET_IFACE" info 2>/dev/null | grep -q "type monitor"; then
        pass "$KISMET_IFACE is in monitor mode"
    else
        if [ "$KISMET_RUNNING" = "true" ]; then
            # Kismet is up; it may be using an internal capture method
            pass "$KISMET_IFACE found — Kismet is running and managing capture"
        else
            warn "$KISMET_IFACE is NOT in monitor mode — Kismet will set this, but NetworkManager may interfere"
            if command -v nmcli >/dev/null 2>&1; then
                NM_STATE=$(nmcli -f DEVICE,STATE dev 2>/dev/null | awk -v iface="$KISMET_IFACE" '$1==iface {print $2}')
                if [ "$NM_STATE" = "connected" ] || [ "$NM_STATE" = "disconnected" ] || [ "$NM_STATE" = "unavailable" ]; then
                    warn "NetworkManager is managing $KISMET_IFACE (state: $NM_STATE) — run: sudo nmcli dev set $KISMET_IFACE managed no"
                else
                    pass "NetworkManager is NOT managing $KISMET_IFACE"
                fi
            fi
        fi
    fi
elif [ -n "$MONITOR_IFACE" ]; then
    # wlan0 was renamed/virtualized; a monitor interface exists under another name
    pass "Monitor-mode interface active: $MONITOR_IFACE (Kismet renamed $KISMET_IFACE)"
elif [ "$KISMET_RUNNING" = "true" ]; then
    # Kismet is running but we can't see the interface — it's fully owned by Kismet
    pass "$KISMET_IFACE is owned by the running Kismet process (expected)"
else
    fail "Interface $KISMET_IFACE not found and Kismet is not running — run 'ip link show' to check available interfaces"
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
