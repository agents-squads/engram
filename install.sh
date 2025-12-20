#!/bin/bash
# Engram - One-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/agents-squads/engram/main/install.sh | bash

set -e

echo "======================================"
echo "  Installing Engram"
echo "======================================"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required but not installed."; exit 1; }
command -v ollama >/dev/null 2>&1 || { echo "Error: Ollama is required but not installed."; exit 1; }

# Clone repo
INSTALL_DIR="${ENGRAM_INSTALL_DIR:-$HOME/engram}"

if [ -d "$INSTALL_DIR" ]; then
    echo "Engram already exists at $INSTALL_DIR"
    echo "To reinstall, remove it first: rm -rf $INSTALL_DIR"
    exit 1
fi

echo "Cloning Engram to $INSTALL_DIR..."
git clone https://github.com/agents-squads/engram.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Setup config
echo "Creating configuration..."
cp .env.example .env

# Pull Ollama models
echo "Pulling Ollama models (this may take a few minutes)..."
ollama pull qwen3:latest || echo "Warning: Could not pull qwen3, using existing model"
ollama pull nomic-embed-text || echo "Warning: Could not pull nomic-embed-text, using existing model"

# Start services
echo "Starting Engram services..."
./scripts/start.sh

# Run migrations
echo "Setting up authentication..."
./scripts/migrate-auth.sh

echo ""
echo "======================================"
echo "  Engram Installed Successfully!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Create your auth token:"
echo "   cd $INSTALL_DIR && ./scripts/create-token.sh your@email.com \"Your Name\""
echo ""
echo "2. Add to Claude Code (use token from step 1):"
echo "   claude mcp add engram http://localhost:8080/mcp/ -t http \\"
echo "     -H \"X-MCP-Token: YOUR_TOKEN\" \\"
echo "     -H \"X-MCP-UserID: your@email.com\""
echo ""
echo "3. Verify connection:"
echo "   claude mcp list"
echo ""
echo "Documentation: https://github.com/agents-squads/engram"
echo ""
