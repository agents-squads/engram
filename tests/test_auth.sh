#!/bin/bash
# Test MCP Authentication System

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧪 Testing MCP Authentication"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create test token
echo "📝 Creating test token..."
TEST_USER="test@example.com"
TOKEN_OUTPUT=$(python3 scripts/mcp-token.py create --user-id "$TEST_USER" --name "Test User" 2>&1)

# Extract token from output
TEST_TOKEN=$(echo "$TOKEN_OUTPUT" | grep "^Token:" | awk '{print $2}')

if [ -z "$TEST_TOKEN" ]; then
    echo "❌ Failed to create test token"
    echo "$TOKEN_OUTPUT"
    exit 1
fi

echo "✅ Test token created: ${TEST_TOKEN:0:16}..."
echo ""

# Test 1: Missing headers
echo "Test 1: Missing authentication headers (should fail with 401)"
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/sse)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ PASS - Rejected with 401"
else
    echo "❌ FAIL - Expected 401, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 2: Invalid token
echo "Test 2: Invalid token (should fail with 401)"
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/sse \
  -H "X-MCP-Token: invalid_token_12345" \
  -H "X-MCP-UserID: $TEST_USER")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "401" ] && echo "$BODY" | grep -q "Invalid authentication token"; then
    echo "✅ PASS - Invalid token rejected"
else
    echo "❌ FAIL - Expected 401 with error message"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 3: Valid token, wrong user ID
echo "Test 3: Valid token with wrong user ID (should fail with 401)"
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/sse \
  -H "X-MCP-Token: $TEST_TOKEN" \
  -H "X-MCP-UserID: wrong@example.com")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "401" ] && echo "$BODY" | grep -q "User ID mismatch"; then
    echo "✅ PASS - User ID mismatch detected"
else
    echo "❌ FAIL - Expected 401 with mismatch error"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 4: Valid token and user ID (should succeed)
echo "Test 4: Valid token and user ID (should succeed with 200)"
RESPONSE=$(curl -s -w "\n%{http_code}" -I http://localhost:8080/sse \
  -H "X-MCP-Token: $TEST_TOKEN" \
  -H "X-MCP-UserID: $TEST_USER")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ PASS - Authentication successful"
else
    echo "❌ FAIL - Expected 200, got $HTTP_CODE"
    echo "Response: $RESPONSE"
    exit 1
fi
echo ""

# Test 5: Token revocation
echo "Test 5: Token revocation (revoke and test)"
python3 scripts/mcp-token.py revoke "$TEST_TOKEN" --yes > /dev/null 2>&1

RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/sse \
  -H "X-MCP-Token: $TEST_TOKEN" \
  -H "X-MCP-UserID: $TEST_USER")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "401" ] && echo "$BODY" | grep -q "disabled"; then
    echo "✅ PASS - Revoked token rejected"
else
    echo "❌ FAIL - Expected 401 with disabled error"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 6: Re-enable token
echo "Test 6: Re-enable token (enable and test)"
python3 scripts/mcp-token.py enable "$TEST_TOKEN" > /dev/null 2>&1

RESPONSE=$(curl -s -w "\n%{http_code}" -I http://localhost:8080/sse \
  -H "X-MCP-Token: $TEST_TOKEN" \
  -H "X-MCP-UserID: $TEST_USER")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ PASS - Re-enabled token works"
else
    echo "❌ FAIL - Expected 200 after re-enable, got $HTTP_CODE"
    exit 1
fi
echo ""

# Cleanup
echo "🧹 Cleaning up test token..."
python3 scripts/mcp-token.py delete "$TEST_TOKEN" --yes > /dev/null 2>&1
echo "✅ Test token deleted"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ All Authentication Tests Passed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Authentication system is working correctly"
echo ""
