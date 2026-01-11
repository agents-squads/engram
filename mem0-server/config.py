"""
Configuration module for Mem0 REST API Server.

Handles environment-based configuration with smart defaults.
"""

import os
from typing import Dict, Any

# Database Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_COLLECTION_NAME = os.getenv("POSTGRES_COLLECTION_NAME", "memories")


# LLM Provider Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.2:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:8b")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:8b")
OLLAMA_EMBEDDING_DIMS = int(os.getenv("OLLAMA_EMBEDDING_DIMS", "4096"))

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_EMBEDDING_DIMS = int(os.getenv("OPENAI_EMBEDDING_DIMS", "1536"))

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# Other Configuration
HISTORY_DB_PATH = os.getenv("HISTORY_DB_PATH", "/app/history/history.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration based on provider."""
    if LLM_PROVIDER == "openai":
        return {
            "provider": "openai",
            "config": {
                "api_key": OPENAI_API_KEY,
                "model": OPENAI_LLM_MODEL,
                "temperature": 0.2,
            }
        }
    elif LLM_PROVIDER == "anthropic":
        return {
            "provider": "anthropic",
            "config": {
                "api_key": ANTHROPIC_API_KEY,
                "model": ANTHROPIC_MODEL,
                "temperature": 0.2,
            }
        }
    else:  # Default to Ollama
        return {
            "provider": "ollama",
            "config": {
                "model": OLLAMA_LLM_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
                "temperature": 0.2,
            }
        }


def get_embedder_config() -> Dict[str, Any]:
    """Get embedder configuration based on provider."""
    if LLM_PROVIDER == "openai":
        embedding_dims = OPENAI_EMBEDDING_DIMS
        return {
            "provider": "openai",
            "config": {
                "api_key": OPENAI_API_KEY,
                "model": OPENAI_EMBEDDING_MODEL,
                "embedding_dims": embedding_dims,
            }
        }
    else:  # Default to Ollama (Anthropic uses embeddings from another provider)
        embedding_dims = OLLAMA_EMBEDDING_DIMS
        return {
            "provider": "ollama",
            "config": {
                "model": OLLAMA_EMBEDDING_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
                "embedding_dims": embedding_dims,
            }
        }


def get_vector_store_config() -> Dict[str, Any]:
    """Get vector store configuration with smart HNSW toggle."""
    # Determine embedding dimensions based on provider
    if LLM_PROVIDER == "openai":
        embedding_dims = OPENAI_EMBEDDING_DIMS
    else:
        embedding_dims = OLLAMA_EMBEDDING_DIMS

    # Disable HNSW if dimensions > 2000 (pgvector limitation)
    use_hnsw = embedding_dims <= 2000

    return {
        "provider": "pgvector",
        "config": {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "collection_name": POSTGRES_COLLECTION_NAME,
            "embedding_model_dims": embedding_dims,
            "hnsw": use_hnsw,
        }
    }


def get_mem0_config() -> Dict[str, Any]:
    """Get complete Mem0 configuration."""
    return {
        "version": "v1.1",
        "vector_store": get_vector_store_config(),
        "llm": get_llm_config(),
        "embedder": get_embedder_config(),
        "history_db_path": HISTORY_DB_PATH,
    }
