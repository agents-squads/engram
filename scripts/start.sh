#!/bin/bash
# Start Mem0 MCP Stack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Starting Mem0 MCP Stack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update with your settings."
    echo ""
    echo "📝 Important: Update OLLAMA_BASE_URL in .env if needed"
    echo "   Default: http://192.168.1.2:11434"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit and edit .env..."
fi

# Start services
echo "📦 Starting services..."
docker compose up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service health
echo ""
echo "🔍 Service Status:"
docker compose ps

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Mem0 MCP Stack Started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📡 Endpoints:"
echo "   Mem0 API:     http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   MCP SSE:      http://localhost:8080/sse"
echo "   Neo4j:        http://localhost:7474"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:    ./scripts/logs.sh"
echo "   Run tests:    ./scripts/test.sh"
echo "   Health check: ./scripts/health.sh"
echo "   Stop stack:   ./scripts/stop.sh"
echo ""
echo "💡 Connect Claude Code to: http://localhost:8080/sse"
echo ""
