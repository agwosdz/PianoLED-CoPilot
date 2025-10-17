#!/bin/bash
# LED Controller Fix Verification Script
# Run this on your Pi to verify the fix is working

echo "=================================================="
echo "LED Controller Singleton Fix Verification"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "[1/5] Checking if service is running..."
if sudo systemctl is-active --quiet piano-led-visualizer; then
    echo -e "${GREEN}✓${NC} Service is running"
else
    echo -e "${RED}✗${NC} Service is NOT running. Starting..."
    sudo systemctl start piano-led-visualizer
    sleep 3
fi
echo ""

echo "[2/5] Checking for singleton reset message..."
if sudo journalctl -u piano-led-visualizer -n 50 | grep -q "singleton reset"; then
    echo -e "${GREEN}✓${NC} Singleton reset message found"
    sudo journalctl -u piano-led-visualizer -n 50 | grep "singleton reset"
else
    echo -e "${YELLOW}⚠${NC} Singleton reset message not found - service may not have been restarted"
    echo "   Restarting service..."
    sudo systemctl restart piano-led-visualizer
    sleep 3
    if sudo journalctl -u piano-led-visualizer -n 50 | grep -q "singleton reset"; then
        echo -e "${GREEN}✓${NC} Found after restart"
    else
        echo -e "${RED}✗${NC} Still not found - check app.py was deployed"
    fi
fi
echo ""

echo "[3/5] Checking if rpi_ws281x is loaded (not in simulation mode)..."
if sudo journalctl -u piano-led-visualizer -n 50 | grep -q "rpi_ws281x library loaded successfully"; then
    echo -e "${GREEN}✓${NC} Hardware library loaded - NOT in simulation mode"
else
    echo -e "${RED}✗${NC} Hardware library NOT loaded - running in simulation mode"
    echo "   Check: python3 -c \"from rpi_ws281x import PixelStrip\""
fi
echo ""

echo "[4/5] Checking LED controller initialization..."
LED_INIT=$(sudo journalctl -u piano-led-visualizer -n 50 | grep "LED controller initialized")
if [ -n "$LED_INIT" ]; then
    echo -e "${GREEN}✓${NC} LED controller initialized successfully"
    echo "   $LED_INIT"
else
    echo -e "${RED}✗${NC} LED controller initialization not found"
fi
echo ""

echo "[5/5] Checking API responsiveness..."
if curl -s http://localhost:5001/api/midi-input/status > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API is responding"
else
    echo -e "${RED}✗${NC} API not responding - service may not be fully started"
fi
echo ""

echo "=================================================="
echo "Full Recent Logs:"
echo "=================================================="
sudo journalctl -u piano-led-visualizer -n 30

echo ""
echo "=================================================="
echo "Verification Complete"
echo "=================================================="
