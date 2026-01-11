"""
Mem0 REST API Server

A production-ready FastAPI server providing memory storage and retrieval
with support for multiple LLM providers (Ollama, OpenAI, Anthropic).
"""

import logging
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from mem0 import Memory
import config
from truncate_embedder import TruncateEmbedder
from telemetry import init_telemetry, trace_operation, SpanNames, add_memory_attributes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Mem0 with configuration
logger.info(f"Initializing Mem0 with provider: {config.LLM_PROVIDER}")

target_dims = config.OLLAMA_EMBEDDING_DIMS if config.LLM_PROVIDER == 'ollama' else config.OPENAI_EMBEDDING_DIMS
logger.info(f"Embedding dimensions: {target_dims}")
logger.info(f"HNSW enabled: {config.get_vector_store_config()['config']['hnsw']}")

MEMORY_INSTANCE = Memory.from_config(config.get_mem0_config())

# Wrap embedder with truncation for MRL models (e.g., qwen3-embedding:4b)
if config.LLM_PROVIDER == 'ollama' and 'qwen3-embedding' in config.OLLAMA_EMBEDDING_MODEL:
    logger.info(f"Wrapping embedder with TruncateEmbedder for MRL support (target: {target_dims} dims)")
    MEMORY_INSTANCE.embedding_model = TruncateEmbedder(
        MEMORY_INSTANCE.embedding_model,
        target_dims=target_dims
    )

# Initialize FastAPI app
app = FastAPI(
    title="Mem0 REST API",
    description="A production-ready REST API for managing and searching memories for AI Agents and Apps.",
    version="1.0.0",
)

# Initialize OpenTelemetry tracing
tracer = init_telemetry(app)
logger.info("OpenTelemetry tracing initialized")

# Request/Response Models
class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: str = Field(..., description="Message content.")


class MemoryCreate(BaseModel):
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


# API Endpoints
@app.post("/configure", summary="Configure Mem0")
def set_config(config_data: Dict[str, Any]):
    """Set memory configuration dynamically."""
    global MEMORY_INSTANCE
    try:
        MEMORY_INSTANCE = Memory.from_config(config_data)
        return {"message": "Configuration set successfully"}
    except Exception as e:
        logger.exception("Error setting configuration:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories", summary="Create memories")
async def add_memory(memory_create: MemoryCreate):
    """
    Store new memories in PostgreSQL and automatically sync to Neo4j.

    This unified endpoint handles both vector storage (PostgreSQL) and
    graph intelligence (Neo4j) transparently. No manual sync required.
    """
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(
            status_code=400,
            detail="At least one identifier (user_id, agent_id, run_id) is required."
        )

    params = {
        k: v for k, v in memory_create.model_dump().items()
        if v is not None and k != "messages"
    }

    # Trace the entire memory add operation
    with trace_operation(SpanNames.MEMORY_ADD, {
        "user_id": memory_create.user_id,
        "agent_id": memory_create.agent_id,
        "message_count": len(memory_create.messages),
    }) as span:
        try:
            # 1. Add to PostgreSQL/pgvector (includes LLM extraction + embedding)
            start_time = time.perf_counter()
            with trace_operation("mem0.add", {"provider": config.LLM_PROVIDER}) as mem0_span:
                response = MEMORY_INSTANCE.add(
                    messages=[m.model_dump() for m in memory_create.messages],
                    **params
                )
                results_count = len(response.get("results", []))
                mem0_span.set_attribute("results_count", results_count)

            mem0_duration = (time.perf_counter() - start_time) * 1000
            span.set_attribute("mem0_add_duration_ms", mem0_duration)
            span.set_attribute("results_count", results_count)
            logger.info(f"mem0.add completed in {mem0_duration:.0f}ms, {results_count} results")

            return JSONResponse(content=response)
        except Exception as e:
            logger.exception("Error adding memory:")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", summary="Get memories")
def get_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Retrieve stored memories."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(
            status_code=400,
            detail="At least one identifier is required."
        )

    try:
        params = {
            k: v for k, v in {
                "user_id": user_id,
                "run_id": run_id,
                "agent_id": agent_id
            }.items() if v is not None
        }
        return MEMORY_INSTANCE.get_all(**params)
    except Exception as e:
        logger.exception("Error getting memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", summary="Get a memory")
def get_memory(memory_id: str, user_id: Optional[str] = None):
    """Retrieve a specific memory by ID with ownership validation."""
    try:
        memory = MEMORY_INSTANCE.get(memory_id)

        # Validate ownership if user_id is provided
        if user_id and memory.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Memory {memory_id} does not belong to user {user_id}"
            )

        return memory
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", summary="Unified intelligent search")
def search_memories(search_req: SearchRequest):
    """
    Universal intelligent search - automatically enhanced with graph intelligence.

    This unified endpoint:
    1. Performs vector similarity search (pgvector)
    2. Automatically enriches with graph context when available (Neo4j)
    3. Re-ranks results using enhanced scoring

    No need to choose between search modes - the system automatically
    provides the best results by combining vector + graph intelligence.

    Each result includes:
    - Semantic similarity score
    - Graph context (connections, relationships, trust)
    - Enhanced score (re-ranked for relevance)
    """
    with trace_operation(SpanNames.MEMORY_SEARCH, {
        "user_id": search_req.user_id,
        "query_length": len(search_req.query),
    }) as span:
        try:
            params = {
                k: v for k, v in search_req.model_dump().items()
                if v is not None and k != "query"
            }

            # Perform vector search (includes embedding generation)
            with trace_operation(SpanNames.VECTOR_SEARCH, {"provider": config.LLM_PROVIDER}) as vector_span:
                start_time = time.perf_counter()
                vector_results = MEMORY_INSTANCE.search(query=search_req.query, **params)
                vector_duration = (time.perf_counter() - start_time) * 1000
                results_count = len(vector_results.get("results", []))
                vector_span.set_attribute("results_count", results_count)
                vector_span.set_attribute("duration_ms", vector_duration)

            span.set_attribute("vector_search_duration_ms", vector_duration)
            span.set_attribute("vector_results_count", results_count)
            logger.info(f"Vector search completed in {vector_duration:.0f}ms, {results_count} results")

            return vector_results

        except Exception as e:
            logger.exception("Error searching memories:")
            raise HTTPException(status_code=500, detail=str(e))


@app.put("/memories/{memory_id}", summary="Update a memory")
def update_memory(memory_id: str, updated_memory: Dict[str, Any], user_id: Optional[str] = None):
    """Update an existing memory with new content and ownership validation."""
    try:
        # Validate ownership if user_id is provided
        if user_id:
            memory = MEMORY_INSTANCE.get(memory_id)
            if memory.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Memory {memory_id} does not belong to user {user_id}"
                )

        return MEMORY_INSTANCE.update(memory_id=memory_id, data=updated_memory)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str, user_id: Optional[str] = None):
    """Retrieve the change history of a memory with ownership validation."""
    try:
        # Validate ownership if user_id is provided
        if user_id:
            memory = MEMORY_INSTANCE.get(memory_id)
            if memory.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Memory {memory_id} does not belong to user {user_id}"
                )

        return MEMORY_INSTANCE.history(memory_id=memory_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting memory history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories/{memory_id}", summary="Delete a memory")
def delete_memory(memory_id: str, user_id: Optional[str] = None):
    """Delete a specific memory by ID with ownership validation."""
    try:
        # Validate ownership if user_id is provided
        if user_id:
            memory = MEMORY_INSTANCE.get(memory_id)
            if memory.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Memory {memory_id} does not belong to user {user_id}"
                )

        MEMORY_INSTANCE.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories", summary="Delete all memories")
def delete_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Delete all memories for a given identifier."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(
            status_code=400,
            detail="At least one identifier is required."
        )

    try:
        params = {
            k: v for k, v in {
                "user_id": user_id,
                "run_id": run_id,
                "agent_id": agent_id
            }.items() if v is not None
        }
        MEMORY_INSTANCE.delete_all(**params)
        return {"message": "All relevant memories deleted"}
    except Exception as e:
        logger.exception("Error deleting all memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset", summary="Reset all memories")
def reset_memory():
    """Completely reset all stored memories."""
    try:
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logger.exception("Error resetting memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", summary="Health check")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "mem0-server",
        "provider": config.LLM_PROVIDER,
    }


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
