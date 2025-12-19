#!/bin/bash

# CYT-NG Universal Linux Installer
# Generates Systemd service and Logrotate config based on current location.

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   CYT-NG Linux Service Installer             ${NC}"
echo -e "${BLUE}==============================================${NC}"

# 1. Detect Environment
CURRENT_USER=$(whoami)
PROJECT_DIR=$(pwd)
PYTHON_BIN=$(which python3)

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}Error: python3 not found!${NC}"
    exit 1
fi

echo -e "Detected User:   ${GREEN}${CURRENT_USER}${NC}"
echo -e "Detected Dir:    ${GREEN}${PROJECT_DIR}${NC}"
echo -e "Python Path:     ${GREEN}${PYTHON_BIN}${NC}"

# Check for sudo
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Please run as root (use sudo ./install_service.sh)${NC}"
  exit 1
fi

echo -e "\n${BLUE}Generating Configuration Files...${NC}"

# 2. Generate Systemd Service
cat > cyt.service <<EOF
[Unit]
Description=Chasing Your Tail - Wireless Surveillance Detection
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON_BIN} cyt_daemon.py start
ExecStop=${PYTHON_BIN} cyt_daemon.py stop
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo -e "✓ Generated cyt.service"

# 3. Generate Logrotate Config
cat > cyt_logrotate.conf <<EOF
${PROJECT_DIR}/logs/*.log
${PROJECT_DIR}/logs/kismet/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ${CURRENT_USER} ${CURRENT_USER}
}
EOF

echo -e "✓ Generated cyt_logrotate.conf"

# 4. Install Service
echo -e "\n${BLUE}Installing Service...${NC}"

cp cyt.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable cyt

echo -e "✓ Service installed to /etc/systemd/system/cyt.service"
echo -e "✓ Service enabled on boot"

# 5. Install Logrotate
echo -e "\n${BLUE}Installing Log Rotation...${NC}"

cp cyt_logrotate.conf /etc/logrotate.d/cyt
chmod 644 /etc/logrotate.d/cyt

echo -e "✓ Logrotate config installed to /etc/logrotate.d/cyt"

# 6. Final Steps
echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}   Installation Complete!                     ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "To start the system now, run:"
echo -e "  ${BLUE}sudo systemctl start cyt${NC}"
echo -e ""
echo -e "To view logs:"
echo -e "  ${BLUE}tail -f ${PROJECT_DIR}/logs/cyt_monitor.log${NC}"
echo -e ""
