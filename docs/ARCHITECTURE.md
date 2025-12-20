# Architecture Overview

## System Components

### 1. PostgreSQL + pgvector
- **Purpose:** Vector storage for semantic search
- **Version:** PostgreSQL 17 with pgvector extension
- **Configuration:** Auto-adjusts dimensions based on embedding model
- **HNSW:** Automatically disabled for >2000 dimensions

### 2. Neo4j
- **Purpose:** Graph database for relationship tracking
- **Version:** 5.26.4 with APOC plugin
- **Access:** http://localhost:7474 (neo4j/mem0graph)

### 3. Mem0 Server
- **Technology:** FastAPI (Python 3.12)
- **Purpose:** REST API for memory operations
- **Features:**
  - Multi-LLM support (Ollama/OpenAI/Anthropic)
  - Smart embedding dimension detection
  - Automatic HNSW toggle
  - Comprehensive error handling
  - **Async/await architecture** - All memory endpoints use async for non-blocking Neo4j sync
  - **Background task processing** - Neo4j sync runs asynchronously with retry logic

### 4. MCP Server
- **Technology:** FastMCP with SSE transport
- **Purpose:** Model Context Protocol integration for Claude Code
- **Features:**
  - 5 production-ready tools
  - Project isolation (3 modes)
  - HTTP client with retry logic
  - Health monitoring

## Data Flow

```
Claude Code
    ↓ (MCP Tool Call)
MCP Server
    ↓ (HTTP REST)
Mem0 Server
    ↓ (Query/Store)
PostgreSQL (vectors) + Neo4j (graphs)
    ↑
Ollama/OpenAI (LLM + Embeddings)
```

## Networking

All services communicate via Docker bridge network `mem0_network`:
- Internal DNS resolution
- Isolated from host
- Exposed ports: 5432, 7474, 7687, 8000, 8080

## Storage

### Volumes
- `postgres_data`: PostgreSQL database
- `neo4j_data`: Neo4j graph data
- `./history`: SQLite history files (host mount)

### Data Persistence
- Memories survive container restarts
- Use `./scripts/clean.sh` to remove all data

## Async Architecture

### Background Neo4j Sync

**Implementation:** `mem0-server/main.py:64-114`

When memories are created via `/memories` endpoint:
1. Memory is stored in PostgreSQL (synchronous, immediate)
2. Background task spawned for Neo4j sync (asynchronous, non-blocking)
3. Client receives immediate response (doesn't wait for graph sync)

**Key Points:**
- **Async endpoint required:** The `/memories` endpoint must be `async def` to support `asyncio.create_task()`
- **Event loop dependency:** Background tasks require an active event loop (provided by FastAPI's async context)
- **Retry logic:** 7 retry attempts with exponential backoff (1s, 2s, 4s, 8s, 16s, 32s)
- **Total timeout:** ~63 seconds max before giving up on sync

**Code Structure:**
```python
@app.post("/memories", summary="Create memories")
async def add_memory(memory_create: MemoryCreate):  # ✅ Must be async
    # 1. Synchronous storage to PostgreSQL
    response = MEMORY_INSTANCE.add(messages=..., **params)

    # 2. Async background sync to Neo4j (non-blocking)
    if response.get("results"):
        for result in response["results"]:
            asyncio.create_task(  # Requires async context
                _sync_to_neo4j_with_retry(
                    memory_id=result["id"],
                    memory_text=result["memory"],
                    user_id=user_id,
                    metadata=metadata
                )
            )

    # 3. Immediate response (doesn't wait for Neo4j)
    return JSONResponse(content=response)
```

**Error Handling:**
- If Neo4j sync fails after all retries, error is logged but doesn't affect response
- Memory still accessible via PostgreSQL (vector search)
- Graph features unavailable until manual sync: `POST /graph/sync?memory_id={id}`

### FastAPI Async Benefits

1. **Non-blocking I/O:** Multiple requests processed concurrently
2. **Background tasks:** Long-running operations don't block responses
3. **Efficient resource usage:** Single thread handles many connections
4. **Compatible with asyncpg:** Async PostgreSQL driver for auth
5. **Compatible with httpx:** Async HTTP client for MCP server

## Security

- Default passwords (MUST change for production)
- No external network exposure by default
- Health checks for all services
- Proper dependency ordering
