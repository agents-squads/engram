# MCP Tools Reference

Complete guide to the 5 Model Context Protocol tools available in Claude Code.

## Overview

The MCP server exposes 5 tools for memory management:

1. **add_coding_preference** - Store new memories
2. **search_coding_preferences** - Semantic search
3. **get_all_coding_preferences** - Retrieve all memories
4. **delete_memory** - Remove specific memory
5. **get_memory_history** - View change history

All tools automatically use the current project directory as the `user_id` when `PROJECT_ID_MODE=auto`.

---

## 1. add_coding_preference

Store a new coding preference or memory with automatic smart chunking for large text.

### Usage in Claude Code

```
"Store this in memory: I prefer using Tailwind CSS for styling"
```

```
"Remember that I use PostgreSQL 16 with pgvector extension"
```

```
"Save this code snippet: def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
```

```
"Store this entire code file in memory: [paste large file]"
```

### Tool Parameters

```python
{
  "text": str  # The content to store (any size)
}
```

### What Happens

**Small Text (≤1000 characters):**
1. Tool receives the text
2. Adds current `user_id` (project directory hash)
3. Sends directly to Mem0 API at `/memories`
4. LLM processes and stores the memory
5. Returns confirmation with memory ID

**Large Text (>1000 characters):**
1. Tool receives the text
2. **Automatically chunks** text at semantic boundaries (paragraphs/sentences)
3. Adds 150-character overlap between chunks for context preservation
4. Sends each chunk sequentially with shared `run_id`
5. Each chunk includes metadata (index, total, size, overlap)
6. Returns confirmation with all chunk IDs

### Smart Chunking

The tool automatically handles large text inputs (code files, documentation, long explanations) by splitting them intelligently:

**Chunking Strategy:**
- **Threshold:** Text > 1000 characters triggers chunking
- **Boundaries:** Splits at paragraphs (double newlines) first
- **Fallback:** If paragraph too large, splits at sentences
- **Overlap:** 150 characters overlap between chunks preserves context
- **Session:** All chunks share same `run_id` for relationship tracking

**Example: 5000-character code file**
```
Input: 5000 chars
     ↓
Chunk 1: [Part 1/5] chars 0-1000
Chunk 2: [Part 2/5] chars 850-1850 (150 overlap)
Chunk 3: [Part 3/5] chars 1700-2700 (150 overlap)
Chunk 4: [Part 4/5] chars 2550-3550 (150 overlap)
Chunk 5: [Part 5/5] chars 3400-5000 (150 overlap)
     ↓
5 memories stored, linked by run_id
```

### Example Responses

**Small text:**
```
✅ Successfully added preference for project '/home/user/myproject'
   Memory ID: mem_abc123xyz
   Content: "User prefers Tailwind CSS for styling"
```

**Large text (chunked):**
```
✅ Successfully added large preference (5 chunks) for project '/home/user/myproject':
{
  "status": "success",
  "total_chunks": 5,
  "chunks_stored": 5,
  "project_id": "prj_a1b2c3d4",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_ids": [
    "mem_abc123xyz",
    "mem_def456uvw",
    "mem_ghi789rst",
    "mem_jkl012mno",
    "mem_pqr345stu"
  ]
}
```

### Performance

**Small text:**
- Time: 2-5 seconds
- Storage: 1 memory entry
- Overhead: None

**Large text (5000 chars):**
- Time: 15-45 seconds (5 chunks × 3-9s each)
- Storage: 5 memory entries (linked by run_id)
- Overhead: Automatic, transparent to user

**Timeout protection:** MCP client timeout extended to 180 seconds to accommodate large text processing.

### Error Handling

```
❌ Error adding preference: Failed to connect to Mem0 server
```

```
❌ Error adding preference: HTTP 408 - Timeout
   (Try using smaller text or check embedding model performance)
```

### Best Practices

- **Be specific:** "I use React 18 with TypeScript" vs "I use React"
- **Include context:** "For API calls, I prefer axios over fetch"
- **Store implementation details:** Include code snippets, patterns, conventions
- **Tag categories:** "Testing: I use pytest with fixtures"
- **Store large files:** Entire code files are automatically chunked (no size limit)
- **Maintain context:** The 150-char overlap ensures context isn't lost between chunks

---

## 2. search_coding_preferences

Search stored memories using semantic similarity.

### Usage in Claude Code

```
"Search my memories for React hooks"
```

```
"Find what I've stored about database migrations"
```

```
"Show me memories related to authentication"
```

### Tool Parameters

```python
{
  "query": str,    # Search query
  "limit": int     # Max results (default: 10)
}
```

### What Happens

1. Tool receives the query
2. Adds current `user_id` (project directory)
3. Sends to Mem0 API at `/search`
4. Performs vector similarity search
5. Returns ranked results with scores

### Example Response

```
Found 3 relevant memories:

1. [Score: 0.89] "User prefers React hooks over class components"
   ID: mem_abc123xyz
   Created: 2025-10-08 12:34:56

2. [Score: 0.76] "User uses custom hooks for API calls"
   ID: mem_def456uvw
   Created: 2025-10-08 12:40:00

3. [Score: 0.65] "User follows React best practices from official docs"
   ID: mem_ghi789rst
   Created: 2025-10-08 12:45:00
```

### Score Interpretation

- **0.9 - 1.0**: Highly relevant, exact or near-exact match
- **0.7 - 0.89**: Very relevant, strong semantic similarity
- **0.5 - 0.69**: Moderately relevant, related concepts
- **< 0.5**: Low relevance, tangentially related

### Error Handling

```
❌ Error searching preferences: Query cannot be empty
```

### Search Tips

- Use natural language: "Python testing" vs "pytest unittest"
- Try different phrasings if results are poor
- Use broader queries to discover related memories
- Combine keywords: "React testing hooks"

---

## 3. get_all_coding_preferences

Retrieve all stored memories for the current project.

### Usage in Claude Code

```
"Show me all my stored preferences"
```

```
"List all memories for this project"
```

```
"What have I saved so far?"
```

### Tool Parameters

None required - automatically uses current project.

### What Happens

1. Tool determines current `user_id`
2. Sends to Mem0 API at `/memories?user_id={user_id}`
3. Returns all memories with metadata
4. Sorted by creation date (newest first)

### Example Response

```
Found 5 memories for project '/home/user/myproject':

1. [mem_abc123xyz] "User prefers async/await over callbacks"
   Created: 2025-10-08 12:50:00
   Updated: 2025-10-08 12:50:00

2. [mem_def456uvw] "User uses TypeScript strict mode"
   Created: 2025-10-08 12:45:00
   Updated: 2025-10-08 12:47:00

3. [mem_ghi789rst] "User follows Airbnb style guide"
   Created: 2025-10-08 12:40:00
   Updated: 2025-10-08 12:40:00

... (2 more)
```

### Use Cases

- Audit stored preferences
- Review all memories before cleanup
- Export/backup memories
- Discover forgotten memories

### Error Handling

```
❌ Error retrieving preferences: Database connection failed
```

---

## 4. delete_memory

Delete a specific memory by ID.

### Usage in Claude Code

```
"Delete memory mem_abc123xyz"
```

```
"Remove the memory about React hooks"
```

```
"Delete all memories about Python" (requires multiple delete calls)
```

### Tool Parameters

```python
{
  "memory_id": str  # The memory ID to delete
}
```

### What Happens

1. Tool receives the memory ID
2. Adds current `user_id` for verification
3. Sends DELETE to `/memories/{memory_id}`
4. Permanently removes the memory
5. Returns confirmation

### Example Response

```
✅ Successfully deleted memory mem_abc123xyz
   Previous content: "User prefers React class components"
```

### Error Handling

```
❌ Error deleting memory: Memory not found or does not belong to this project
```

### Safety Notes

- **Irreversible**: Deleted memories cannot be recovered
- **Project-scoped**: Can only delete memories from current project
- **History preserved**: Some systems may keep deletion history

### Workflow

1. Search for memory: `search_coding_preferences("old pattern")`
2. Identify ID from results: `mem_abc123xyz`
3. Delete: `delete_memory("mem_abc123xyz")`
4. Verify: `search_coding_preferences("old pattern")` (should not appear)

---

## 5. get_memory_history

View the change history for a specific memory.

### Usage in Claude Code

```
"Show history for memory mem_abc123xyz"
```

```
"How has this memory changed over time?"
```

```
"Show me the evolution of memory mem_def456uvw"
```

### Tool Parameters

```python
{
  "memory_id": str  # The memory ID
}
```

### What Happens

1. Tool receives the memory ID
2. Adds current `user_id` for verification
3. Sends to `/memories/{memory_id}/history`
4. Returns chronological history
5. Shows all ADD/UPDATE/DELETE events

### Example Response

```
History for memory mem_abc123xyz:

1. [ADD] 2025-10-08 12:34:56
   "User prefers React class components"

2. [UPDATE] 2025-10-08 12:40:00
   "User prefers React hooks over class components"
   (Changed: terminology updated, hooks emphasized)

3. [UPDATE] 2025-10-08 12:45:00
   "User strongly prefers React hooks and avoids class components"
   (Changed: added emphasis, clarified avoidance)
```

### Use Cases

- Track how preferences evolved
- Understand memory refinement
- Debug unexpected memory content
- Audit changes over time

### Error Handling

```
❌ Error retrieving history: Memory not found or no history available
```

---

## Project Isolation

### Auto Mode (Default)

```bash
PROJECT_ID_MODE=auto
```

Each directory gets a unique `user_id` based on its absolute path hash:

```
/home/user/project-a  →  user_id: "prj_a1b2c3d4"
/home/user/project-b  →  user_id: "prj_e5f6g7h8"
```

Memories are **completely isolated** between projects.

### Manual Mode

```bash
PROJECT_ID_MODE=manual
DEFAULT_USER_ID=my_custom_project
```

All memories use the specified `user_id`. Useful for:
- Sharing memories across projects
- Custom isolation strategies
- Testing

### Global Mode

```bash
PROJECT_ID_MODE=global
DEFAULT_USER_ID=global_memory
```

**All projects share the same memory pool**. Useful for:
- Personal coding preferences (across all projects)
- Team-wide conventions
- Shared knowledge base

---

## Common Workflows

### Workflow 1: Store and Retrieve

```
User: "Store in memory: I use pytest with fixtures for testing"
Claude: ✅ Stored successfully

User: "What's my preferred testing approach?"
Claude: [Searches and finds] "You use pytest with fixtures for testing"
```

### Workflow 2: Search and Update

```
User: "Search memories for database"
Claude: Found 2 memories about PostgreSQL

User: "Store in memory: I've switched from PostgreSQL to MongoDB"
Claude: ✅ Stored successfully
```

### Workflow 3: Audit and Clean

```
User: "Show all my memories"
Claude: [Lists 10 memories]

User: "Delete memory mem_abc123xyz (outdated)"
Claude: ✅ Deleted successfully

User: "Show all my memories"
Claude: [Lists 9 memories]
```

### Workflow 4: History Investigation

```
User: "Why does memory mem_abc123xyz mention React hooks?"
Claude: [Gets history] Shows 3 updates, originally was about class components

User: "That makes sense, I changed my approach last month"
```

---

## Tips for Effective Memory Usage

### 1. Be Specific

❌ "I use React"
✅ "I use React 18 with TypeScript, hooks, and functional components"

### 2. Include Context

❌ "I use axios"
✅ "For API calls, I use axios with custom interceptors for auth"

### 3. Store Patterns, Not Just Facts

❌ "I know Python"
✅ "In Python, I use dataclasses for DTOs, pydantic for validation, and pytest for testing"

### 4. Update, Don't Duplicate

If your preference changes, search for the old memory and update it rather than creating a new one.

### 5. Use Categories

Store memories with implicit categories:
- "Testing: I use pytest with fixtures"
- "Styling: I prefer Tailwind CSS"
- "Database: I use PostgreSQL with SQLAlchemy"

### 6. Leverage Semantic Search

Search works on meaning, not just keywords:
- Query: "API testing" → Finds: "I use pytest-httpx for testing HTTP endpoints"
- Query: "async code" → Finds: "I prefer asyncio over threading"

---

## Troubleshooting

### Tool Not Available

**Problem:** MCP tools don't appear in Claude Code

**Solutions:**
1. Verify MCP config: `~/.config/claude-code/config.json`
2. Restart Claude Code
3. Check MCP server: `curl http://localhost:8080/sse`
4. View logs: `./scripts/logs.sh mcp`

### Empty Search Results

**Problem:** Search returns no results despite stored memories

**Solutions:**
1. Verify you're in the correct project directory (auto mode)
2. Check if memories exist: `get_all_coding_preferences()`
3. Try broader search terms
4. Check Ollama/LLM connectivity: `./scripts/logs.sh mem0`

### Slow Tool Responses

**Problem:** Tools take 30-60 seconds to respond

**Causes:**
- First request loads Ollama model
- Large embedding dimensions (4096)

**Solutions:**
1. Use smaller model: `OLLAMA_EMBEDDING_MODEL=nomic-embed-text`
2. Switch to OpenAI: `LLM_PROVIDER=openai`
3. Pre-warm models: `curl http://ollama:11434/api/generate`

### Memory Not Stored

**Problem:** Tool returns success but memory not found

**Solutions:**
1. Check mem0 logs: `./scripts/logs.sh mem0`
2. Verify database health: `./scripts/health.sh`
3. Test API directly: `curl http://localhost:8000/health`
4. Check Ollama connectivity

---

## API Integration

For advanced usage, you can call the Mem0 REST API directly. See [API.md](API.md) for details.

Example: Store memory via curl
```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I use Docker Compose"}],
    "user_id": "prj_custom"
  }'
```
