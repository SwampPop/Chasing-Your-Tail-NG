#!/bin/bash

# ADDED: Ensure only one instance of this script can run at a time.
# This creates a "lock file" in the /tmp directory.
exec 200>/tmp/cyt_gui.lock
flock -n 200 || { echo "Another instance is already running."; exit 1; }

# ADDED: Make the script portable by finding its own directory.
# This allows the project to be moved without breaking the script.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# REMOVED: The hardcoded path is no longer needed.
# cd /home/matt/Desktop/cytng

# REMOVED: The long, inefficient sleep is replaced by the more intelligent while loop below.
# sleep 120

# Set environment variables for GUI access
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Wait for X server to be available with a timeout
timeout_count=0
while ! xset q &>/dev/null; do
    echo "$(date): Waiting for X server... (attempt $timeout_count)" >> gui_startup.log
    sleep 15
    timeout_count=$((timeout_count + 1))
    if [ $timeout_count -gt 20 ]; then
        echo "$(date): ERROR - X server timeout after 300 seconds" >> gui_startup.log
        exit 1
    fi
done

echo "$(date): X server available, starting GUI..." >> gui_startup.log

# Start the GUI in the background and log all output
python3 cyt_gui.py >> gui_startup.log 2>&1 &

# Log success
echo "$(date): CYT GUI started successfully" >> gui_startup.log