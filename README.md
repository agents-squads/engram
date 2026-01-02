# Engram

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-required-blue)](https://docker.com)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-orange)](https://agents-squads.github.io/engram)

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
- **Observable** — Langfuse integration for traces, costs, and analytics.

## Engram vs mem0

Engram is built on [mem0](https://mem0.ai), extending it for agentic workflows:

| Feature | mem0 | Engram |
|---------|------|--------|
| API | REST only | REST + **MCP** (Claude Code native) |
| Graph | Basic | **Neo4j** (full knowledge graph) |
| Hosting | Cloud or self-host | **Local-first** (your machine, always) |
| Capture | Manual | **Auto-hooks** (conversations captured automatically) |
| Multi-agent | Single user | **Squad isolation** + cross-squad sharing |
| Observability | Limited | **Langfuse** (traces, evals, analytics) |

**In short:** mem0 is a great memory API. Engram wraps it with MCP integration, a real knowledge graph, auto-capture hooks, and local-first architecture.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Ollama: `ollama pull qwen3:latest && ollama pull nomic-embed-text`

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

### Enable Auto-Capture

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

## Observability

Engram integrates with [Langfuse](https://langfuse.com) for tracing, evals, and analytics.

Key operations traced:
- `memory.add` — Full memory creation (LLM extraction + embedding + storage)
- `memory.search` — Vector search + graph enrichment
- `graph.sync` — Neo4j synchronization
- `graph.enrich` — Graph context enrichment for search results

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

## MemoryML (Coming Soon)

A declarative memory modeling language:

```yaml
schema: project_context
version: 1.0

fields:
  name: string
  stack: string[]
  decisions: relation[decision]

retrieval:
  vector: 0.4
  graph: 0.4
  recency: 0.2
```

Define how your agent remembers in YAML. Validate before storage. Export as JSON-LD.

[Read the spec →](https://agents-squads.github.io/engram/spec)

## Roadmap

- [ ] Entity extraction (auto-detect people, companies, concepts)
- [ ] Relationship inference (auto-connect related memories)
- [ ] Rolling summaries (compress old memories)
- [ ] Multi-agent memory sharing
- [ ] Conflict detection and resolution
- [ ] MemoryML implementation

## Philosophy

1. **Owned by you** — Your data, your machine, your control
2. **Transparent** — See what's stored, how it's connected
3. **Open** — Built on open standards, open source
4. **Useful** — Actually makes AI assistants better

## Ecosystem

| Project | Description |
|---------|-------------|
| [squads-cli](https://github.com/agents-squads/squads-cli) | CLI for managing agent squads |
| [agents-squads](https://github.com/agents-squads/agents-squads) | Full framework with infrastructure |

## Credits

Built on [mem0](https://mem0.ai).

## License

[MIT](LICENSE)

---

Built by [Agents Squads](https://agents-squads.com) — AI systems you can learn, understand, and trust.
