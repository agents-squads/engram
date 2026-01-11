# Engram Roadmap

> Persistent memory for AI agents — local-first, privacy-respecting, built on open standards.

## Vision

Engram becomes the memory layer for the agents-squads ecosystem:
- **Unified infrastructure** with squads-cli
- **MemoryML** for declarative memory modeling
- **Cross-agent memory** sharing within squads

---

## Current State: v0.1.0

### Implemented
- MCP Server with 5 core tools
- mem0 integration for memory extraction
- PostgreSQL + pgvector for vector storage
- Token-based authentication
- Smart text chunking (semantic boundaries)
- Auto-capture hooks for conversations

### Open Issues
- [#1](https://github.com/agents-squads/engram/issues/1) Memory export/import
- [#2](https://github.com/agents-squads/engram/issues/2) Memory deduplication

---

## v0.2.0 — Infrastructure Integration

**Theme**: Engram becomes a first-class citizen in squads-cli infrastructure.

### Goals
1. Single `squads local start` command runs everything
2. Shared services (no duplication)
3. Unified telemetry through squads-bridge

### Changes

#### squads-cli (docker/docker-compose.yml)

| Change | Details |
|--------|---------|
| Upgrade postgres | `postgres:16-alpine` → `pgvector/pgvector:pg17` |
| Add mem0 service | Port 8000, depends on postgres |
| Add engram-mcp service | Port 8080, depends on mem0 |
| Add pgvector init | Create extension in init script |

```yaml
# New services to add
mem0:
  build:
    context: ../engram/mem0-server
  container_name: squads-mem0
  environment:
    DATABASE_URL: postgresql://squads:squads@postgres:5432/engram
  ports:
    - "8000:8000"
  depends_on:
    postgres:
      condition: service_healthy

engram-mcp:
  build:
    context: ../engram/mcp-server
  container_name: squads-engram-mcp
  environment:
    MEM0_API_URL: http://mem0:8000
    POSTGRES_HOST: postgres
    POSTGRES_PORT: 5432
    POSTGRES_USER: squads
    POSTGRES_PASSWORD: squads
    POSTGRES_DB: engram
  ports:
    - "8080:8080"
  depends_on:
    - mem0
```

#### engram

| Change | Details |
|--------|---------|
| Deprecate docker-compose.yml | Keep for standalone dev only |
| Update .env.example | Point to squads-cli ports |
| Update README | Document `squads local start` requirement |
| Add health check endpoint | For squads-cli integration |

#### CLI commands

```bash
squads local start              # Full stack including Engram
squads local start --lite       # Core only (postgres, redis, bridge)
squads local start --no-memory  # Skip mem0 + engram-mcp
squads local status             # Show all service health
```

### Database Schema

```sql
-- Add to squads-cli/docker/init-db.sql
CREATE DATABASE engram;
\c engram
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Migration Path

1. Users with existing engram data:
   ```bash
   # Export from old stack
   cd engram && ./scripts/export.sh

   # Start new unified stack
   squads local start

   # Import to new stack
   ./scripts/import.sh
   ```

2. New users: Just `squads local start`

### Deliverables

- [ ] PR: squads-cli infrastructure changes
- [ ] PR: engram config updates
- [ ] PR: squads-cli `local` command enhancements
- [ ] Docs: Migration guide
- [ ] Test: Full integration test

---

## v0.3.0 — Memory Intelligence

**Theme**: Smarter memory with automatic entity extraction and relationship inference.

### Features

#### Entity Extraction
Auto-detect and categorize entities in memories:
- People (names, roles)
- Organizations (companies, teams)
- Technologies (languages, frameworks, tools)
- Concepts (patterns, architectures)

```python
# Input
"Jorge prefers TypeScript and uses Claude Code for development"

# Extracted entities
- Person: Jorge
- Technology: TypeScript
- Tool: Claude Code
- Preference: Jorge → prefers → TypeScript
```

#### Relationship Inference
Automatically create graph edges based on content analysis:
- Co-occurrence in same memory
- Semantic similarity above threshold
- Temporal proximity (same session)

#### Memory Deduplication (#2)
- Detect near-duplicate memories
- Merge or link duplicates
- Configurable similarity threshold

### Technical Approach

```yaml
# New config in .env
ENTITY_EXTRACTION_ENABLED=true
ENTITY_EXTRACTION_MODEL=ollama/qwen3:latest  # or openai/gpt-4o-mini
RELATIONSHIP_INFERENCE_ENABLED=true
SIMILARITY_THRESHOLD=0.85
DEDUP_ENABLED=true
DEDUP_THRESHOLD=0.95
```

### New MCP Tools

| Tool | Description |
|------|-------------|
| `extract_entities` | Manually trigger entity extraction on a memory |
| `find_duplicates` | Find potential duplicate memories |
| `merge_memories` | Merge two memories into one |
| `get_entities` | Get all entities of a type |

### Deliverables

- [ ] Entity extraction pipeline
- [ ] Relationship inference engine
- [ ] Deduplication algorithm
- [ ] New MCP tools
- [ ] Configuration options
- [ ] Tests

---

## v0.4.0 — Export/Import & Multi-Agent

**Theme**: Memory portability and squad-level sharing.

### Memory Export/Import (#1)

```bash
# CLI commands
engram export --format json-ld --output memories.jsonld
engram export --format json --output memories.json
engram import --file memories.jsonld

# MCP tools
export_memories(format="json-ld", filter={...})
import_memories(file_path="...")
```

#### JSON-LD Format
```json
{
  "@context": "https://engram.dev/schema/context.jsonld",
  "@graph": [
    {
      "@type": "Semantic",
      "id": "urn:engram:memory:...",
      "content": "User prefers TypeScript",
      "entity_type": "preference",
      "relationships": [...]
    }
  ]
}
```

### Multi-Agent Memory

#### Squad Isolation
Each agent gets isolated memory namespace:
```
memories/
├── agent:claude-code/     # Personal memories
├── agent:cursor/          # Personal memories
└── squad:engineering/     # Shared squad memories
```

#### Cross-Agent Sharing
```python
# Share a memory with the squad
share_memory(memory_id, scope="squad:engineering")

# Search across squad memories
search_memories(query, scope="squad:engineering")
```

### Deliverables

- [ ] Export/import CLI commands
- [ ] Export/import MCP tools
- [ ] JSON-LD schema definition
- [ ] Agent namespace isolation
- [ ] Squad sharing mechanism
- [ ] Access control (who can read/write squad memories)

---

## v0.5.0 — Memory Lifecycle

**Theme**: Automatic memory management over time.

### Rolling Summaries
Compress old memories while preserving key information:

```yaml
retention:
  raw_memories: 30d          # Keep full text for 30 days
  summarized_after: 30d      # Summarize after 30 days
  archived_after: 90d        # Archive after 90 days
  deleted_after: 365d        # Delete after 1 year
```

### Conflict Detection
Identify contradictory memories:
```
Memory A: "Project uses PostgreSQL"
Memory B: "Project uses MySQL"
→ Conflict detected, flagged for review
```

### Importance Decay
Reduce importance score over time for unused memories:
```python
importance = base_importance * decay_factor^(days_since_access)
```

### Deliverables

- [ ] Summarization pipeline
- [ ] Conflict detection algorithm
- [ ] Importance decay system
- [ ] Archival to cold storage
- [ ] Retention policy configuration

---

## v1.0.0 — MemoryML

**Theme**: Declarative memory modeling language.

### Overview

MemoryML (spec: `docs/spec/MEMORYML_SPEC.md`) provides:
- Schema-first memory definitions
- Backend-agnostic storage
- Hybrid retrieval strategies
- Policy-driven lifecycle

### Implementation Phases

#### Phase 1: Schema Validation
- Parse `.mml` files
- Validate memory against schema
- Add `memory_type` field to existing API

#### Phase 2: Backend Abstraction
- Create backend interface
- Wrap pgvector operations
- Configuration-based backend selection

#### Phase 3: Explore Engine
- Implement explore parser
- Build hybrid retrieval
- Token budget management
- Query optimization

#### Phase 4: Full MML
- CLI tooling (`engram validate`, `engram migrate`)
- Test framework
- Documentation generator
- TypeScript type generation

### File Structure
```
memory/
├── memory.yaml           # Project config
├── types/
│   ├── episodic.mml      # Time-stamped events
│   ├── semantic.mml      # Facts and knowledge
│   └── procedural.mml    # Skills and patterns
├── explores/
│   └── project_context.mml
├── backends/
│   ├── development.yaml
│   └── production.yaml
└── policies/
    ├── retention.yaml
    └── privacy.yaml
```

### Deliverables

- [ ] MML parser
- [ ] Schema validator
- [ ] Backend abstraction layer
- [ ] Explore engine
- [ ] CLI tools
- [ ] Migration from v0.x

---

## Release Timeline

| Version | Theme | Target |
|---------|-------|--------|
| v0.2.0 | Infrastructure Integration | Q1 2026 |
| v0.3.0 | Memory Intelligence | Q1 2026 |
| v0.4.0 | Export/Import & Multi-Agent | Q2 2026 |
| v0.5.0 | Memory Lifecycle | Q2 2026 |
| v1.0.0 | MemoryML | Q3 2026 |

---

## How to Contribute

1. Check [open issues](https://github.com/agents-squads/engram/issues)
2. Pick a milestone feature
3. Discuss approach in issue before coding
4. Submit PR with tests

---

## Related Projects

- [squads-cli](https://github.com/agents-squads/squads-cli) — CLI for managing agent squads
- [agents-squads](https://github.com/agents-squads/agents-squads) — Framework template

---

*Last updated: 2026-01-04*
