"""
MCP Server for Mem0 Integration with Claude Code

Provides 13 tools for managing coding preferences, memories, and graph intelligence via MCP protocol.

Core Memory Tools (5):
- add_coding_preference: Store code snippets and knowledge
- search_coding_preferences: Semantic search
- get_all_coding_preferences: Retrieve all memories
- delete_memory: Remove memories
- get_memory_history: View change history

Memory Intelligence Tools (8):
- link_memories: Create relationships between memories
- get_related_memories: Graph traversal to find connections
- analyze_memory_intelligence: 🚀 Comprehensive intelligence report (GAME-CHANGER)
- create_component: Map system architecture
- link_component_dependency: Define component dependencies
- analyze_component_impact: Impact analysis for changes
- create_decision: Track technical decisions with pros/cons
- get_decision_rationale: Retrieve decision context

Supports both SSE (legacy) and HTTP Stream (recommended) transports.
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

import asyncpg
import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, WebSocketRoute

import config
from auth import TokenAuthenticator
from text_chunker import chunk_text_semantic, add_chunk_markers

# Context variables for authentication
auth_token: ContextVar[str] = ContextVar('auth_token', default=None)
auth_user_id: ContextVar[str] = ContextVar('auth_user_id', default=None)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
# Session-based mode for proper lifespan integration with Starlette
mcp = FastMCP("mem0-mcp")

# Global instances (initialized in lifespan)
http_client = None
db_pool = None
authenticator = None


async def wait_for_server(max_retries: int = 30, delay: int = 2):
    """Wait for mem0 server to be ready."""
    async with httpx.AsyncClient(base_url=config.MEM0_API_URL, timeout=30.0) as client:
        for i in range(max_retries):
            try:
                response = await client.get("/")
                if response.status_code in [200, 307]:  # 307 is redirect to /docs
                    logger.info("✅ Mem0 server is ready!")
                    return True
            except Exception:
                logger.info(f"⏳ Waiting for mem0 server... ({i+1}/{max_retries})")
                await asyncio.sleep(delay)

    logger.error("❌ Failed to connect to mem0 server")
    return False


async def validate_auth() -> dict:
    """
    Validate authentication token and user_id from context variables.

    Returns:
        dict: {"valid": bool, "error": str, ...}
    """
    token = auth_token.get()
    user_id = auth_user_id.get()

    if not token or not user_id:
        return {
            "valid": False,
            "error": "Missing authentication credentials. Please ensure MEM0_TOKEN and MEM0_USER_ID are set in your environment and configured in Claude Code MCP settings."
        }

    auth_result = await authenticator.validate_token(token, user_id, None, "MCP-Tool-Call")

    if not auth_result["valid"]:
        logger.warning(f"❌ Auth failed for user {user_id}: {auth_result['error']}")
    else:
        logger.info(f"✅ Authenticated tool call: {auth_result['user_id']}")

    return auth_result


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to extract authentication headers and store in context variables."""

    async def dispatch(self, request: Request, call_next):
        """Extract X-MCP-Token and X-MCP-UserID headers and set context variables."""
        token = request.headers.get("X-MCP-Token")
        user_id = request.headers.get("X-MCP-UserID")

        # Set context variables for this request
        auth_token.set(token)
        auth_user_id.set(user_id)

        if token and user_id:
            logger.debug(f"🔐 Auth headers extracted: user_id={user_id}, token={token[:20]}...")

        response = await call_next(request)
        return response


# MCP Tool Definitions
@mcp.tool(
    description="""Add a new coding preference to mem0. This tool stores code snippets, implementation details,
    and coding patterns for future reference. When storing code, you should include:
    - Complete code with all necessary imports and dependencies
    - Language/framework version information (e.g., "Python 3.9", "React 18")
    - Full implementation context and any required setup/configuration
    - Detailed comments explaining the logic
    - Example usage or test cases
    - Any known limitations or performance considerations
    - Related patterns or alternative approaches
    The preference will be indexed for semantic search and can be retrieved later.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def add_coding_preference(text: str) -> str:
    """
    Add a new coding preference to mem0 with smart chunking for large texts.

    Args:
        text: The content to store in memory, including code, documentation, and context

    Note: Memories are automatically scoped to the current project.
    Authentication is handled automatically via MCP headers.
    Large texts (>1000 chars) are automatically chunked with semantic boundaries and overlap.
    """
    # Validate authentication from headers
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        # Generate unique run_id for this memory operation (required by mem0 for session tracking)
        run_id = str(uuid.uuid4())

        # Chunk text intelligently (handles both small and large texts)
        # Uses CHUNK_MAX_SIZE and CHUNK_OVERLAP_SIZE from config/env
        chunks = chunk_text_semantic(text, max_chunk_size=config.CHUNK_MAX_SIZE, overlap_size=config.CHUNK_OVERLAP_SIZE)

        if len(chunks) == 1 and not chunks[0]["is_chunked"]:
            # Small text - send as-is (fast path)
            payload = {
                "messages": [{"role": "user", "content": text}],
                "user_id": uid,
                "run_id": run_id
            }

            logger.info(f"📤 Sending memory request (single chunk) with run_id={run_id}")
            response = await http_client.post("/memories", json=payload)
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Successfully added memory")
            return f"✅ Successfully added preference for project '{uid}': {json.dumps(result, indent=2)}"

        else:
            # Large text - send chunks sequentially with metadata
            logger.info(f"📦 Large text detected: splitting into {len(chunks)} semantic chunks")
            results = []

            for chunk_data in chunks:
                # Add chunk markers for context
                chunk_text = add_chunk_markers(chunk_data)

                payload = {
                    "messages": [{"role": "user", "content": chunk_text}],
                    "user_id": uid,
                    "run_id": run_id,
                    "metadata": {
                        "chunk_index": chunk_data["chunk_index"],
                        "total_chunks": chunk_data["total_chunks"],
                        "chunk_size": chunk_data["chunk_size"],
                        "has_overlap": chunk_data.get("has_overlap", False)
                    }
                }

                logger.info(f"📤 Sending chunk {chunk_data['chunk_index'] + 1}/{chunk_data['total_chunks']} ({chunk_data['chunk_size']} chars)")
                response = await http_client.post("/memories", json=payload)
                response.raise_for_status()

                chunk_result = response.json()
                results.append(chunk_result)
                logger.info(f"✅ Chunk {chunk_data['chunk_index'] + 1}/{chunk_data['total_chunks']} stored successfully")

            # Return summary of all chunks stored
            summary = {
                "status": "success",
                "total_chunks": len(chunks),
                "chunks_stored": len(results),
                "project_id": uid,
                "run_id": run_id,
                "chunk_ids": [r.get("id") for r in results if "id" in r]
            }

            logger.info(f"✅ Successfully stored {len(chunks)} chunks for large text")
            return f"✅ Successfully added large preference ({len(chunks)} chunks) for project '{uid}':\n{json.dumps(summary, indent=2)}"

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        logger.error(f"HTTP error adding preference: {e.response.status_code} - {error_detail}")
        return f"❌ Error adding preference: HTTP {e.response.status_code} - {error_detail}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error adding preference: {e}", exc_info=True)
        return f"❌ Error adding preference: {str(e)}"
    except Exception as e:
        logger.error(f"Error adding preference: {e}", exc_info=True)
        return f"❌ Error adding preference: {str(e)}"


@mcp.tool(
    description="""Retrieve all stored coding preferences for the current project. Call this tool when you need
    complete context of all previously stored preferences. Returns:
    - Code snippets and implementation patterns
    - Programming knowledge and best practices
    - Technical documentation and examples
    - Setup and configuration guides
    Results are returned in JSON format with metadata.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def get_all_coding_preferences() -> str:
    """
    Get all coding preferences for the current project.

    Returns a JSON formatted list of all stored preferences with metadata.
    Note: Memories are automatically scoped to the current project.
    Authentication is handled automatically via MCP headers.
    """
    # Validate authentication from headers
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        response = await http_client.get("/memories", params={"user_id": uid})
        response.raise_for_status()

        memories = response.json()
        return json.dumps(memories, indent=2)
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting preferences: {e}")
        return f"❌ Error getting preferences: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return f"❌ Error getting preferences: {str(e)}"


@mcp.tool(
    description="""Search through stored coding preferences using semantic search. This tool helps find:
    - Specific code implementations or patterns
    - Solutions to programming problems
    - Best practices and coding standards
    - Setup and configuration guides
    - Technical documentation and examples
    The search uses natural language understanding to find relevant matches.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def search_coding_preferences(query: str, limit: int = 10) -> str:
    """
    Search coding preferences using semantic search.

    Args:
        query: Search query describing what you're looking for
        limit: Maximum number of results to return (default: 10)

    Returns ranked results by relevance.
    Note: Searches are automatically scoped to the current project.
    Authentication is handled automatically via MCP headers.
    """
    # Validate authentication from headers
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        payload = {
            "query": query,
            "user_id": uid
        }

        response = await http_client.post("/search", json=payload)
        response.raise_for_status()

        results = response.json()

        # Extract and limit results
        if isinstance(results, dict) and "results" in results:
            memories = results.get("results", [])[:limit]
            return json.dumps(memories, indent=2)

        return json.dumps(results, indent=2)
    except httpx.HTTPError as e:
        logger.error(f"HTTP error searching preferences: {e}")
        return f"❌ Error searching preferences: {str(e)}"
    except Exception as e:
        logger.error(f"Error searching preferences: {e}")
        return f"❌ Error searching preferences: {str(e)}"


@mcp.tool(
    description="""Delete a specific memory by its ID. Use this to remove outdated or incorrect information.
    Only memories owned by the authenticated user can be deleted.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def delete_memory(memory_id: str) -> str:
    """
    Delete a specific memory by ID with ownership validation.

    Args:
        memory_id: The ID of the memory to delete

    Note: Authentication is handled automatically via MCP headers.
    Only the owner of the memory can delete it.
    """
    # Validate authentication from headers
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        response = await http_client.delete(f"/memories/{memory_id}", params={"user_id": uid})
        response.raise_for_status()

        return f"✅ Successfully deleted memory {memory_id}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return f"❌ Access denied: Memory {memory_id} does not belong to your project"
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        logger.error(f"HTTP error deleting memory: {e.response.status_code} - {error_detail}")
        return f"❌ Error deleting memory: HTTP {e.response.status_code} - {error_detail}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error deleting memory: {e}")
        return f"❌ Error deleting memory: {str(e)}"
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return f"❌ Error deleting memory: {str(e)}"


@mcp.tool(
    description="""Get the history of a specific memory to see how it evolved over time.
    Only the owner of the memory can view its history.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def get_memory_history(memory_id: str) -> str:
    """
    Get the history of changes for a specific memory with ownership validation.

    Args:
        memory_id: The ID of the memory to get history for

    Note: Authentication is handled automatically via MCP headers.
    Only the owner of the memory can view its history.
    """
    # Validate authentication from headers
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        response = await http_client.get(f"/memories/{memory_id}/history", params={"user_id": uid})
        response.raise_for_status()

        history = response.json()
        return json.dumps(history, indent=2)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return f"❌ Access denied: Memory {memory_id} does not belong to your project"
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        logger.error(f"HTTP error getting memory history: {e.response.status_code} - {error_detail}")
        return f"❌ Error getting memory history: HTTP {e.response.status_code} - {error_detail}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting memory history: {e}")
        return f"❌ Error getting memory history: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting memory history: {e}")
        return f"❌ Error getting memory history: {str(e)}"


# ============================================
# MEMORY INTELLIGENCE - GRAPH MCP TOOLS
# ============================================

@mcp.tool(
    description="""Link two memories with a typed relationship to build knowledge graphs.

    Relationship types:
    - RELATES_TO: General association between memories
    - DEPENDS_ON: One memory depends on another (e.g., feature depends on infrastructure)
    - SUPERSEDES: New memory replaces/updates old knowledge
    - RESPONDS_TO: Conversation thread continuation
    - EXTENDS: Adds detail to previous memory
    - CONFLICTS_WITH: Contradictory information flagged for review

    Use this to create rich semantic connections between memories for better context retrieval.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def link_memories(memory_id_1: str, memory_id_2: str, relationship_type: str = "RELATES_TO") -> str:
    """
    Create a typed relationship between two memories in the knowledge graph.

    Args:
        memory_id_1: First memory ID
        memory_id_2: Second memory ID
        relationship_type: Type of relationship (RELATES_TO, DEPENDS_ON, SUPERSEDES, etc.)

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        payload = {
            "memory_id_1": memory_id_1,
            "memory_id_2": memory_id_2,
            "relationship_type": relationship_type
        }

        response = await http_client.post("/graph/link", json=payload)
        response.raise_for_status()

        result = response.json()
        return f"✅ Successfully linked memories: {json.dumps(result, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error linking memories: {e}")
        return f"❌ Error linking memories: {str(e)}"
    except Exception as e:
        logger.error(f"Error linking memories: {e}")
        return f"❌ Error linking memories: {str(e)}"


@mcp.tool(
    description="""Get all memories related to a specific memory within N hops in the knowledge graph.

    This traverses the graph to find connected memories, helping you discover:
    - Related context and dependencies
    - Conversation threads
    - Knowledge evolution chains
    - Impact analysis for changes

    Returns memories with their relationship paths and distance from the source.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def get_related_memories(memory_id: str, depth: int = 2) -> str:
    """
    Get all memories related to a specific memory by traversing the graph.

    Args:
        memory_id: The memory ID to start from
        depth: How many hops to traverse (default: 2, max recommended: 3)

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        response = await http_client.get(f"/graph/related/{memory_id}", params={"depth": depth})
        response.raise_for_status()

        related = response.json()
        return json.dumps(related, indent=2)
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting related memories: {e}")
        return f"❌ Error getting related memories: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting related memories: {e}")
        return f"❌ Error getting related memories: {str(e)}"


@mcp.tool(
    description="""🚀 GAME-CHANGER: Generate comprehensive intelligence report about your project's knowledge graph.

    This analyzes your entire memory network to provide:
    - **Health Score**: Overall knowledge graph connectivity and quality
    - **Memory Statistics**: Total memories, connections, isolated nodes
    - **Knowledge Clusters**: Automatically detected topic groups
    - **Central Memories**: Most connected/important memories
    - **Obsolete Detection**: Superseded/outdated information
    - **Conflict Detection**: Contradictory information flagged
    - **Actionable Recommendations**: Specific suggestions to improve knowledge quality

    Use this to understand your project's knowledge landscape and identify areas needing attention.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def analyze_memory_intelligence() -> str:
    """
    Generate comprehensive intelligence analysis of your project's memory graph.

    This is the most powerful tool - it combines all graph analysis capabilities to give you
    deep insights into your project's knowledge structure, quality, and areas for improvement.

    Note: Authentication is handled automatically via MCP headers.
    Automatically scoped to current project.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        response = await http_client.get("/graph/intelligence", params={"user_id": uid})
        response.raise_for_status()

        intelligence = response.json()
        return f"📊 **Memory Intelligence Report for Project '{uid}'**\n\n{json.dumps(intelligence, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error analyzing intelligence: {e}")
        return f"❌ Error analyzing intelligence: {str(e)}"
    except Exception as e:
        logger.error(f"Error analyzing intelligence: {e}")
        return f"❌ Error analyzing intelligence: {str(e)}"


@mcp.tool(
    description="""Create a technical component node in the knowledge graph (Feature, Service, Database, API, etc.).

    Components represent parts of your system architecture. Use this to:
    - Map system architecture and dependencies
    - Track which memories affect which components
    - Perform impact analysis when components change
    - Understand cascading effects of changes

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def create_component(name: str, component_type: str = "Component") -> str:
    """
    Create a technical component node in the knowledge graph.

    Args:
        name: Component name (e.g., "Authentication Service", "PostgreSQL Database")
        component_type: Type (Infrastructure, Service, API, Feature, Library, etc.)

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        payload = {
            "name": name,
            "component_type": component_type
        }

        response = await http_client.post("/graph/component", json=payload)
        response.raise_for_status()

        result = response.json()
        return f"✅ Created component: {json.dumps(result, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error creating component: {e}")
        return f"❌ Error creating component: {str(e)}"
    except Exception as e:
        logger.error(f"Error creating component: {e}")
        return f"❌ Error creating component: {str(e)}"


@mcp.tool(
    description="""Create a dependency between two components (e.g., "API depends on Database").

    Use this to map your system architecture and understand:
    - Component dependencies and relationships
    - What breaks if a component changes
    - Cascading impact of infrastructure changes
    - Critical paths in your system

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def link_component_dependency(component_from: str, component_to: str, dependency_type: str = "DEPENDS_ON") -> str:
    """
    Create a dependency relationship between two components.

    Args:
        component_from: Source component name
        component_to: Target component name
        dependency_type: Type of dependency (DEPENDS_ON, USES, EXTENDS, etc.)

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        params = {
            "component_from": component_from,
            "component_to": component_to,
            "dependency_type": dependency_type
        }

        response = await http_client.post("/graph/component/dependency", params=params)
        response.raise_for_status()

        result = response.json()
        return f"✅ Linked component dependency: {json.dumps(result, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error linking component dependency: {e}")
        return f"❌ Error linking component dependency: {str(e)}"
    except Exception as e:
        logger.error(f"Error linking component dependency: {e}")
        return f"❌ Error linking component dependency: {str(e)}"


@mcp.tool(
    description="""Analyze the impact of changing a component - what else would be affected?

    This performs graph traversal to find:
    - All dependent components (what depends on this)
    - Memories associated with the component
    - Cascade impact (downstream dependencies)
    - Impact score (severity of changes)

    Use before making architectural changes to understand the full scope of impact.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def analyze_component_impact(component_name: str) -> str:
    """
    Analyze what would be impacted if a component changes.

    Args:
        component_name: Name of the component to analyze

    Returns detailed impact analysis including dependent components, affected memories,
    and cascading effects throughout the system.

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        response = await http_client.get(f"/graph/impact/{component_name}")
        response.raise_for_status()

        impact = response.json()
        return f"📊 **Impact Analysis for '{component_name}'**\n\n{json.dumps(impact, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error analyzing impact: {e}")
        return f"❌ Error analyzing impact: {str(e)}"
    except Exception as e:
        logger.error(f"Error analyzing impact: {e}")
        return f"❌ Error analyzing impact: {str(e)}"


@mcp.tool(
    description="""Create a decision node with pros, cons, and alternatives considered.

    Use this to track important technical decisions:
    - Why did we choose technology X over Y?
    - What were the tradeoffs considered?
    - What alternatives were evaluated?
    - What are the known limitations?

    Creates a structured decision record that can be retrieved later to understand
    historical context and reasoning.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def create_decision(
    text: str,
    pros: str = None,
    cons: str = None,
    alternatives: str = None
) -> str:
    """
    Create a decision node with structured rationale.

    Args:
        text: The decision text (e.g., "Use PostgreSQL as primary database")
        pros: Comma-separated pros (e.g., "ACID compliance,Mature ecosystem,pgvector support")
        cons: Comma-separated cons (e.g., "Scaling complexity,Higher resource usage")
        alternatives: Comma-separated alternatives considered (e.g., "MongoDB,MySQL,DynamoDB")

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        uid = config.CURRENT_PROJECT_ID
        payload = {
            "text": text,
            "user_id": uid,
            "pros": [p.strip() for p in pros.split(",")] if pros else [],
            "cons": [c.strip() for c in cons.split(",")] if cons else [],
            "alternatives": [a.strip() for a in alternatives.split(",")] if alternatives else []
        }

        response = await http_client.post("/graph/decision", json=payload)
        response.raise_for_status()

        result = response.json()
        return f"✅ Created decision: {json.dumps(result, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error creating decision: {e}")
        return f"❌ Error creating decision: {str(e)}"
    except Exception as e:
        logger.error(f"Error creating decision: {e}")
        return f"❌ Error creating decision: {str(e)}"


@mcp.tool(
    description="""Retrieve the complete rationale for a past decision.

    Returns:
    - The decision text
    - All pros that were considered
    - All cons that were considered
    - Alternative options that were evaluated
    - When the decision was made

    Use this to understand why past technical choices were made.

    **Authentication**: Automatically uses credentials from MCP configuration headers."""
)
async def get_decision_rationale(decision_id: str) -> str:
    """
    Get the complete rationale and context for a decision.

    Args:
        decision_id: The decision ID (returned from create_decision)

    Note: Authentication is handled automatically via MCP headers.
    """
    auth_result = await validate_auth()
    if not auth_result["valid"]:
        return f"❌ Authentication failed: {auth_result['error']}"

    try:
        response = await http_client.get(f"/graph/decision/{decision_id}")
        response.raise_for_status()

        rationale = response.json()
        return f"📝 **Decision Rationale**\n\n{json.dumps(rationale, indent=2)}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting decision rationale: {e}")
        return f"❌ Error getting decision rationale: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting decision rationale: {e}")
        return f"❌ Error getting decision rationale: {str(e)}"


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that serves the MCP server with both SSE and HTTP Stream transports."""
    # Configure SSE transport (legacy, for backward compatibility)
    sse = SseServerTransport("/messages/")

    # Create wrapper class for SSE ASGI app
    class SSEApp:
        """ASGI app wrapper for SSE endpoint."""
        async def __call__(self, scope, receive, send):
            """Handle SSE connection (no authentication required for connection, auth is per-tool)."""
            if scope["type"] == "http":
                logger.info("📡 New SSE connection established")

                # Continue with SSE connection (authentication will be validated per-tool)
                async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                    await mcp_server.run(
                        read_stream,
                        write_stream,
                        mcp_server.create_initialization_options(),
                    )

    sse_app = SSEApp()

    # Create wrapper class for HTTP Stream ASGI app
    # This ensures proper logging and context handling for HTTP Stream requests
    class HTTPStreamApp:
        """ASGI app wrapper for HTTP Stream endpoint."""
        def __init__(self, streamable_app):
            self.streamable_app = streamable_app

        async def __call__(self, scope, receive, send):
            """Handle HTTP Stream connection with proper session_manager context."""
            if scope["type"] == "http":
                logger.info(f"🌐 HTTP Stream request: {scope['method']} {scope['path']}")

            try:
                # Forward the request to the streamable HTTP app
                # The session_manager.run() context from the parent lifespan
                # should be available here in session-based mode
                await self.streamable_app(scope, receive, send)
            except Exception as e:
                logger.error(f"❌ HTTP Stream error: {e}", exc_info=True)
                raise

    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint for Docker health checks."""
        return JSONResponse({
            "status": "healthy",
            "service": "mem0-mcp",
            "project_id": config.CURRENT_PROJECT_ID,
            "project_mode": config.PROJECT_ID_MODE,
        })

    @asynccontextmanager
    async def combined_lifespan(app):
        """Initialize and cleanup resources with proper FastMCP integration."""
        global http_client, db_pool, authenticator

        # Create PostgreSQL connection pool for authentication
        logger.info("Connecting to PostgreSQL for authentication...")
        db_pool = await asyncpg.create_pool(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            database=config.POSTGRES_DB,
            min_size=2,
            max_size=10
        )
        logger.info("✅ PostgreSQL connection pool created")

        # Initialize token authenticator
        authenticator = TokenAuthenticator(db_pool)
        logger.info("✅ Token authenticator initialized")

        # Initialize HTTP client for Mem0 API with extended timeout for large text chunking
        http_client = httpx.AsyncClient(base_url=config.MEM0_API_URL, timeout=180.0)
        logger.info("✅ HTTP client initialized with 180s timeout")

        # Start FastMCP session manager for HTTP Stream transport
        # This MUST be running for HTTP Stream requests to work
        logger.info("Starting FastMCP session manager...")
        async with mcp.session_manager.run():
            logger.info("✅ FastMCP session manager started and ready")
            # Yield here keeps session_manager active during the app's lifetime
            yield
            logger.info("Shutting down FastMCP session manager...")

        # Cleanup resources
        await http_client.aclose()
        logger.info("✅ HTTP client closed")

        await db_pool.close()
        logger.info("✅ Database pool closed")

    # Configure FastMCP for Streamable HTTP (modern, recommended)
    mcp.settings.streamable_http_path = "/"  # Mount at root of /mcp path
    http_stream_base_app = mcp.streamable_http_app()

    # Wrap the HTTP Stream app to ensure proper context propagation
    http_stream_app = HTTPStreamApp(http_stream_base_app)

    return Starlette(
        debug=debug,
        lifespan=combined_lifespan,
        routes=[
            Route("/", endpoint=health_check),
            # SSE transport (legacy, for backward compatibility)
            Mount("/sse", app=sse_app),
            Mount("/messages", app=sse.handle_post_message),
            # HTTP Stream transport (modern, recommended)
            Mount("/mcp", app=http_stream_app),
        ],
        middleware=[
            Middleware(AuthMiddleware)
        ],
    )


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default=config.MCP_HOST, help='Host to bind to')
    parser.add_argument('--port', type=int, default=config.MCP_PORT, help='Port to listen on')
    parser.add_argument('--skip-wait', action='store_true', help='Skip waiting for mem0 server')
    args = parser.parse_args()

    # Wait for mem0 server to be ready (unless skipped)
    if not args.skip_wait:
        if not asyncio.run(wait_for_server()):
            logger.error("Failed to connect to mem0 server. Exiting.")
            exit(1)

    logger.info(f"🚀 Starting MCP server on {args.host}:{args.port}")
    logger.info(f"📡 SSE endpoint (legacy): http://{args.host}:{args.port}/sse")
    logger.info(f"🌐 HTTP Stream endpoint (recommended): http://{args.host}:{args.port}/mcp")
    logger.info(f"🔗 Mem0 API: {config.MEM0_API_URL}")
    logger.info(f"🔧 Project ID Mode: {config.PROJECT_ID_MODE}")
    logger.info(f"👤 Current Project ID: {config.CURRENT_PROJECT_ID}")

    # Create and run the Starlette app
    mcp_server = mcp._mcp_server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)
