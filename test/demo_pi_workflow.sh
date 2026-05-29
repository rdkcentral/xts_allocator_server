#!/bin/bash
# Live demonstration of Raspberry Pi device allocation workflow
# Shows: Auth → Allocate → Test → Deallocate

set -e

BASE_URL="http://localhost:5000"
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        RASPBERRY PI ALLOCATION WORKFLOW - LIVE DEMO                  ║"
echo "║        Complete End-to-End Test with Real Device                     ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 1: Authentication${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🔐 Logging in as engineer..."

LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@example.com","password":"engineer123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
USER_EMAIL=$(echo $LOGIN_RESPONSE | jq -r '.user.email')
USER_ROLE=$(echo $LOGIN_RESPONSE | jq -r '.user.role')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Authentication failed!${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated successfully${NC}"
echo "   Email: $USER_EMAIL"
echo "   Role: $USER_ROLE"
echo "   Token: ${TOKEN:0:50}..."
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 2: Query Available Raspberry Pi Devices${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🔍 Searching for available Raspberry Pi devices..."

SEARCH_RESPONSE=$(curl -s -X POST $BASE_URL/list_slots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform": "raspberrypi", "state": "free"}')

echo "$SEARCH_RESPONSE" | jq '.devices[] | {
  id: .id,
  model: .model,
  hostname: .host_ipv4,
  state: .state,
  rack: .rack.name
}'

PI_DEVICE_ID=$(echo "$SEARCH_RESPONSE" | jq -r '.devices[0].id')

if [ "$PI_DEVICE_ID" == "null" ] || [ -z "$PI_DEVICE_ID" ]; then
    echo -e "${RED}❌ No free Raspberry Pi devices found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found available device (ID: $PI_DEVICE_ID)${NC}"
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 3: Allocate Raspberry Pi Device${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📋 Allocating device $PI_DEVICE_ID for 2 hours..."

ALLOC_RESPONSE=$(curl -s -X POST $BASE_URL/allocate_slot \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"user\": {
      \"email\": \"$USER_EMAIL\",
      \"username\": \"engineer\",
      \"name\": \"Test Engineer\"
    },
    \"slot\": {\"id\": $PI_DEVICE_ID},
    \"duration\": \"2h\"
  }")

if echo "$ALLOC_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}❌ Allocation failed!${NC}"
    echo "$ALLOC_RESPONSE" | jq .
    exit 1
fi

DEVICE_HOSTNAME=$(echo "$ALLOC_RESPONSE" | jq -r '.device.host_ipv4')
DEVICE_STATE=$(echo "$ALLOC_RESPONSE" | jq -r '.device.state')
DEVICE_MODEL=$(echo "$ALLOC_RESPONSE" | jq -r '.device.model')
ALLOCATION_EXPIRY=$(echo "$ALLOC_RESPONSE" | jq -r '.device.allocation_expiry')
HISTORY_ID=$(echo "$ALLOC_RESPONSE" | jq -r '.allocation_history.id')
SSH_URI=$(echo "$ALLOC_RESPONSE" | jq -r '.device.control_uris.ssh')

echo -e "${GREEN}✅ Device allocated successfully!${NC}"
echo ""
echo "   Device: $DEVICE_MODEL"
echo "   Hostname: $DEVICE_HOSTNAME"
echo "   SSH: $SSH_URI"
echo "   State: $DEVICE_STATE"
echo "   Expires: $ALLOCATION_EXPIRY"
echo "   History ID: $HISTORY_ID"
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 4: Check SSH Connectivity${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🔌 Testing SSH connectivity to $DEVICE_HOSTNAME..."

if timeout 3 nc -z -w 2 ${DEVICE_HOSTNAME} 22 2>/dev/null; then
    echo -e "${GREEN}✅ SSH port 22 is reachable on $DEVICE_HOSTNAME${NC}"
    echo "   You can SSH: ssh $DEVICE_HOSTNAME"
else
    echo -e "${YELLOW}⚠️  SSH port not reachable (device may be offline or hostname not resolving)${NC}"
    echo "   This is OK for demo - continuing with workflow..."
fi
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 5: Start Test Execution${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🧪 Starting test execution on device..."

TEST_RESPONSE=$(curl -s -X POST $BASE_URL/start_test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $PI_DEVICE_ID,
    \"test_suite\": \"pi_validation_suite\",
    \"test_name\": \"basic_connectivity_test\",
    \"expected_duration\": 5,
    \"user_email\": \"$USER_EMAIL\",
    \"allocation_history_id\": $HISTORY_ID
  }")

if echo "$TEST_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}❌ Test start failed!${NC}"
    echo "$TEST_RESPONSE" | jq .
else
    TEST_ID=$(echo "$TEST_RESPONSE" | jq -r '.test_execution.id')
    DEVICE_STATE=$(echo "$TEST_RESPONSE" | jq -r '.device.state')
    TEST_SUITE=$(echo "$TEST_RESPONSE" | jq -r '.test_execution.test_suite')
    
    echo -e "${GREEN}✅ Test started successfully!${NC}"
    echo ""
    echo "   Test ID: $TEST_ID"
    echo "   Test Suite: $TEST_SUITE"
    echo "   Device State: $DEVICE_STATE"
    echo ""
    
    echo "⏳ Simulating test execution (5 seconds)..."
    sleep 2
    
    echo "📡 Sending heartbeat..."
    curl -s -X POST $BASE_URL/test_heartbeat \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"test_id\": $TEST_ID}" > /dev/null
    
    sleep 3
    echo -e "${GREEN}✅ Test heartbeat sent${NC}"
    echo ""
fi

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 6: End Test Execution${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🏁 Ending test execution..."

if [ ! -z "$TEST_ID" ]; then
    END_RESPONSE=$(curl -s -X POST $BASE_URL/end_test \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"test_id\": $TEST_ID,
        \"status\": \"passed\",
        \"exit_code\": 0,
        \"logs_url\": \"http://logs.example.com/test-$TEST_ID\"
      }")
    
    if echo "$END_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Test end warning:${NC}"
        echo "$END_RESPONSE" | jq .
    else
        DEVICE_STATE=$(echo "$END_RESPONSE" | jq -r '.device.state')
        echo -e "${GREEN}✅ Test completed successfully!${NC}"
        echo "   Device State: $DEVICE_STATE (back to allocated)"
    fi
fi
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 7: View Allocation History${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📊 Checking allocation history..."

HISTORY_RESPONSE=$(curl -s "$BASE_URL/allocation_history?device_id=$PI_DEVICE_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$HISTORY_RESPONSE" | jq '.allocations[0] | {
  id: .id,
  user_email: .user_email,
  allocated_at: .allocated_at,
  duration_requested: .duration_requested_minutes,
  test_count: .test_executions_count,
  state: .state
}'

echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}STEP 8: Deallocate Device${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🗑️  Deallocating device $PI_DEVICE_ID..."

DEALLOC_RESPONSE=$(curl -s -X POST $BASE_URL/deallocate_slot \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"user\": {\"email\": \"$USER_EMAIL\"},
    \"slot\": {\"id\": $PI_DEVICE_ID}
  }")

if echo "$DEALLOC_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Deallocation warning:${NC}"
    echo "$DEALLOC_RESPONSE" | jq .
else
    FINAL_STATE=$(echo "$DEALLOC_RESPONSE" | jq -r '.device.state')
    echo -e "${GREEN}✅ Device deallocated successfully!${NC}"
    echo "   Final State: $FINAL_STATE"
    echo "   Device is now available for others"
fi
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}DEMO COMPLETE! ✅${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "🎉 Successfully demonstrated full workflow:"
echo ""
echo "   ✅ Authentication (JWT token)"
echo "   ✅ Device discovery (search by platform)"
echo "   ✅ Device allocation (2h duration)"
echo "   ✅ SSH connectivity check"
echo "   ✅ Test execution lifecycle (start → heartbeat → end)"
echo "   ✅ Allocation history tracking"
echo "   ✅ Device deallocation"
echo ""
echo "📝 The system tracked:"
echo "   • Who allocated the device ($USER_EMAIL)"
echo "   • When it was allocated"
echo "   • Test execution (ID: $TEST_ID)"
echo "   • Complete audit trail in allocation history"
echo ""
echo "🔗 Real-world usage:"
echo "   • SSH to device: ssh $DEVICE_HOSTNAME"
echo "   • Run your actual tests via SSH"
echo "   • Report results via API"
echo "   • Auto-cleanup after 2 hours"
echo ""
echo "🌐 View dashboard: http://localhost:5000/dashboard"
echo ""
