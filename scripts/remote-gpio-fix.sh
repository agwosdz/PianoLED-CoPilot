#!/bin/bash

# Remote GPIO Fix Script
# This script automates the entire GPIO fix process on the Raspberry Pi
# Usage: bash remote-gpio-fix.sh <pi-ip> [<gpio-pin>]
# Example: bash remote-gpio-fix.sh 192.168.1.225 12

set -e

# Configuration
PI_IP="${1:-192.168.1.225}"
GPIO_PIN="${2:-12}"
PI_USER="pi"
SERVICE_NAME="piano-led-visualizer"
DB_PATH="/home/pi/PianoLED-CoPilot/backend/settings.db"
SCRIPT_PATH="/home/pi/PianoLED-CoPilot/scripts/diagnose-gpio.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          REMOTE GPIO FIX - Piano LED Visualizer               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ -z "$PI_IP" ]; then
    echo -e "${RED}ERROR: Raspberry Pi IP address required${NC}"
    echo "Usage: bash $0 <pi-ip> [<gpio-pin>]"
    echo "Example: bash $0 192.168.1.225 12"
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  Pi Address: $PI_IP"
echo "  GPIO Pin: $GPIO_PIN"
echo "  Service: $SERVICE_NAME"
echo ""

# Step 1: Check connectivity
echo -e "${YELLOW}Step 1: Checking connectivity to Pi...${NC}"
if ssh -o ConnectTimeout=5 "$PI_USER@$PI_IP" "echo 'Connected'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected to $PI_IP${NC}"
else
    echo -e "${RED}✗ Could not connect to $PI_IP${NC}"
    echo "  Make sure:"
    echo "  - Raspberry Pi is powered on and connected to network"
    echo "  - IP address is correct: $PI_IP"
    echo "  - SSH is enabled on Pi"
    echo "  - You have passwordless SSH or can enter password"
    exit 1
fi

echo ""

# Step 2: Run diagnostic script
echo -e "${YELLOW}Step 2: Running GPIO diagnostic on Pi...${NC}"
echo ""

ssh "$PI_USER@$PI_IP" << 'DIAGNOSTIC_SCRIPT'
cd /home/pi/PianoLED-CoPilot
if [ -f "scripts/diagnose-gpio.sh" ]; then
    sudo bash scripts/diagnose-gpio.sh
else
    echo "Diagnostic script not found!"
    exit 1
fi
DIAGNOSTIC_SCRIPT

DIAG_STATUS=$?
echo ""

if [ $DIAG_STATUS -ne 0 ]; then
    echo -e "${RED}✗ Diagnostic script failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Diagnostic completed${NC}"
echo ""

# Step 3: Confirm GPIO pin choice
echo -e "${YELLOW}Step 3: Confirming GPIO pin choice...${NC}"
echo "  Selected GPIO pin: $GPIO_PIN"
read -p "  Continue with GPIO $GPIO_PIN? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted by user${NC}"
    exit 1
fi

echo ""

# Step 4: Stop service
echo -e "${YELLOW}Step 4: Stopping piano-led-visualizer service...${NC}"

ssh "$PI_USER@$PI_IP" << STOP_SERVICE
sudo systemctl stop $SERVICE_NAME
sleep 2
echo "Service stopped"
STOP_SERVICE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Service stopped${NC}"
else
    echo -e "${RED}✗ Failed to stop service${NC}"
    exit 1
fi

echo ""

# Step 5: Backup settings
echo -e "${YELLOW}Step 5: Backing up settings.db...${NC}"

ssh "$PI_USER@$PI_IP" << BACKUP_DB
cd /home/pi/PianoLED-CoPilot
if [ -f "backend/settings.db" ]; then
    cp backend/settings.db backend/settings.db.backup
    ls -lh backend/settings.db*
    echo "Backup created"
else
    echo "Settings database not found!"
    exit 1
fi
BACKUP_DB

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Settings backed up${NC}"
else
    echo -e "${RED}✗ Failed to backup settings${NC}"
    exit 1
fi

echo ""

# Step 6: Update GPIO pin in settings.db
echo -e "${YELLOW}Step 6: Updating GPIO pin to $GPIO_PIN in settings.db...${NC}"

ssh "$PI_USER@$PI_IP" << UPDATE_DB
cd /home/pi/PianoLED-CoPilot
sqlite3 backend/settings.db << 'EOF'
UPDATE settings SET value='$GPIO_PIN' WHERE category='led' AND key='gpio_pin';
SELECT 'GPIO pin updated to: ' || value FROM settings WHERE category='led' AND key='gpio_pin';
EOF
VERIFY_RESULT=$?
if [ $VERIFY_RESULT -eq 0 ]; then
    echo "Update successful"
else
    echo "Update failed!"
    exit 1
fi
UPDATE_DB

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ GPIO pin updated to $GPIO_PIN${NC}"
else
    echo -e "${RED}✗ Failed to update GPIO pin${NC}"
    exit 1
fi

echo ""

# Step 7: Restart service
echo -e "${YELLOW}Step 7: Restarting piano-led-visualizer service...${NC}"

ssh "$PI_USER@$PI_IP" << RESTART_SERVICE
sudo systemctl start piano-led-visualizer
sleep 5
echo "Service restarted"
RESTART_SERVICE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Service restarted${NC}"
else
    echo -e "${RED}✗ Failed to restart service${NC}"
    exit 1
fi

echo ""

# Step 8: Verify health
echo -e "${YELLOW}Step 8: Verifying LED health status...${NC}"

HEALTH_RESPONSE=$(ssh "$PI_USER@$PI_IP" "curl -s http://localhost:5001/api/calibration/health")

if echo "$HEALTH_RESPONSE" | grep -q '"status".*"OK"'; then
    echo -e "${GREEN}✓ Health check PASSED${NC}"
    echo ""
    echo "LED Controller Status:"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    echo ""
    echo -e "${GREEN}✓ LED controller is responsive!${NC}"
    SUCCESS=true
elif echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
    echo -e "${YELLOW}⚠ Health check returned status but not OK${NC}"
    echo "Response:"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    SUCCESS=false
else
    echo -e "${RED}✗ Health check failed or API not responding${NC}"
    echo "Response: $HEALTH_RESPONSE"
    SUCCESS=false
fi

echo ""

# Step 9: Check service logs
echo -e "${YELLOW}Step 9: Checking service logs for errors...${NC}"

LOGS=$(ssh "$PI_USER@$PI_IP" "sudo journalctl -u $SERVICE_NAME -n 10 --no-pager")
echo "$LOGS"

if echo "$LOGS" | grep -i error | grep -v "No errors"; then
    echo -e "${YELLOW}⚠ Errors found in logs (see above)${NC}"
else
    echo -e "${GREEN}✓ No critical errors in logs${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"

if [ "$SUCCESS" = true ]; then
    echo -e "${BLUE}║                 ✅ GPIO FIX SUCCESSFUL!                       ║${NC}"
    echo -e "${BLUE}║                                                                ║${NC}"
    echo -e "${BLUE}║  • GPIO pin updated to: $GPIO_PIN                                  ║${NC}"
    echo -e "${BLUE}║  • Service is running                                          ║${NC}"
    echo -e "${BLUE}║  • LED controller is responsive                                ║${NC}"
    echo -e "${BLUE}║                                                                ║${NC}"
    echo -e "${BLUE}║  Next steps:                                                   ║${NC}"
    echo -e "${BLUE}║  1. Test LED control via web interface                         ║${NC}"
    echo -e "${BLUE}║  2. Verify physical LED strip responds                         ║${NC}"
    echo -e "${BLUE}║  3. Test MIDI input processing                                 ║${NC}"
else
    echo -e "${BLUE}║                 ⚠️ GPIO FIX INCOMPLETE                         ║${NC}"
    echo -e "${BLUE}║                                                                ║${NC}"
    echo -e "${BLUE}║  Health check did not return OK status.                        ║${NC}"
    echo -e "${BLUE}║  Try different GPIO pin and run again.                         ║${NC}"
    echo -e "${BLUE}║                                                                ║${NC}"
    echo -e "${BLUE}║  Next steps:                                                   ║${NC}"
    echo -e "${BLUE}║  1. Check logs (shown above)                                   ║${NC}"
    echo -e "${BLUE}║  2. Try different GPIO pin (13, 19, 21)                        ║${NC}"
    echo -e "${BLUE}║  3. Run script again with: bash remote-gpio-fix.sh $PI_IP 13   ║${NC}"
fi

echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi
