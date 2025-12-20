#!/bin/bash
# Clean Mem0 MCP Stack (removes all data)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧹 Clean Mem0 MCP Stack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  WARNING: This will remove ALL data including:"
echo "   - All memories and vectors"
echo "   - PostgreSQL database"
echo "   - Neo4j graph data"
echo "   - History files"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🛑 Stopping services..."
docker compose down

echo ""
echo "🗑️  Removing volumes..."
docker compose down -v

echo ""
echo "🧹 Cleaning history files..."
rm -rf history/*.db history/*.db-wal history/*.db-shm

echo ""
echo "✅ Clean complete!"
echo ""
echo "💡 To start fresh: ./scripts/start.sh"
echo ""
