"""
Mem0 REST API Server

A production-ready FastAPI server providing memory storage and retrieval
with support for multiple LLM providers (Ollama, OpenAI, Anthropic).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from mem0 import Memory
import config
from graph_intelligence import MemoryIntelligence
from truncate_embedder import TruncateEmbedder

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

# Initialize Memory Intelligence System
GRAPH_INTELLIGENCE = MemoryIntelligence(
    uri=config.NEO4J_URI,
    username=config.NEO4J_USERNAME,
    password=config.NEO4J_PASSWORD
)

# Initialize FastAPI app
app = FastAPI(
    title="Mem0 REST API",
    description="A production-ready REST API for managing and searching memories for AI Agents and Apps.",
    version="1.0.0",
)

# Background Neo4j sync with retry logic
async def _sync_to_neo4j_with_retry(
    memory_id: str,
    memory_text: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    max_retries: int = None
):
    """
    Sync memory to Neo4j with exponential backoff retry.
    Runs in background, non-blocking.

    Retry Schedule (default 7 attempts, configurable via NEO4J_SYNC_MAX_RETRIES):
    - Attempt 1: Immediate
    - Attempt 2: Wait 1s
    - Attempt 3: Wait 2s
    - Attempt 4: Wait 4s
    - Attempt 5: Wait 8s
    - Attempt 6: Wait 16s
    - Attempt 7: Wait 32s
    Total max wait time: ~63 seconds
    """
    # Use config value if not specified
    if max_retries is None:
        max_retries = config.NEO4J_SYNC_MAX_RETRIES

    for attempt in range(max_retries):
        try:
            # Run sync in thread pool (Neo4j driver is synchronous)
            await asyncio.to_thread(
                GRAPH_INTELLIGENCE.sync_memory_to_neo4j,
                memory_id=memory_id,
                memory_text=memory_text,
                user_id=user_id,
                metadata=metadata
            )
            logger.info(f"✅ Auto-synced memory {memory_id} to Neo4j (attempt {attempt + 1}/{max_retries})")
            return  # Success
        except Exception as sync_error:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s
            if attempt < max_retries - 1:
                logger.warning(
                    f"⚠️  Neo4j sync failed for {memory_id} (attempt {attempt + 1}/{max_retries}): {sync_error}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"❌ Neo4j sync failed for {memory_id} after {max_retries} attempts. "
                    f"Total wait time: ~{sum(2**i for i in range(max_retries))}s. "
                    f"Final error: {sync_error}"
                )


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


class MemoryLinkRequest(BaseModel):
    memory_id_1: str = Field(..., description="First memory ID")
    memory_id_2: str = Field(..., description="Second memory ID")
    relationship_type: str = Field("RELATES_TO", description="Type of relationship")
    metadata: Optional[Dict[str, Any]] = None


class DecisionRequest(BaseModel):
    text: str = Field(..., description="Decision text")
    user_id: str = Field(..., description="User ID")
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ComponentRequest(BaseModel):
    name: str = Field(..., description="Component name")
    component_type: str = Field("Component", description="Component type")
    metadata: Optional[Dict[str, Any]] = None


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

    try:
        # 1. Add to PostgreSQL/pgvector for vector search
        response = MEMORY_INSTANCE.add(
            messages=[m.model_dump() for m in memory_create.messages],
            **params
        )

        # 2. Auto-sync to Neo4j for graph intelligence (async, non-blocking)
        if response.get("results"):
            for result in response["results"]:
                memory_id = result.get("id")
                memory_text = result.get("memory", "")
                user_id = memory_create.user_id or memory_create.agent_id or memory_create.run_id

                # Create background task for Neo4j sync (non-blocking)
                asyncio.create_task(
                    _sync_to_neo4j_with_retry(
                        memory_id=memory_id,
                        memory_text=memory_text,
                        user_id=user_id,
                        metadata=memory_create.metadata
                    )
                )

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
    try:
        params = {
            k: v for k, v in search_req.model_dump().items()
            if v is not None and k != "query"
        }

        # Perform vector search
        vector_results = MEMORY_INSTANCE.search(query=search_req.query, **params)

        # Auto-enhance with graph context if results exist
        if vector_results.get("results"):
            try:
                enriched_results = GRAPH_INTELLIGENCE.enrich_search_results_with_graph(
                    search_results=vector_results["results"],
                    include_graph_context=True
                )

                # Update response with enriched results
                response = vector_results.copy()
                response["results"] = enriched_results
                response["search_type"] = "unified_intelligent"
                return response
            except Exception as graph_error:
                # Graceful fallback if graph enrichment fails
                logger.warning(f"Graph enrichment failed, returning vector results: {graph_error}")
                vector_results["search_type"] = "vector_only"
                return vector_results
        else:
            vector_results["search_type"] = "vector_only"
            return vector_results

    except Exception as e:
        logger.exception("Error searching memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/enhanced", summary="Enhanced search with graph context")
def enhanced_search_memories(search_req: SearchRequest, include_graph_context: bool = True):
    """
    Search for memories using vector similarity and enrich results with Neo4j graph context.

    This endpoint combines:
    - Vector search (pgvector) for semantic similarity
    - Graph intelligence (Neo4j) for relationship context

    Each result includes graph_context with:
    - Number of connections to other memories
    - Related memory IDs (up to 3)
    - Dependencies (DEPENDS_ON relationships)
    - Superseded status (is this memory outdated?)
    - Linked components (system architecture)
    - Trust score and validations

    Results are re-ranked using enhanced_score that considers:
    - Original vector similarity score
    - Connection boost (highly connected memories)
    - Outdated penalty (superseded memories)
    - Trust boost (validated/cited memories)
    """
    try:
        # Perform standard vector search
        params = {
            k: v for k, v in search_req.model_dump().items()
            if v is not None and k != "query"
        }
        vector_results = MEMORY_INSTANCE.search(query=search_req.query, **params)

        # If no results or graph context not requested, return as-is
        if not include_graph_context or not vector_results.get("results"):
            return vector_results

        # Enrich results with graph context
        enriched_results = GRAPH_INTELLIGENCE.enrich_search_results_with_graph(
            search_results=vector_results["results"],
            include_graph_context=include_graph_context
        )

        # Update response with enriched results
        response = vector_results.copy()
        response["results"] = enriched_results
        response["search_type"] = "enhanced_vector_graph"

        return response
    except Exception as e:
        logger.exception("Error in enhanced search:")
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


# ============================================
# MEMORY INTELLIGENCE - GRAPH ANALYSIS ENDPOINTS
# ============================================

@app.post("/graph/sync", summary="Sync memory to Neo4j", tags=["Memory Intelligence"])
def sync_memory_to_neo4j(memory_id: str, user_id: str):
    """
    Sync a memory from PostgreSQL to Neo4j graph database.
    This must be called before using graph operations on a memory.
    """
    try:
        # Get the memory from PostgreSQL
        params = {"user_id": user_id}
        all_memories = MEMORY_INSTANCE.get_all(**params)

        # Find the specific memory
        memory = next((m for m in all_memories.get("results", []) if m["id"] == memory_id), None)
        if not memory:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")

        # Sync to Neo4j
        return GRAPH_INTELLIGENCE.sync_memory_to_neo4j(
            memory_id=memory_id,
            memory_text=memory.get("memory", ""),
            user_id=user_id,
            metadata=memory.get("metadata")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error syncing memory to Neo4j:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/link", summary="Link two memories", tags=["Memory Intelligence"])
def link_memories(link_req: MemoryLinkRequest):
    """Create a relationship between two memories."""
    try:
        return GRAPH_INTELLIGENCE.link_memories(
            memory_id_1=link_req.memory_id_1,
            memory_id_2=link_req.memory_id_2,
            relationship_type=link_req.relationship_type,
            metadata=link_req.metadata
        )
    except Exception as e:
        logger.exception("Error linking memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/related/{memory_id}", summary="Get related memories", tags=["Memory Intelligence"])
def get_related(
    memory_id: str,
    depth: int = 2,
    relationship_types: Optional[str] = None
):
    """Get all memories related to a specific memory."""
    try:
        rel_types = relationship_types.split(",") if relationship_types else None
        return GRAPH_INTELLIGENCE.get_related_memories(
            memory_id=memory_id,
            depth=depth,
            relationship_types=rel_types
        )
    except Exception as e:
        logger.exception("Error getting related memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/path", summary="Find path between memories", tags=["Memory Intelligence"])
def find_memory_path(from_memory_id: str, to_memory_id: str):
    """Find the shortest path between two memories."""
    try:
        result = GRAPH_INTELLIGENCE.find_path(from_memory_id, to_memory_id)
        if result:
            return result
        raise HTTPException(status_code=404, detail="No path found between memories")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error finding path:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/evolution/{topic}", summary="Get knowledge evolution", tags=["Memory Intelligence"])
def get_evolution(topic: str, user_id: Optional[str] = None):
    """Track how knowledge about a topic has evolved over time."""
    try:
        return GRAPH_INTELLIGENCE.get_memory_evolution(topic=topic)
    except Exception as e:
        logger.exception("Error getting memory evolution:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/superseded", summary="Find obsolete memories", tags=["Memory Intelligence"])
def get_superseded(user_id: str):
    """Find all memories that have been superseded (outdated)."""
    try:
        return GRAPH_INTELLIGENCE.find_superseded_memories(user_id=user_id)
    except Exception as e:
        logger.exception("Error finding superseded memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/thread/{memory_id}", summary="Get conversation thread", tags=["Memory Intelligence"])
def get_thread(memory_id: str):
    """Get the full conversation thread for a memory."""
    try:
        return GRAPH_INTELLIGENCE.get_conversation_thread(memory_id=memory_id)
    except Exception as e:
        logger.exception("Error getting conversation thread:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/component", summary="Create component", tags=["Memory Intelligence"])
def create_component(comp_req: ComponentRequest):
    """Create a technical component node."""
    try:
        return GRAPH_INTELLIGENCE.create_component(
            name=comp_req.name,
            component_type=comp_req.component_type,
            metadata=comp_req.metadata
        )
    except Exception as e:
        logger.exception("Error creating component:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/component/dependency", summary="Link component dependency", tags=["Memory Intelligence"])
def link_component_dependency(
    component_from: str,
    component_to: str,
    dependency_type: str = "DEPENDS_ON"
):
    """Create a dependency between components."""
    try:
        return GRAPH_INTELLIGENCE.link_component_dependency(
            component_from=component_from,
            component_to=component_to,
            dependency_type=dependency_type
        )
    except Exception as e:
        logger.exception("Error linking component dependency:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/component/link-memory", summary="Link memory to component", tags=["Memory Intelligence"])
def link_memory_to_component(memory_id: str, component_name: str):
    """Link a memory to a component it affects."""
    try:
        return GRAPH_INTELLIGENCE.link_memory_to_component(
            memory_id=memory_id,
            component_name=component_name
        )
    except Exception as e:
        logger.exception("Error linking memory to component:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/impact/{component_name}", summary="Analyze component impact", tags=["Memory Intelligence"])
def analyze_impact(component_name: str):
    """Analyze what would be impacted if a component changes."""
    try:
        return GRAPH_INTELLIGENCE.get_impact_analysis(component_name=component_name)
    except Exception as e:
        logger.exception("Error analyzing impact:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/decision", summary="Create decision", tags=["Memory Intelligence"])
def create_decision(decision_req: DecisionRequest):
    """Create a decision node with pros, cons, and alternatives."""
    try:
        return GRAPH_INTELLIGENCE.create_decision(
            text=decision_req.text,
            user_id=decision_req.user_id,
            pros=decision_req.pros,
            cons=decision_req.cons,
            alternatives=decision_req.alternatives,
            metadata=decision_req.metadata
        )
    except Exception as e:
        logger.exception("Error creating decision:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/decision/{decision_id}", summary="Get decision rationale", tags=["Memory Intelligence"])
def get_decision(decision_id: str):
    """Get the complete rationale for a decision."""
    try:
        return GRAPH_INTELLIGENCE.get_decision_rationale(decision_id=decision_id)
    except Exception as e:
        logger.exception("Error getting decision rationale:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/communities", summary="Detect memory communities", tags=["Memory Intelligence"])
def get_communities(user_id: str):
    """Detect clusters of related memories (topics/themes)."""
    try:
        return GRAPH_INTELLIGENCE.detect_memory_communities(user_id=user_id)
    except Exception as e:
        logger.exception("Error detecting communities:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/trust-score/{memory_id}", summary="Calculate trust score", tags=["Memory Intelligence"])
def get_trust_score(memory_id: str):
    """Calculate trust score for a memory."""
    try:
        return GRAPH_INTELLIGENCE.calculate_trust_score(memory_id=memory_id)
    except Exception as e:
        logger.exception("Error calculating trust score:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/intelligence", summary="Memory Intelligence Analysis", tags=["Memory Intelligence"])
def analyze_intelligence(user_id: str):
    """
    🚀 GAME-CHANGER ENDPOINT 🚀

    Generate comprehensive intelligence report about user's memory graph.
    Combines temporal analysis, relationship mapping, quality scoring, and actionable insights.
    """
    try:
        return GRAPH_INTELLIGENCE.analyze_memory_intelligence(user_id=user_id)
    except Exception as e:
        logger.exception("Error analyzing memory intelligence:")
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
