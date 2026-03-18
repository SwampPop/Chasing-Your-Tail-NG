#!/bin/bash

# --- CHECK FOR ROOT PRIVILEGES (ADDED) ---
# Kismet requires root, so we exit early if not run with sudo.
if [ "$EUID" -ne 0 ]; then
  echo "❌ This script must be run as root. Please use sudo."
  exit 1
fi

# --- MAKE SCRIPT PORTABLE (CHANGED) ---
# This block makes the script run from its own directory.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

get_log_prefix() {
  if [ -n "${KISMET_LOG_PREFIX:-}" ]; then
    echo "$KISMET_LOG_PREFIX"
    return
  fi

  if [ -f "$DIR/config.json" ]; then
    python3 - <<'PY' "$DIR/config.json"
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as handle:
    config = json.load(handle)

paths = config.get("paths", {})
print(paths.get("kismet_logs_vm") or paths.get("kismet_logs") or "logs/kismet")
PY
    return
  fi

  echo "$DIR/logs/kismet"
}

# --- GET INTERFACE FROM ARGUMENT (ADDED) ---
# Use the first command-line argument as the interface, or default to 'wlan0'.
INTERFACE=${1:-wlan0}
LOG_PREFIX="$(get_log_prefix)"
echo "Starting Kismet on interface: $INTERFACE"
echo "Using log prefix: $LOG_PREFIX"

# Start Kismet directly
# Note: We don't need 'sudo' here because we already checked for root.
mkdir -p "$LOG_PREFIX"
/usr/bin/kismet -c "$INTERFACE" --daemonize --log-prefix "$LOG_PREFIX"

# --- INTELLIGENT WAIT (CHANGED) ---
# Loop for up to 10 seconds, checking every second for the Kismet process.
echo "Waiting for Kismet to start..."
for i in {1..10}; do
    if pgrep -f kismet >/dev/null; then
        echo "✅ SUCCESS - Kismet is running."
        echo "   Web interface: http://localhost:2501"
        exit 0 # Exit successfully
    fi
    sleep 1
done

# If the loop finishes without finding the process, it has failed.
echo "❌ FAILED - Kismet did not start within 10 seconds."
exit 1
