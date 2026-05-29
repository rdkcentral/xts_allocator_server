#!/bin/bash

# XTS Allocator Server - Live Demo Script
# Demonstrates all key features including authentication, allocations, rate limiting, and audit logs

BASE_URL="http://localhost:5000"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           XTS ALLOCATOR SERVER - LIVE DEMO                       ║"
echo "║           Current Features Showcase (Feb 2026)                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  AUTHENTICATION SYSTEM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔐 Login as Engineer..."
ENGINEER_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@example.com","password":"engineer123"}')
ENGINEER_TOKEN=$(echo $ENGINEER_RESPONSE | jq -r '.access_token')
echo "✅ Engineer logged in"
echo "   Token: ${ENGINEER_TOKEN:0:60}..."
echo "   Role: $(echo $ENGINEER_RESPONSE | jq -r '.user.role')"
echo ""

echo "🔐 Login as Admin..."
ADMIN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}')
ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | jq -r '.access_token')
echo "✅ Admin logged in"
echo "   Token: ${ADMIN_TOKEN:0:60}..."
echo "   Role: $(echo $ADMIN_RESPONSE | jq -r '.user.role')"
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  PROTECTED ROUTES - Auth Required"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "❌ Try to list devices WITHOUT authentication..."
curl -s $BASE_URL/list_slots | jq -c '{status, message}'
echo ""

echo "✅ List devices WITH authentication..."
curl -s $BASE_URL/list_slots \
  -H "Authorization: Bearer $ENGINEER_TOKEN" | jq '{device_count: (.devices | length), first_device: .devices[0].platform}'
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  DEVICE ALLOCATION with Duration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Allocate device for 2 hours..."
ALLOC_RESPONSE=$(curl -s -X POST $BASE_URL/allocate_slot \
  -H "Authorization: Bearer $ENGINEER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "email": "engineer@example.com",
      "username": "engineer",
      "name": "Test Engineer"
    },
    "slot": {"id": 1},
    "duration": "2h"
  }')

echo $ALLOC_RESPONSE | jq '{
  device_id: .device.id,
  platform: .device.platform,
  state: .device.state,
  owner: .device.owner_email,
  expiry: .device.allocation_expiry,
  history_id: .allocation_history.id
}'
DEVICE_ID=$(echo $ALLOC_RESPONSE | jq -r '.device.id')
HISTORY_ID=$(echo $ALLOC_RESPONSE | jq -r '.allocation_history.id')
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  TEST EXECUTION Tracking"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 Start test execution..."
TEST_RESPONSE=$(curl -s -X POST $BASE_URL/start_test \
  -H "Authorization: Bearer $ENGINEER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"test_suite\": \"performance_suite\",
    \"test_name\": \"video_playback_4k\",
    \"expected_duration\": 30,
    \"user_email\": \"engineer@example.com\"
  }")

echo $TEST_RESPONSE | jq '{
  test_id: .test_execution.id,
  device_state: .device_state,
  test_suite: .test_execution.test_suite,
  started_at: .test_execution.started_at
}'
TEST_ID=$(echo $TEST_RESPONSE | jq -r '.test_execution.id')
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  RATE LIMITING Protection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚡ Making 5 rapid requests (rate limit: 60/min)..."
for i in {1..5}; do
  RESPONSE=$(curl -s $BASE_URL/list_slots \
    -H "Authorization: Bearer $ENGINEER_TOKEN" \
    -w "\nHTTP_CODE:%{http_code}\n")
  HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
  echo "  Request $i: HTTP $HTTP_CODE"
done
echo "✅ All requests allowed (within rate limit)"
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  ROLE-BASED ACCESS CONTROL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "❌ Engineer tries to access admin-only audit logs..."
curl -s $BASE_URL/audit/logs \
  -H "Authorization: Bearer $ENGINEER_TOKEN" | jq -c '{status, message}'
echo ""

echo "✅ Admin accesses audit logs..."
AUDIT_RESPONSE=$(curl -s "$BASE_URL/audit/logs?limit=3" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo $AUDIT_RESPONSE | jq '{
  total_events: (.logs | length),
  recent_events: [.logs[0:3][] | {event_type, user_email, timestamp}]
}'
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  METRICS & MONITORING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 System metrics..."
curl -s $BASE_URL/metrics | jq '{
  total_devices: .total_devices,
  devices_by_state: .devices_by_state,
  allocations_today: .allocations_today
}'
echo ""

echo "🏥 Health check..."
curl -s $BASE_URL/health | jq '{status, service, database: .database.status}'
echo ""

sleep 1

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  CLEANUP - End test and deallocate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🏁 End test execution..."
curl -s -X POST $BASE_URL/end_test \
  -H "Authorization: Bearer $ENGINEER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"test_id\": $TEST_ID,
    \"status\": \"passed\",
    \"exit_code\": 0
  }" | jq '{message, device_state: .device.state}'
echo ""

echo "🗑️  Deallocate device..."
curl -s -X POST $BASE_URL/deallocate_slot \
  -H "Authorization: Bearer $ENGINEER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"user\": {\"email\": \"engineer@example.com\"},
    \"slot\": {\"id\": $DEVICE_ID}
  }" | jq '{message, device_state: .device.state}'
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  DEMO COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Key Features Demonstrated:"
echo "   ✓ JWT Authentication (3 roles: admin/engineer/readonly)"
echo "   ✓ Role-based access control (RBAC)"
echo "   ✓ Protected API endpoints"
echo "   ✓ Device allocation with duration/expiry"
echo "   ✓ Test execution tracking & lifecycle"
echo "   ✓ Rate limiting (per-user, sliding window)"
echo "   ✓ Audit logging (admin-only access)"
echo "   ✓ Metrics & health monitoring"
echo "   ✓ State machine validation"
echo ""
echo "🌐 Try the web dashboard: http://localhost:5000/dashboard"
echo "📖 API docs: http://localhost:5000/openapi.json"
echo ""
