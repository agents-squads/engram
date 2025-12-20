# Quick Start Guide

## 5-Minute Setup

### Step 1: Prerequisites
```bash
# Check Docker
docker --version
docker compose version

# Check Ollama (if using)
curl http://192.168.1.2:11434/api/tags
```

### Step 2: Configure
```bash
cd /path/to/mem0-mcp
cp .env.example .env
# Edit .env if needed (Ollama URL, etc.)
```

### Step 3: Start
```bash
./scripts/start.sh
```

### Step 4: Setup Authentication

```bash
# Run database migrations
./scripts/migrate-auth.sh

# Create your token
python3 scripts/mcp-token.py create \
  --user-id your.email@company.com \
  --name "Your Name" \
  --email your.email@company.com

# Add to ~/.zshrc or ~/.bashrc
export MEM0_TOKEN='mcp_abc123...'  # From previous command
export MEM0_USER_ID='your.email@company.com'

# Reload shell
source ~/.zshrc  # or ~/.bashrc
```

### Step 5: Connect Claude Code

**Using Claude CLI (Recommended):**
```bash
# HTTP Stream transport (modern, recommended)
claude mcp add mem0 http://localhost:8080/mcp/ -t http \
  -H "X-MCP-Token: ${MEM0_TOKEN}" \
  -H "X-MCP-UserID: ${MEM0_USER_ID}"

# Verify
claude mcp list
```

**Alternative: Manual Configuration**

Add to `~/.config/claude-code/config.json`:
```json
{
  "mcpServers": {
    "mem0": {
      "url": "http://localhost:8080/mcp/",
      "transport": "http",
      "headers": {
        "X-MCP-Token": "your-token-here",
        "X-MCP-UserID": "your.email@company.com"
      }
    }
  }
}
```

Restart Claude Code.

### Step 6: Test
```
Ask Claude: "Store this code in memory: def hello(): return 'world'"
Ask Claude: "Search my memories for Python functions"
```

## That's It!

You now have:
- ✅ PostgreSQL + pgvector running
- ✅ Neo4j graph database running
- ✅ Authentication enabled
- ✅ Mem0 REST API at http://localhost:8000
- ✅ MCP server at http://localhost:8080/mcp (HTTP Stream)
- ✅ Claude Code connected with secure auth

## Next Steps

- View logs: `./scripts/logs.sh`
- Run tests: `./scripts/test.sh`
- Check health: `./scripts/health.sh`
- Read README.md for full documentation
