# Troubleshooting Guide

## Common Issues

### 0. Authentication Issues

See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed authentication troubleshooting.

**Quick fixes:**

```bash
# Verify environment variables
echo $MEM0_TOKEN
echo $MEM0_USER_ID

# List tokens
python3 scripts/mcp-token.py list

# Test authentication
./tests/test_auth.sh

# Remove and re-add server
claude mcp remove mem0
claude mcp add mem0 http://localhost:8080/mcp/ -t http \
  -H "X-MCP-Token: ${MEM0_TOKEN}" \
  -H "X-MCP-UserID: ${MEM0_USER_ID}"
```

### 1. Services Won't Start

**Symptoms:** Docker containers fail to start or are unhealthy

**Solutions:**
```bash
# Check logs
./scripts/logs.sh

# Check ports
lsof -i :5432  # PostgreSQL
lsof -i :8000  # Mem0 API
lsof -i :8080  # MCP Server

# Clean and restart
./scripts/clean.sh
./scripts/start.sh
```

### 2. Slow Memory Operations

**Symptoms:** Memory creation takes 60+ seconds

**Causes:**
- Ollama model loading (first request)
- Large embedding dimensions (4096)
- HNSW disabled

**Solutions:**
```bash
# Use smaller embedding model
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768

# Or switch to OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 3. Can't Connect to Ollama

**Symptoms:** "Failed to connect to Ollama" errors

**Solutions:**
```bash
# Test Ollama connectivity
curl http://192.168.1.2:11434/api/tags

# Verify models are pulled
ollama list | grep qwen3

# Check from inside container
docker compose exec mem0 curl http://192.168.1.2:11434/api/tags

# Update OLLAMA_BASE_URL in .env
```

### 4. Dimension Mismatch Errors

**Error:** `expected 1536 dimensions, not 4096`

**Solution:**
Already fixed in this package! The config auto-detects dimensions.
If you still see this, ensure `.env` has:
```bash
OLLAMA_EMBEDDING_DIMS=4096  # Match your model
```

### 5. HNSW Index Error

**Error:** `column cannot have more than 2000 dimensions for hnsw index`

**Solution:**
Already fixed! HNSW auto-disables for >2000 dims.
For faster search, use smaller model:
```bash
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
```

### 6. Claude Code Can't Connect

**Symptoms:** MCP tools not available in Claude Code

**Solutions:**
1. Verify endpoints:
   ```bash
   # HTTP Stream (recommended)
   curl -v http://localhost:8080/mcp/

   # SSE (legacy)
   curl -v http://localhost:8080/sse/
   ```

2. Check MCP config with authentication:
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

3. Verify using CLI:
   ```bash
   claude mcp list
   # Should show mem0 with "✓ Connected"
   ```

4. Restart Claude Code after config changes

5. Check MCP server logs:
   ```bash
   ./scripts/logs.sh mcp
   ```

6. Verify authentication:
   ```bash
   echo $MEM0_TOKEN
   echo $MEM0_USER_ID
   ```

### 7. Database Connection Errors

**Symptoms:** "Could not connect to database"

**Solutions:**
```bash
# Check PostgreSQL
docker compose exec postgres pg_isready -U postgres

curl http://localhost:7474

# Restart services
./scripts/restart.sh
```

---

## Smart Text Chunking Issues

### Issue: Timeout Storing Large Text

**Symptoms:**
- Storing large code files (>1000 characters) times out
- Error: "HTTP 408 - Timeout" or "Request timeout after 180s"
- MCP tool doesn't respond after long wait

**Causes:**
1. Embedding model is very slow (8B+ models)
2. Too many chunks created (very large text)
3. Timeout setting too low
4. Network issues between MCP server and Mem0 API

**Solutions:**

**1. Use faster embedding model:**
```bash
# Edit .env
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768

# Restart services
./scripts/restart.sh
```

**2. Increase timeout (if needed):**
```python
# Edit mcp-server/main.py (line ~700)
http_client = httpx.AsyncClient(
    base_url=config.MEM0_API_URL,
    timeout=300.0  # Increase from 180s to 300s (5 minutes)
)

# Rebuild MCP server
docker compose build mcp
docker compose restart mcp
```

**3. Use larger chunks (faster but riskier):**
```python
# Edit mcp-server/text_chunker.py
def chunk_text_semantic(
    text: str,
    max_chunk_size: int = 2000,  # Increase from 1000
    overlap_size: int = 150
):
```

**4. Switch to OpenAI (fastest):**
```bash
# Edit .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536

./scripts/restart.sh
```

**5. Monitor chunking progress:**
```bash
# Watch logs in real-time
./scripts/logs.sh mcp -f

# You should see:
# 📦 Large text detected: splitting into 5 semantic chunks
# 📤 Sending chunk 1/5 (982 chars)
# ✅ Chunk 1/5 stored successfully
# ...
```

---

### Issue: Too Many Chunks Created

**Symptoms:**
- Large text split into 20+ chunks
- Very slow storage time
- Hard to search/retrieve chunked memories

**Causes:**
- Very large input text (10,000+ characters)
- Small chunk size (1000 chars default)

**Solutions:**

**1. Increase chunk size:**
```python
# Edit mcp-server/text_chunker.py
max_chunk_size = 2000  # Double the chunk size
```

**2. Store text in sections manually:**
Instead of:
```
"Store this entire 50-page document in memory: [paste all]"
```

Do:
```
"Store this intro section: [section 1]"
"Store the implementation details: [section 2]"
"Store the API reference: [section 3]"
```

**3. Check logs to see chunk count:**
```bash
./scripts/logs.sh mcp | grep "semantic chunks"
# Example: 📦 Large text detected: splitting into 25 semantic chunks
```

---

### Issue: Context Lost Between Chunks

**Symptoms:**
- Search returns incomplete results
- Code snippets broken across chunks
- Missing context when retrieving memories

**Causes:**
- Insufficient overlap between chunks (150 chars default)
- Text split at bad boundaries

**Solutions:**

**1. Increase overlap:**
```python
# Edit mcp-server/text_chunker.py
overlap_size = 300  # Double the overlap from 150
```

**2. Verify overlap in chunk metadata:**
```bash
# Search for chunked memory
# Check metadata shows has_overlap: true

# Example response:
{
  "chunk_index": 1,
  "total_chunks": 5,
  "has_overlap": true  # ← Should be true for chunks 2-5
}
```

**3. Use run_id to find related chunks:**
When searching returns partial results, check the `run_id` metadata to find all related chunks from the same storage operation.

---

### Issue: Chunking Not Triggering

**Symptoms:**
- Large text (>1000 chars) stored as single memory
- Timeout occurs without chunking
- No "splitting into N chunks" log message

**Causes:**
- Chunking code not active
- text_chunker.py not included in build
- Old version running

**Solutions:**

**1. Verify chunking code is active:**
```bash
# Check logs for chunking
./scripts/logs.sh mcp | grep -i chunk

# Should see imports and chunking logic
```

**2. Verify text_chunker.py exists:**
```bash
# Check file exists
ls -la mcp-server/text_chunker.py

# Check it's included in Dockerfile
grep text_chunker mcp-server/Dockerfile
```

**3. Rebuild MCP server:**
```bash
docker compose build mcp
docker compose restart mcp
./scripts/logs.sh mcp
```

**4. Test chunking manually:**
```bash
# Store a test with >1000 characters
# Check logs for chunking activity

# You should see:
# 📦 Large text detected: splitting into N semantic chunks
```

---

### Issue: Chunk Metadata Missing

**Symptoms:**
- Chunks stored but no metadata
- Can't tell which chunks belong together
- No `run_id` or `chunk_index` in responses

**Causes:**
- Metadata not passed to API
- Old API version
- Database issue

**Solutions:**

**1. Check API version:**
```bash
curl http://localhost:8000/health

# Should show metadata support
```

**2. Verify metadata in logs:**
```bash
./scripts/logs.sh mcp -f

# Look for metadata in payload:
# "metadata": {
#   "chunk_index": 0,
#   "total_chunks": 5,
#   ...
# }
```

**3. Check database storage:**
```bash
docker compose exec postgres psql -U postgres -d postgres

# Query metadata
SELECT id, payload->'metadata' FROM memories
WHERE payload->'metadata' ? 'chunk_index'
LIMIT 5;
```

---

### Issue: Slow Chunking Performance

**Symptoms:**
- Each chunk takes 10+ seconds to process
- Overall storage time very long (minutes)
- CPU/memory high during chunking

**Causes:**
- Slow embedding model (8B parameters)
- HNSW disabled (>2000 dimensions)
- Insufficient server resources

**Solutions:**

**1. Use faster embedding model:**
```bash
# Fastest (768 dims, HNSW enabled)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIMS=768
```

**2. Pre-warm Ollama models:**
```bash
./scripts/warmup.sh

# Or manually:
curl http://192.168.1.2:11434/api/generate \
  -d '{"model": "qwen3:8b", "prompt": "warmup", "keep_alive": -1}'
```

**3. Monitor performance:**
```bash
# Watch chunk processing time
./scripts/logs.sh mcp -f | grep "Chunk.*stored"

# Each chunk should complete in 2-5 seconds
# If >10 seconds per chunk, switch to faster model
```

**4. Use OpenAI (fastest option):**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxx

# Chunks process in 1-2 seconds each
```

---

### Debugging Chunking

**Enable detailed chunking logs:**

```python
# Edit mcp-server/text_chunker.py
# Add verbose logging

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def chunk_text_semantic(text: str, ...):
    logger.debug(f"Input text length: {len(text)}")
    logger.debug(f"Chunk threshold: {max_chunk_size}")
    logger.debug(f"Overlap size: {overlap_size}")

    # ... chunking logic ...

    logger.debug(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        logger.debug(f"Chunk {i}: size={chunk['chunk_size']}, overlap={chunk.get('has_overlap')}")
```

**Test chunking locally:**

```python
# Test chunking algorithm directly
docker compose exec mcp python3 -c "
from text_chunker import chunk_text_semantic

text = 'A' * 5000  # 5000 character test
chunks = chunk_text_semantic(text, max_chunk_size=1000, overlap_size=150)

print(f'Total chunks: {len(chunks)}')
for chunk in chunks:
    print(f'Chunk {chunk[\"chunk_index\"]}: {chunk[\"chunk_size\"]} chars, overlap={chunk.get(\"has_overlap\")}')
"
```

**Monitor chunking in production:**

```bash
# Real-time monitoring
watch -n 1 './scripts/logs.sh mcp | tail -20'

# Count successful chunks
./scripts/logs.sh mcp | grep "Chunk.*stored successfully" | wc -l

# Find failed chunks
./scripts/logs.sh mcp | grep -i "error.*chunk"
```

---

## Backend/Development Issues

### Issue: "no running event loop" Error

**Symptoms:**
- Error: `RuntimeError: no running event loop`
- HTTP 500 errors when storing memories
- Logs show: `asyncio.create_task()` error in `add_memory` function

**Error Details:**
```python
File "/app/main.py", line 208, in add_memory
    asyncio.create_task(
File "/usr/local/lib/python3.12/asyncio/tasks.py", line 417, in create_task
    loop = events.get_running_loop()
           ^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: no running event loop
```

**Root Cause:**
`asyncio.create_task()` was called from a synchronous function (`def add_memory`) which doesn't have an event loop. Background tasks with `asyncio.create_task()` require the parent function to be async.

**Solution:**

**Fixed in:** `mem0-server/main.py:175`
```python
# BEFORE (incorrect - causes error)
@app.post("/memories", summary="Create memories")
def add_memory(memory_create: MemoryCreate):
    ...
    asyncio.create_task(...)  # ❌ Error: no event loop

# AFTER (correct - async function)
@app.post("/memories", summary="Create memories")
async def add_memory(memory_create: MemoryCreate):
    ...
    asyncio.create_task(...)  # ✅ Works correctly
```

**How to Apply:**
```bash
# 1. Verify the fix is in place
docker compose exec mem0 grep -A 2 '@app.post("/memories"' /app/main.py
# Should show: async def add_memory

# 2. If not fixed, rebuild mem0 server
docker compose build --no-cache mem0
docker compose restart mem0

# 3. Verify fix works
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "test memory"}],
    "user_id": "test_user"
  }'

# Should return 200 OK, not 500 error
```

**Note:** This fix is already included in the latest version. If you encounter this error, ensure you're running the latest code and have rebuilt the containers.

---

## Getting Help

1. Check service health: `./scripts/health.sh`
2. View logs: `./scripts/logs.sh`
3. Run tests: `./scripts/test.sh`
4. See ARCHITECTURE.md for system design
5. Check .env configuration
