"""
Configuration module for MCP Server.

Handles project isolation and API connection settings.
"""

import os
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# API Configuration
MEM0_API_URL = os.getenv("MEM0_API_URL", "http://mem0:8000")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "claude_code_mcp")

# MCP Server Configuration
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))

# PostgreSQL Configuration (for authentication)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Smart Text Chunking Configuration
CHUNK_MAX_SIZE = int(os.getenv("CHUNK_MAX_SIZE", "1000"))
CHUNK_OVERLAP_SIZE = int(os.getenv("CHUNK_OVERLAP_SIZE", "150"))

# Project Isolation Mode
# - "auto": Auto-detect project from working directory (default)
# - "manual": Use DEFAULT_USER_ID explicitly
# - "global": Share memories across all projects
PROJECT_ID_MODE = os.getenv("PROJECT_ID_MODE", "auto")


def get_project_id() -> str:
    """
    Generate a project-specific user ID based on the working directory.

    Modes:
    - "auto": Generate project ID from current working directory (default)
    - "manual": Use DEFAULT_USER_ID (must be set explicitly per project)
    - "global": Use DEFAULT_USER_ID for all projects (original behavior)

    Returns:
        A stable project identifier string
    """
    if PROJECT_ID_MODE == "global":
        return DEFAULT_USER_ID

    if PROJECT_ID_MODE == "manual":
        return DEFAULT_USER_ID

    # Auto mode: generate from working directory
    try:
        # Get current working directory from environment or default
        cwd = os.getenv("PROJECT_DIR", os.getcwd())
        project_path = Path(cwd).resolve()

        # Use project directory name + hash of full path for uniqueness
        project_name = project_path.name
        path_hash = hashlib.sha256(str(project_path).encode()).hexdigest()[:8]

        project_id = f"project_{project_name}_{path_hash}"
        logger.info(f"🔍 Auto-detected project ID: {project_id} (from {project_path})")

        return project_id
    except Exception as e:
        logger.warning(f"⚠️  Failed to auto-detect project: {e}. Using default user ID.")
        return DEFAULT_USER_ID


# Get the current project ID
CURRENT_PROJECT_ID = get_project_id()
