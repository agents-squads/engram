# Performance Optimization Guide

Complete guide to optimizing the Mem0 MCP Server for speed, scalability, and efficiency.

## Performance Overview

### Typical Performance Characteristics

| Operation | Cold Start | Warm | Notes |
|-----------|-----------|------|-------|
| **Add Memory** | 60-90s | 2-5s | Cold: Model loading |
| **Search** | 60-90s | 1-3s | Cold: Model loading |
| **Get All** | <1s | <1s | No LLM inference |
| **Delete** | <1s | <1s | No LLM inference |
| **History** | <1s | <1s | No LLM inference |

### Factors Affecting Performance

1. **LLM Provider** - Ollama (self-hosted) vs OpenAI (cloud)
2. **Embedding Dimensions** - 768d vs 4096d
3. **HNSW Indexing** - Enabled (<2000d) vs Disabled (>2000d)
4. **Model Size** - 8B vs 3B parameters
5. **Hardware** - CPU, RAM, GPU availability

---

## Quick Wins

### 1. Use Smaller Embedding Model

**Impact:** 10-20x faster embeddings

```bash
# Before (4096 dimensions, no HNSW)
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
OLLAMA_EMBEDDING_DIMS=4096
# Speed: Slow, Accuracy: High

# After (768 dimensions, HNSW enabled)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
# Speed: Fast, Accuracy: Good (95% as good)
```

**Restart required:**
```bash
./scripts/restart.sh
```

---

### 2. Switch to OpenAI

**Impact:** 5-10x faster responses

```bash
# Before: Ollama (self-hosted)
LLM_PROVIDER=ollama
# First request: 60-90s, Subsequent: 2-5s

# After: OpenAI (cloud)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxx
# All requests: 1-2s
```

**Trade-offs:**
- ✅ Much faster
- ✅ No local infrastructure
- ❌ API costs ($0.30 per 1M tokens for embeddings)
- ❌ Data sent to OpenAI
- ❌ Requires internet

---

### 3. Pre-warm Ollama Models

**Impact:** Eliminates cold start (60s → 2s)

```bash
# Keep models in memory (run once after Ollama starts)
curl http://192.168.1.2:11434/api/generate \
  -d '{
    "model": "qwen3:8b",
    "prompt": "warmup",
    "keep_alive": -1
  }'

curl http://192.168.1.2:11434/api/generate \
  -d '{
    "model": "qwen3-embedding:8b",
    "prompt": "warmup",
    "keep_alive": -1
  }'
```

**Automated warmup script:**

Create `scripts/warmup.sh`:
```bash
#!/bin/bash
set -e

echo "Pre-warming Ollama models..."

OLLAMA_URL="${OLLAMA_BASE_URL:-http://192.168.1.2:11434}"
LLM_MODEL="${OLLAMA_LLM_MODEL:-qwen3:8b}"
EMBED_MODEL="${OLLAMA_EMBEDDING_MODEL:-qwen3-embedding:8b}"

# Warmup LLM
echo "Warming up $LLM_MODEL..."
curl -s "$OLLAMA_URL/api/generate" -d "{
  \"model\": \"$LLM_MODEL\",
  \"prompt\": \"warmup\",
  \"keep_alive\": -1
}" > /dev/null

# Warmup embeddings
echo "Warming up $EMBED_MODEL..."
curl -s "$OLLAMA_URL/api/embeddings" -d "{
  \"model\": \"$EMBED_MODEL\",
  \"prompt\": \"warmup\"
}" > /dev/null

echo "✅ Models warmed up and ready"
```

Run after startup:
```bash
chmod +x scripts/warmup.sh
./scripts/warmup.sh
```

---

### 4. Smart Text Chunking (Automatic)

**Impact:** Eliminates timeouts on large text inputs

The MCP server automatically handles large text inputs through intelligent semantic chunking. This feature prevents timeout errors when storing large code files, documentation, or long-form content.

**How It Works:**

```python
# Automatic chunking for text > 1000 characters
# Location: mcp-server/text_chunker.py

max_chunk_size = 1000     # Characters per chunk
overlap_size = 150        # Overlap for context preservation
```

**Processing Flow:**

1. **Small text (≤1000 chars):** Sent directly (fast path, no overhead)
2. **Large text (>1000 chars):** Automatically chunked with:
   - Semantic boundaries (paragraphs → sentences)
   - 150-character overlap between chunks
   - Shared `run_id` for session tracking
   - Full metadata for traceability

**Performance Benefits:**

```bash
# Before chunking (large text)
Status: ❌ Timeout after 30s
Result: Failed to store memory

# After chunking (large text)
Status: ✅ Completed in 45s
Result: Stored as 5 chunks with metadata
Chunks: [Part 1/5] → [Part 5/5]
```

**Chunking Strategy:**

```
Input: 5000-character code file

Step 1: Split by paragraphs (double newlines)
  ↓
Step 2: If paragraph > 1000 chars, split by sentences
  ↓
Step 3: Add 150-char overlap between chunks
  ↓
Result: 5 semantic chunks with context preservation

Chunk 1: chars 0-1000 (no overlap)
Chunk 2: chars 850-1850 (150 overlap from chunk 1)
Chunk 3: chars 1700-2700 (150 overlap from chunk 2)
Chunk 4: chars 2550-3550 (150 overlap from chunk 3)
Chunk 5: chars 3400-5000 (150 overlap from chunk 4)
```

**Timeout Configuration:**

```python
# mcp-server/main.py
http_client = httpx.AsyncClient(
    base_url=config.MEM0_API_URL,
    timeout=180.0  # Extended from 30s to 180s
)
```

**Chunk Metadata:**

Each chunk includes comprehensive tracking:

```json
{
  "chunk_index": 0,           // Position (0-indexed)
  "total_chunks": 5,          // Total chunks
  "chunk_size": 982,          // Characters in chunk
  "has_overlap": true,        // Has overlap from previous
  "run_id": "uuid-shared"     // Same for all chunks
}
```

**When Chunking Triggers:**

- ✅ **Triggered:** Code files, documentation, long explanations (>1000 chars)
- ❌ **Bypassed:** Short snippets, commands, brief notes (≤1000 chars)

**Benefits:**

1. **No Timeouts** - Large text no longer fails after 30s
2. **Context Preserved** - 150-char overlap maintains semantic continuity
3. **Semantic Boundaries** - Splits at paragraphs/sentences, never mid-word
4. **Transparent** - Automatic, users don't need to manually split text
5. **Traceable** - Full metadata for reconstruction
6. **Zero Overhead** - Small texts bypass chunking entirely

**Monitoring Chunking:**

Check MCP server logs to see chunking in action:

```bash
./scripts/logs.sh mcp

# Output:
# 📦 Large text detected: splitting into 5 semantic chunks
# 📤 Sending chunk 1/5 (982 chars)
# ✅ Chunk 1/5 stored successfully
# 📤 Sending chunk 2/5 (1015 chars)
# ✅ Chunk 2/5 stored successfully
# ...
# ✅ Successfully stored 5 chunks for large text
```

**Tuning Chunking (Advanced):**

If you need to adjust chunking behavior, edit `mcp-server/text_chunker.py`:

```python
def chunk_text_semantic(
    text: str,
    max_chunk_size: int = 1000,    # Increase for fewer chunks
    overlap_size: int = 150         # Increase for more context
) -> List[Dict[str, any]]:
```

**Trade-offs:**

- ✅ Larger `max_chunk_size` (e.g., 2000): Fewer chunks, faster processing
- ❌ Larger `max_chunk_size`: Higher risk of timeouts per chunk
- ✅ Larger `overlap_size` (e.g., 300): Better context preservation
- ❌ Larger `overlap_size`: More duplicate content stored

**Recommended settings:** Keep defaults (1000/150) for balanced performance.

---

### 5. Async Architecture (Built-in Performance)

**Impact:** Non-blocking I/O enables concurrent request handling

The Mem0 server uses FastAPI's async/await architecture for optimal performance with background task processing.

**How It Works:**

```python
# mem0-server/main.py:175
@app.post("/memories", summary="Create memories")
async def add_memory(memory_create: MemoryCreate):
    # 1. Synchronous PostgreSQL storage (immediate, <100ms)
    response = MEMORY_INSTANCE.add(messages=..., **params)

    # 2. Async Neo4j sync (background, non-blocking)
    asyncio.create_task(
        _sync_to_neo4j_with_retry(
            memory_id=result["id"],
            memory_text=result["memory"],
            user_id=user_id
        )
    )

    # 3. Immediate response (doesn't wait for graph sync)
    return JSONResponse(content=response)
```

**Performance Benefits:**

1. **Immediate Response** - API returns in <500ms without waiting for Neo4j sync
2. **Non-Blocking I/O** - Multiple requests processed concurrently
3. **Background Processing** - Graph operations don't block memory storage
4. **Automatic Retry** - 7 retry attempts with exponential backoff (1s, 2s, 4s, 8s, 16s, 32s)
5. **Fault Tolerance** - If Neo4j sync fails, memory still accessible via PostgreSQL

**Typical Timing:**

```
User stores memory
  ↓
PostgreSQL write: 50-100ms ✅ User receives response
  ↓
Neo4j sync: 200-500ms (background, non-blocking)
  ↓
Total user-facing latency: <500ms
```

**Without async (blocking approach):**

```
User stores memory
  ↓
PostgreSQL write: 50-100ms
  ↓
Neo4j sync: 200-500ms ❌ User waits
  ↓
Total user-facing latency: 250-600ms
```

**Async Improvement:** ~50% faster response times for memory storage

---

## LLM Provider Comparison

### Ollama (Self-Hosted)

**Pros:**
- 100% self-hosted, no API costs
- Full data privacy
- Works offline
- No rate limits

**Cons:**
- Slower than cloud providers
- Requires local compute resources
- Cold start delay (60-90s)

**Best for:**
- Development
- Privacy-sensitive data
- Cost-conscious projects
- Offline environments

**Performance tuning:**
```bash
# Fast mode
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768

# Accurate mode
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
OLLAMA_EMBEDDING_DIMS=4096
```

---

### OpenAI (Cloud)

**Pros:**
- Very fast (1-2s per request)
- High-quality embeddings
- No infrastructure management
- No cold starts

**Cons:**
- API costs (~$0.30 per 1M tokens)
- Data sent to OpenAI
- Requires internet
- Rate limits (tier-based)

**Best for:**
- Production
- Speed-critical applications
- Small to medium workloads
- Quick prototyping

**Performance config:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxx
OPENAI_LLM_MODEL=gpt-4o-mini  # Fastest
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536
```

---

### Anthropic + Ollama Embeddings (Hybrid)

**Pros:**
- Claude's reasoning quality
- Self-hosted embeddings (no cost)
- Balanced approach

**Cons:**
- Two systems to manage
- Embedding still has cold start
- API costs for LLM

**Best for:**
- High-quality reasoning + cost savings on embeddings
- Privacy for vector data, cloud for LLM

**Performance config:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxx
ANTHROPIC_MODEL=claude-3-5-haiku-20241022  # Fastest Claude

# Ollama for embeddings
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
```

---

## Database Performance

### PostgreSQL Optimization

**1. Connection Pooling**

In `docker-compose.yml`:
```yaml
services:
  postgres:
    environment:
      POSTGRES_MAX_CONNECTIONS: 200
      POSTGRES_SHARED_BUFFERS: 512MB
      POSTGRES_EFFECTIVE_CACHE_SIZE: 2GB
      POSTGRES_WORK_MEM: 16MB
```

**2. Index Optimization**

HNSW is automatically managed, but you can tune:

```sql
-- For HNSW (dimensions <= 2000)
CREATE INDEX ON memories USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- For exact search (dimensions > 2000)
-- Indexes are automatically managed by pgvector
```

**3. Query Performance**

```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Analyze table
ANALYZE memories;
```

---

### Neo4j Optimization

**1. Memory Configuration**

In `docker-compose.yml`:
```yaml
services:
  neo4j:
    environment:
      NEO4J_dbms_memory_heap_initial__size: 1G
      NEO4J_dbms_memory_heap_max__size: 4G
      NEO4J_dbms_memory_pagecache_size: 2G
```

**2. Index Creation**

```cypher
// Create indexes for common queries
CREATE INDEX user_id_index FOR (n:Memory) ON (n.user_id);
CREATE INDEX created_at_index FOR (n:Memory) ON (n.created_at);
```

**3. Query Optimization**

```cypher
// Use PROFILE to analyze queries
PROFILE MATCH (m:Memory {user_id: $userId})
RETURN m
ORDER BY m.created_at DESC;
```

---

## Embedding Dimension Trade-offs

### 384 Dimensions (all-minilm)

**Speed:** ⭐⭐⭐⭐⭐ (Fastest)
**Accuracy:** ⭐⭐⭐ (Basic)
**HNSW:** ✅ Enabled

```bash
OLLAMA_EMBEDDING_MODEL=all-minilm:l6-v2
OLLAMA_EMBEDDING_DIMS=384
```

**Use for:**
- Quick prototyping
- Development iteration
- Non-critical accuracy

---

### 768 Dimensions (nomic-embed-text)

**Speed:** ⭐⭐⭐⭐ (Fast)
**Accuracy:** ⭐⭐⭐⭐ (Good)
**HNSW:** ✅ Enabled

```bash
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
```

**Use for:**
- Development
- Production (balanced)
- Best speed/accuracy trade-off

**Recommended for most users** ✅

---

### 1536 Dimensions (OpenAI text-embedding-3-small)

**Speed:** ⭐⭐⭐⭐ (Fast, cloud)
**Accuracy:** ⭐⭐⭐⭐⭐ (High)
**HNSW:** ✅ Enabled

```bash
LLM_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536
```

**Use for:**
- Production with OpenAI
- High accuracy needed
- Speed is critical

---

### 4096 Dimensions (qwen3-embedding)

**Speed:** ⭐⭐ (Slow)
**Accuracy:** ⭐⭐⭐⭐⭐ (Highest)
**HNSW:** ❌ Disabled (falls back to exact search)

```bash
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
OLLAMA_EMBEDDING_DIMS=4096
```

**Use for:**
- Maximum accuracy
- Research
- When speed is not critical

---

## Scaling Strategies

### Vertical Scaling (Single Server)

**1. Resource Allocation**

```yaml
# docker-compose.override.yml
services:
  mem0:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

**2. SSD Storage**

Mount volumes on SSD for faster I/O:
```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/nvme0n1/postgres
```

---

### Horizontal Scaling (Multiple Servers)

**1. Separate Services**

Run each service on dedicated hardware:
- Server 1: PostgreSQL + Neo4j (storage tier)
- Server 2: Ollama (inference tier)
- Server 3: Mem0 API + MCP (application tier)

**2. Load Balancing**

Add nginx for multiple Mem0 instances:
```nginx
upstream mem0_backend {
    server mem0-1:8000;
    server mem0-2:8000;
    server mem0-3:8000;
}

server {
    listen 8000;
    location / {
        proxy_pass http://mem0_backend;
    }
}
```

---

### Caching Strategies

**1. In-Memory Caching**

Add Redis for frequently accessed memories:
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**2. Application-Level Caching**

In `mem0-server/main.py`:
```python
from cachetools import TTLCache

# Cache for 5 minutes
memory_cache = TTLCache(maxsize=1000, ttl=300)

@app.get("/memories/{memory_id}")
async def get_memory(memory_id: str, user_id: str):
    cache_key = f"{user_id}:{memory_id}"
    if cache_key in memory_cache:
        return memory_cache[cache_key]

    # Fetch from database
    result = MEMORY_INSTANCE.get(memory_id, user_id=user_id)
    memory_cache[cache_key] = result
    return result
```

---

## Monitoring Performance

### 1. Prometheus Metrics

Add metrics to Mem0 server:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
request_count = Counter('mem0_requests_total', 'Total requests', ['endpoint', 'method'])
request_duration = Histogram('mem0_request_duration_seconds', 'Request duration', ['endpoint'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    request_duration.labels(endpoint=request.url.path).observe(duration)
    request_count.labels(endpoint=request.url.path, method=request.method).inc()

    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### 2. Logging Performance

Enable detailed timing logs:

```python
import logging
import time

logger = logging.getLogger(__name__)

@app.post("/memories")
async def create_memory(data: dict):
    start = time.time()

    # LLM processing
    llm_start = time.time()
    result = MEMORY_INSTANCE.add(...)
    llm_time = time.time() - llm_start

    # Vector storage
    db_start = time.time()
    # ... storage operations
    db_time = time.time() - db_start

    total_time = time.time() - start

    logger.info(f"Memory creation: total={total_time:.2f}s, llm={llm_time:.2f}s, db={db_time:.2f}s")

    return result
```

---

### 3. Health Check Performance

Add timing to health checks:

```bash
# scripts/benchmark.sh
#!/bin/bash

echo "Running performance benchmark..."

# Add memory
start=$(date +%s%N)
curl -s -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"user_id":"bench"}' \
  > /dev/null
end=$(date +%s%N)
add_time=$(( (end - start) / 1000000 ))

echo "Add memory: ${add_time}ms"

# Search
start=$(date +%s%N)
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test","user_id":"bench"}' \
  > /dev/null
end=$(date +%s%N)
search_time=$(( (end - start) / 1000000 ))

echo "Search: ${search_time}ms"
```

---

## Hardware Recommendations

### Development Setup

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 20 GB SSD

**Recommended:**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 50 GB NVMe SSD

---

### Production Setup (Ollama)

**Minimum:**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 100 GB SSD
- GPU: Optional (speeds up inference 5-10x)

**Recommended:**
- CPU: 16 cores
- RAM: 32 GB
- Storage: 500 GB NVMe SSD
- GPU: NVIDIA with 8+ GB VRAM (e.g., RTX 3070)

---

### Production Setup (OpenAI)

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD

**Recommended:**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 100 GB SSD

---

## GPU Acceleration (Ollama)

### Enable GPU Support

**1. Install NVIDIA Docker runtime:**
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**2. Update docker-compose.yml:**
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**3. Verify GPU usage:**
```bash
docker exec -it ollama nvidia-smi
```

**Performance gain:** 5-10x faster inference

---

## Benchmarking

### Run Comprehensive Benchmark

```bash
#!/bin/bash
# scripts/full-benchmark.sh

echo "=== Mem0 MCP Performance Benchmark ==="
echo ""

# Warmup
echo "Warming up..."
for i in {1..3}; do
  curl -s -X POST http://localhost:8000/memories \
    -H "Content-Type: application/json" \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":\"warmup $i\"}],\"user_id\":\"bench\"}" \
    > /dev/null
done

echo "Running benchmark (10 iterations)..."
echo ""

# Add memory benchmark
add_times=()
for i in {1..10}; do
  start=$(date +%s%N)
  curl -s -X POST http://localhost:8000/memories \
    -H "Content-Type: application/json" \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":\"benchmark memory $i\"}],\"user_id\":\"bench\"}" \
    > /dev/null
  end=$(date +%s%N)
  time=$(( (end - start) / 1000000 ))
  add_times+=($time)
  echo "Add $i: ${time}ms"
done

# Calculate average
sum=0
for t in "${add_times[@]}"; do
  sum=$((sum + t))
done
avg=$((sum / 10))

echo ""
echo "=== Results ==="
echo "Average add time: ${avg}ms"
```

Run:
```bash
chmod +x scripts/full-benchmark.sh
./scripts/full-benchmark.sh
```

---

## Performance Troubleshooting

### Issue: First Request Takes 60+ Seconds

**Cause:** Ollama loading model into memory

**Solutions:**
1. Pre-warm models (see Quick Wins #3)
2. Switch to OpenAI (instant)
3. Use smaller model

---

### Issue: Search Is Slow (>5s)

**Causes:**
- Large embedding dimensions (4096) with HNSW disabled
- Large dataset (>100k memories)
- Insufficient PostgreSQL resources

**Solutions:**
1. Use smaller embeddings (768d) to enable HNSW
2. Add PostgreSQL indexes
3. Increase PostgreSQL memory

---

### Issue: Memory Usage Growing

**Causes:**
- Ollama keeping models in memory
- PostgreSQL cache growing
- Neo4j heap usage

**Solutions:**
1. Set Ollama keep_alive to finite value
2. Tune PostgreSQL shared_buffers
3. Adjust Neo4j heap size

---

## Performance Comparison

### Configuration A: Fast Development

```bash
LLM_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
```

**Performance:**
- First request: 30-60s (model loading)
- Subsequent: 1-2s
- HNSW: Enabled
- Cost: $0

---

### Configuration B: Maximum Accuracy

```bash
LLM_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
OLLAMA_EMBEDDING_DIMS=4096
```

**Performance:**
- First request: 60-90s (model loading)
- Subsequent: 3-5s
- HNSW: Disabled
- Cost: $0

---

### Configuration C: Production Speed

```bash
LLM_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536
```

**Performance:**
- All requests: 1-2s
- HNSW: Enabled
- Cost: ~$0.30 per 1M tokens

---

## Recommended Configurations

### For Development
```bash
LLM_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
PROJECT_ID_MODE=global
```

### For Production (Self-Hosted)
```bash
LLM_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b
OLLAMA_EMBEDDING_DIMS=4096
PROJECT_ID_MODE=auto
```
*Pre-warm models, use GPU if available*

### For Production (Cloud)
```bash
LLM_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536
PROJECT_ID_MODE=auto
```

---

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
