#!/bin/bash
# Test MCP Server

set -e

MCP_URL="http://localhost:8080"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧪 Testing MCP Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Health check
echo "✅ Test 1: Health Check"
curl -s "$MCP_URL/" | jq .
echo ""

# Test 2: SSE endpoint availability
echo "✅ Test 2: SSE Endpoint Check"
echo -n "   SSE endpoint: "
if curl -s -I "$MCP_URL/sse" | grep -q "405\|200"; then
    echo "✅ Available"
else
    echo "❌ Not Available"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ MCP Tests Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 To test MCP tools, use Claude Code with:"
echo "   SSE URL: http://localhost:8080/sse"
echo ""
