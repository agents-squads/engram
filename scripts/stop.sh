#!/bin/bash
# Stop Mem0 MCP Stack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🛑 Stopping Mem0 MCP Stack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

docker compose down

echo ""
echo "✅ All services stopped"
echo ""
echo "💡 To remove all data (volumes), run: ./scripts/clean.sh"
echo ""
