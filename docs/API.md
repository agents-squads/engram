# Mem0 REST API Reference

Complete reference for the Mem0 REST API running on port 8000.

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication required for local development. For production, implement authentication at the reverse proxy level.

## Endpoints

### Health Check

```http
GET /health
```

Check if the server is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-08T12:34:56.789Z"
}
```

---

### Create Memory

```http
POST /memories
```

Add a new memory to the system:
- LLM extracts key facts from the conversation
- Embeddings generated for semantic search
- Stored immediately in PostgreSQL (pgvector)

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "I prefer using async/await over callbacks in JavaScript"
    }
  ],
  "user_id": "my_project",
  "metadata": {
    "category": "coding",
    "tags": ["javascript", "async"]
  }
}
```

**Parameters:**
- `messages` (required): Array of message objects
  - `role`: "user" or "assistant"
  - `content`: The text to store
- `user_id` (required): Unique identifier for memory isolation
- `metadata` (optional): Additional structured data
- `agent_id` (optional): Agent identifier
- `run_id` (optional): Session identifier

**Response (201 Created):**
```json
{
  "results": [
    {
      "id": "mem_abc123xyz",
      "memory": "User prefers async/await over callbacks in JavaScript",
      "event": "ADD",
      "created_at": "2025-10-08T12:34:56.789Z"
    }
  ],
  "relations": []
}
```

**Error Response (500):**
```json
{
  "detail": "Failed to add memory: [error message]"
}
```

---

### Get All Memories

```http
GET /memories?user_id={user_id}
```

Retrieve all memories for a specific user.

**Query Parameters:**
- `user_id` (required): User identifier
- `agent_id` (optional): Filter by agent
- `run_id` (optional): Filter by session

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "mem_abc123xyz",
      "memory": "User prefers async/await over callbacks in JavaScript",
      "hash": "e3b0c44298fc1c149afb",
      "metadata": {
        "category": "coding",
        "tags": ["javascript", "async"]
      },
      "created_at": "2025-10-08T12:34:56.789Z",
      "updated_at": "2025-10-08T12:34:56.789Z",
      "user_id": "my_project"
    },
    {
      "id": "mem_def456uvw",
      "memory": "User uses Python 3.12 with type hints",
      "hash": "98f13708210194c47544",
      "metadata": null,
      "created_at": "2025-10-08T12:35:00.123Z",
      "updated_at": "2025-10-08T12:35:00.123Z",
      "user_id": "my_project"
    }
  ]
}
```

---

### Get Specific Memory

```http
GET /memories/{memory_id}?user_id={user_id}
```

Retrieve a single memory by ID.

**Path Parameters:**
- `memory_id` (required): The memory ID

**Query Parameters:**
- `user_id` (required): User identifier

**Response (200 OK):**
```json
{
  "id": "mem_abc123xyz",
  "memory": "User prefers async/await over callbacks in JavaScript",
  "hash": "e3b0c44298fc1c149afb",
  "metadata": {
    "category": "coding"
  },
  "created_at": "2025-10-08T12:34:56.789Z",
  "updated_at": "2025-10-08T12:34:56.789Z",
  "user_id": "my_project"
}
```

**Error Response (404):**
```json
{
  "detail": "Memory not found"
}
```

---

### Update Memory

```http
PUT /memories/{memory_id}
```

Update an existing memory.

**Path Parameters:**
- `memory_id` (required): The memory ID

**Request Body:**
```json
{
  "text": "Updated memory content",
  "user_id": "my_project",
  "metadata": {
    "category": "updated"
  }
}
```

**Response (200 OK):**
```json
{
  "id": "mem_abc123xyz",
  "memory": "Updated memory content",
  "event": "UPDATE",
  "updated_at": "2025-10-08T12:40:00.000Z"
}
```

---

### Delete Memory

```http
DELETE /memories/{memory_id}?user_id={user_id}
```

Delete a specific memory.

**Path Parameters:**
- `memory_id` (required): The memory ID

**Query Parameters:**
- `user_id` (required): User identifier

**Response (200 OK):**
```json
{
  "message": "Memory deleted successfully",
  "deleted_id": "mem_abc123xyz"
}
```

---

### Search Memories

```http
POST /search
```

Perform semantic search across memories.

**Request Body:**
```json
{
  "query": "async programming patterns",
  "user_id": "my_project",
  "limit": 5,
  "filters": {
    "category": "coding"
  }
}
```

**Parameters:**
- `query` (required): Search text
- `user_id` (required): User identifier
- `limit` (optional, default: 10): Max results to return
- `filters` (optional): Metadata filters
- `agent_id` (optional): Filter by agent
- `run_id` (optional): Filter by session

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "mem_abc123xyz",
      "memory": "User prefers async/await over callbacks in JavaScript",
      "score": 0.892,
      "metadata": {
        "category": "coding"
      },
      "created_at": "2025-10-08T12:34:56.789Z"
    },
    {
      "id": "mem_ghi789rst",
      "memory": "User uses Promise.all for concurrent async operations",
      "score": 0.765,
      "metadata": {
        "category": "coding"
      },
      "created_at": "2025-10-08T12:36:00.456Z"
    }
  ]
}
```

**Score Interpretation:**
- `1.0` = Perfect match
- `0.8-0.99` = Very relevant
- `0.6-0.79` = Moderately relevant
- `< 0.6` = Low relevance

---

### Get Memory History

```http
GET /memories/{memory_id}/history?user_id={user_id}
```

Retrieve the change history for a memory.

**Path Parameters:**
- `memory_id` (required): The memory ID

**Query Parameters:**
- `user_id` (required): User identifier

**Response (200 OK):**
```json
{
  "history": [
    {
      "id": "mem_abc123xyz",
      "memory": "User prefers async/await over callbacks in JavaScript",
      "event": "ADD",
      "timestamp": "2025-10-08T12:34:56.789Z",
      "metadata": {
        "category": "coding"
      }
    },
    {
      "id": "mem_abc123xyz",
      "memory": "User strongly prefers async/await over callbacks in JavaScript",
      "event": "UPDATE",
      "timestamp": "2025-10-08T12:40:00.000Z",
      "metadata": {
        "category": "coding",
        "priority": "high"
      }
    }
  ]
}
```

---

## Error Responses

All endpoints may return these error codes:

### 400 Bad Request
```json
{
  "detail": "Invalid request: missing required field 'user_id'"
}
```

### 404 Not Found
```json
{
  "detail": "Memory not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error: [error message]"
}
```

---

## Rate Limiting

No rate limiting for local deployment. Implement at reverse proxy level for production.

---

## Pagination

Currently not implemented. All endpoints return complete result sets. For large datasets, use `limit` parameter in search.

---

## OpenAPI Documentation

Interactive API documentation available at:

```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
http://localhost:8000/openapi.json # OpenAPI spec
```

---

## cURL Examples

### Create Memory
```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I use TypeScript for all projects"}],
    "user_id": "my_project"
  }'
```

### Search Memories
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "TypeScript",
    "user_id": "my_project",
    "limit": 5
  }'
```

### Get All Memories
```bash
curl http://localhost:8000/memories?user_id=my_project
```

### Delete Memory
```bash
curl -X DELETE http://localhost:8000/memories/mem_abc123xyz?user_id=my_project
```
