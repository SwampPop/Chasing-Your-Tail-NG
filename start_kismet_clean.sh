#!/bin/bash

# TRULY CLEAN Kismet startup - NO pkill commands whatsoever!
cd /home/matt/Desktop/cytng

echo "$(date): Starting Kismet without any cleanup..."

# Just start Kismet directly - no process killing!
sudo /usr/local/bin/kismet -c wlan1 --daemonize

sleep 3

if pgrep -f kismet >/dev/null; then
    echo "SUCCESS - Kismet running"
    echo "Web interface: http://localhost:2501"
else
    echo "FAILED - Kismet not running"
fi