#!/bin/bash
# Test script to verify memory ownership validation
# Tests that users can only access/modify/delete their own memories

set -e

API_URL="http://localhost:8000"
USER_A="user_a_test"
USER_B="user_b_test"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔒 Memory Ownership Validation Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: User A creates a memory
echo "📝 Test 1: User A creates a memory..."
RESPONSE=$(curl -s -X POST "$API_URL/memories" \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"User A's secret data\"}],\"user_id\":\"$USER_A\"}")

MEMORY_ID=$(echo $RESPONSE | jq -r '.results[0].id // .id // empty')

if [ -z "$MEMORY_ID" ]; then
  echo "❌ Failed to create memory for User A"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "✅ User A created memory: $MEMORY_ID"
echo ""

# Test 2: User A can read their own memory
echo "📖 Test 2: User A reads their own memory..."
RESPONSE=$(curl -s -X GET "$API_URL/memories/$MEMORY_ID?user_id=$USER_A")

if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "✅ User A can read their own memory"
else
  echo "❌ User A cannot read their own memory"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 3: User B CANNOT read User A's memory
echo "🔒 Test 3: User B tries to read User A's memory (should fail)..."
RESPONSE=$(curl -s -X GET "$API_URL/memories/$MEMORY_ID?user_id=$USER_B")

if echo "$RESPONSE" | jq -e '.detail' | grep -q "Access denied"; then
  echo "✅ User B correctly blocked from reading User A's memory"
else
  echo "❌ SECURITY ISSUE: User B can read User A's memory!"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 4: User B CANNOT delete User A's memory
echo "🗑️  Test 4: User B tries to delete User A's memory (should fail)..."
RESPONSE=$(curl -s -X DELETE "$API_URL/memories/$MEMORY_ID?user_id=$USER_B")

if echo "$RESPONSE" | jq -e '.detail' | grep -q "Access denied"; then
  echo "✅ User B correctly blocked from deleting User A's memory"
else
  echo "❌ SECURITY ISSUE: User B can delete User A's memory!"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 5: Verify memory still exists
echo "🔍 Test 5: Verify User A's memory still exists..."
RESPONSE=$(curl -s -X GET "$API_URL/memories/$MEMORY_ID?user_id=$USER_A")

if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "✅ Memory still exists after failed deletion attempt"
else
  echo "❌ Memory was deleted!"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 6: User B CANNOT view User A's memory history
echo "📜 Test 6: User B tries to view User A's memory history (should fail)..."
RESPONSE=$(curl -s -X GET "$API_URL/memories/$MEMORY_ID/history?user_id=$USER_B")

if echo "$RESPONSE" | jq -e '.detail' | grep -q "Access denied"; then
  echo "✅ User B correctly blocked from viewing User A's memory history"
else
  echo "❌ SECURITY ISSUE: User B can view User A's memory history!"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 7: User A CAN view their own memory history
echo "📜 Test 7: User A views their own memory history..."
RESPONSE=$(curl -s -X GET "$API_URL/memories/$MEMORY_ID/history?user_id=$USER_A")

if echo "$RESPONSE" | jq -e '.[0]' > /dev/null 2>&1 || echo "$RESPONSE" | jq -e '.[]' > /dev/null 2>&1; then
  echo "✅ User A can view their own memory history"
else
  echo "⚠️  User A cannot view memory history (may not be supported)"
  echo "Response: $RESPONSE"
fi
echo ""

# Test 8: User A CAN delete their own memory
echo "🗑️  Test 8: User A deletes their own memory..."
RESPONSE=$(curl -s -X DELETE "$API_URL/memories/$MEMORY_ID?user_id=$USER_A")

if echo "$RESPONSE" | jq -e '.message' | grep -q "deleted successfully"; then
  echo "✅ User A successfully deleted their own memory"
else
  echo "❌ User A cannot delete their own memory"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 9: Create memory for User B
echo "📝 Test 9: User B creates their own memory..."
RESPONSE=$(curl -s -X POST "$API_URL/memories" \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"User B's secret data\"}],\"user_id\":\"$USER_B\"}")

MEMORY_B_ID=$(echo $RESPONSE | jq -r '.results[0].id // .id // empty')

if [ -z "$MEMORY_B_ID" ]; then
  echo "❌ Failed to create memory for User B"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "✅ User B created memory: $MEMORY_B_ID"
echo ""

# Test 10: User A CANNOT access User B's memory
echo "🔒 Test 10: User A tries to read User B's memory (should fail)..."
RESPONSE=$(curl -s -X GET "$API_URL/memories/$MEMORY_B_ID?user_id=$USER_A")

if echo "$RESPONSE" | jq -e '.detail' | grep -q "Access denied"; then
  echo "✅ User A correctly blocked from reading User B's memory"
else
  echo "❌ SECURITY ISSUE: User A can read User B's memory!"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

# Test 11: Search is properly scoped
echo "🔍 Test 11: Verify search is scoped to user..."
RESPONSE_A=$(curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"secret data\",\"user_id\":\"$USER_A\"}")

RESPONSE_B=$(curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"secret data\",\"user_id\":\"$USER_B\"}")

# User A should not find User B's memory
if echo "$RESPONSE_A" | jq -e '.results' | grep -q "$MEMORY_B_ID"; then
  echo "❌ SECURITY ISSUE: User A can find User B's memory in search!"
  exit 1
else
  echo "✅ Search correctly scoped to user"
fi
echo ""

# Cleanup
echo "🧹 Cleanup: Deleting User B's memory..."
curl -s -X DELETE "$API_URL/memories/$MEMORY_B_ID?user_id=$USER_B" > /dev/null
echo "✅ Cleanup complete"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ All Ownership Tests Passed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Summary:"
echo "  ✓ User isolation works correctly"
echo "  ✓ Users can only access their own memories"
echo "  ✓ Users cannot read other users' memories"
echo "  ✓ Users cannot delete other users' memories"
echo "  ✓ Users cannot view other users' memory history"
echo "  ✓ Search is properly scoped to user"
echo ""
