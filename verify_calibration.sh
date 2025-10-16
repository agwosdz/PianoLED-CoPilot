#!/bin/bash

# LED Calibration System - Verification Script
# Tests all backend calibration endpoints
# Usage: ./verify_calibration.sh [BASE_URL]

BASE_URL="${1:-http://localhost:5001}"
API="${BASE_URL}/api/calibration"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4
    local description=$5
    
    echo -e "${BLUE}Testing: $description${NC}"
    echo "  $method $API$endpoint"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        echo "  Response: $body" | head -c 100
        echo ""
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_code, got $http_code)"
        echo "  Response: $body" | head -c 100
        echo ""
        ((FAIL++))
        return 1
    fi
}

# Print header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  LED Calibration System - Endpoint Verification Script       ║${NC}"
echo -e "${BLUE}║  Base URL: $BASE_URL${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if server is running
echo -e "${YELLOW}Checking server connectivity...${NC}"
if ! curl -s "$BASE_URL" > /dev/null 2>&1; then
    echo -e "${RED}✗ Cannot connect to $BASE_URL${NC}"
    echo "  Make sure the backend is running: python -m backend.app"
    exit 1
fi
echo -e "${GREEN}✓ Server is reachable${NC}"
echo ""

# Test 1: Get calibration status
test_endpoint "GET" "/status" "" "200" "Get calibration status"

# Test 2: Get global offset
test_endpoint "GET" "/global-offset" "" "200" "Get global offset"

# Test 3: Set global offset (valid)
test_endpoint "PUT" "/global-offset" '{"global_offset": 5}' "200" "Set global offset to +5"

# Test 4: Verify global offset was set
test_endpoint "GET" "/global-offset" "" "200" "Verify global offset"

# Test 5: Set global offset (invalid - too high)
test_endpoint "PUT" "/global-offset" '{"global_offset": 150}' "400" "Set invalid global offset (should fail)"

# Test 6: Enable calibration
test_endpoint "POST" "/enable" "" "200" "Enable calibration mode"

# Test 7: Get calibration status (should show enabled)
test_endpoint "GET" "/status" "" "200" "Get status (should show enabled)"

# Test 8: Get single key offset
test_endpoint "GET" "/key-offset/60" "" "200" "Get offset for MIDI note 60 (Middle C)"

# Test 9: Set single key offset
test_endpoint "PUT" "/key-offset/60" '{"offset": 2}' "200" "Set Middle C offset to +2"

# Test 10: Set invalid MIDI note
test_endpoint "PUT" "/key-offset/200" '{"offset": 1}' "400" "Set invalid MIDI note (should fail)"

# Test 11: Get all key offsets
test_endpoint "GET" "/key-offsets" "" "200" "Get all key offsets"

# Test 12: Set multiple key offsets
test_endpoint "PUT" "/key-offsets" '{"key_offsets": {"60": 2, "21": -1, "108": 1}}' "200" "Set multiple key offsets"

# Test 13: Set A0 offset
test_endpoint "PUT" "/key-offset/21" '{"offset": -1}' "200" "Set A0 (MIDI 21) offset to -1"

# Test 14: Set C8 offset
test_endpoint "PUT" "/key-offset/108" '{"offset": 1}' "200" "Set C8 (MIDI 108) offset to +1"

# Test 15: Get all key offsets again
test_endpoint "GET" "/key-offsets" "" "200" "Get all key offsets (should have 3 entries)"

# Test 16: Export calibration
test_endpoint "GET" "/export" "" "200" "Export calibration data"

# Test 17: Import calibration
test_endpoint "POST" "/import" '{"global_offset": 3, "key_offsets": {"60": 1}}' "200" "Import calibration data"

# Test 18: Disable calibration
test_endpoint "POST" "/disable" "" "200" "Disable calibration mode"

# Test 19: Verify disabled
test_endpoint "GET" "/status" "" "200" "Get status (should show disabled)"

# Test 20: Reset calibration
test_endpoint "POST" "/reset" "" "200" "Reset calibration to defaults"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Test Results                                                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${GREEN}✓ PASSED: $PASS${NC}"
echo -e "${RED}✗ FAILED: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All tests passed! Calibration system is working correctly.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check the output above.${NC}"
    exit 1
fi
