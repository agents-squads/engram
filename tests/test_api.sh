#!/bin/bash
# Test Mem0 REST API endpoints

set -e

API_URL="http://localhost:8000"
TEST_USER="test_user_$(date +%s)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧪 Testing Mem0 REST API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Test User: $TEST_USER"
echo ""

# Test 1: Health check
echo "✅ Test 1: Health Check"
curl -s "$API_URL/health" | jq .
echo ""

# Test 2: Add memory
echo "✅ Test 2: Add Memory"
curl -s -X POST "$API_URL/memories" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [{\"role\": \"user\", \"content\": \"Test memory: I prefer Python for backend development\"}],
    \"user_id\": \"$TEST_USER\"
  }" | jq .
echo ""

# Test 3: Get all memories
echo "✅ Test 3: Get All Memories"
curl -s "$API_URL/memories?user_id=$TEST_USER" | jq '.results | length'
echo ""

# Test 4: Search memories
echo "✅ Test 4: Search Memories"
curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Python programming\",
    \"user_id\": \"$TEST_USER\"
  }" | jq '.results[] | {memory: .memory, score: .score}'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ API Tests Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
