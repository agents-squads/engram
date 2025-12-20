# Engram

**Persistent memory for AI agents.** Local-first, privacy-respecting, built on open standards.

```
You: "Remember that I prefer TypeScript over JavaScript"
     ↓
[Engram extracts, stores, connects]
     ↓
Next session: "I know you prefer TypeScript. Should I use it for this project?"
```

## Why Engram?

AI assistants forget everything between sessions. Engram fixes that.

- **Local-first** — Your memories stay on your machine. No cloud dependency.
- **Semantic search** — Find memories by meaning, not just keywords.
- **Auto-capture** — Hooks capture conversations automatically.
- **Knowledge graph** — Memories connect to each other, building understanding over time.
- **Multi-agent ready** — Each agent gets isolated memory. Squads share knowledge.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Ollama with models: `ollama pull qwen3:latest && ollama pull nomic-embed-text`

### Install

```bash
git clone https://github.com/agents-squads/engram.git
cd engram
cp .env.example .env
./scripts/start.sh
```

### Connect to Claude Code

```bash
# Create your auth token
./scripts/migrate-auth.sh
./scripts/create-token.sh your@email.com "Your Name"

# Add to Claude Code (token printed by previous command)
claude mcp add engram http://localhost:8080/mcp/ -t http \
  -H "X-MCP-Token: YOUR_TOKEN" \
  -H "X-MCP-UserID: your@email.com"
```

### Enable Auto-Capture (Optional)

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 ~/engram/hooks/capture_conversation.py"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "python3 ~/engram/hooks/capture_conversation.py"}]}]
  }
}
```

Now every conversation is automatically captured and stored.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                       ENGRAM                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Capture   │───▶│   Extract   │───▶│    Store    │  │
│  │   (Hooks)   │    │   (Ollama)  │    │  (pgvector) │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│                                               │          │
│                                               ▼          │
│                                        ┌─────────────┐  │
│                                        │    Link     │  │
│                                        │   (Neo4j)   │  │
│                                        └─────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

1. **Capture** — Hooks automatically capture conversations
2. **Extract** — LLM extracts key facts from raw text
3. **Store** — Facts embedded and stored in PostgreSQL + pgvector
4. **Link** — Knowledge graph connects related memories in Neo4j

## Architecture

| Component | Port | Purpose |
|-----------|------|---------|
| PostgreSQL + pgvector | 5433 | Vector storage for semantic search |
| Neo4j | 7474 | Knowledge graph for relationships |
| Engram API | 8000 | REST API for memory operations |
| MCP Server | 8080 | Claude Code integration |

## MCP Tools

Once connected, Claude has access to:

| Tool | Description |
|------|-------------|
| `add_coding_preference` | Store a memory |
| `search_coding_preferences` | Semantic search |
| `get_all_coding_preferences` | List all memories |
| `link_memories` | Connect two memories |
| `get_related_memories` | Graph traversal |
| `analyze_memory_intelligence` | Health report |

## Configuration

Edit `.env` to customize:

```bash
# LLM Provider (ollama = free, local)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_LLM_MODEL=qwen3:latest
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
OLLAMA_EMBEDDING_DIMS=768

# Or use OpenAI (paid)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
```

## Commands

```bash
./scripts/start.sh      # Start all services
./scripts/stop.sh       # Stop all services
./scripts/logs.sh       # View logs
./scripts/health.sh     # Check service health
./scripts/test.sh       # Run tests
```

## Roadmap

- [ ] Entity extraction (auto-detect people, companies, concepts)
- [ ] Relationship inference (auto-connect related memories)
- [ ] Rolling summaries (compress old memories)
- [ ] Multi-agent memory sharing
- [ ] Conflict detection and resolution
- [ ] Memory evolution tracking

## Philosophy

We believe AI memory should be:

1. **Owned by you** — Your data, your machine, your control
2. **Transparent** — See what's stored, how it's connected
3. **Open** — Built on open standards, open source
4. **Useful** — Actually makes AI assistants better

## Credits

Built on [mem0](https://mem0.ai).

## License

MIT License — use it, modify it, share it.

---

**Built by [agents-squads](https://agents-squads.com)** — AI systems you can learn, understand, and trust.
