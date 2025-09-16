#!/bin/bash

# Define colors once, outside the loop
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Start the infinite monitoring loop
while true; do
    # Clear the screen for a clean, updating display
    clear

    echo "--- CYT Monitor --- ($(date))"
    echo

    # 1. Check for Kismet process using pgrep
    # pgrep is a more reliable tool for finding processes.
    # The '-afc' flags count all processes matching the name.
    if pgrep -afc kismet > /dev/null; then
        echo -e "${GREEN}Kismet Status:  UP${NC}"
    else
        echo -e "${RED}Kismet Status:  DOWN${NC}"
    fi

    # 2. Check for Monitor Mode correctly
    # 'iwconfig 2>/dev/null' checks all interfaces and hides errors.
    # 'grep -q' searches quietly and sets an exit code, which is very efficient.
    if iwconfig 2>/dev/null | grep -q "Mode:Monitor"; then
        echo -e "${GREEN}Monitor Mode:   DETECTED${NC}"
    else
        echo -e "${RED}Monitor Mode:   NOT DETECTED${NC}"
    fi

    # Wait 10 seconds before the next check
    sleep 10
done