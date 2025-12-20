"""
Smart Text Chunking for Large Memory Operations

Implements semantic chunking strategies to handle large text inputs efficiently.
Chunks are created with overlap to preserve context across boundaries.
"""

import os
import re
from typing import List, Dict, Optional


def chunk_text_semantic(
    text: str,
    max_chunk_size: Optional[int] = None,
    overlap_size: Optional[int] = None
) -> List[Dict[str, any]]:
    """
    Smart chunking with semantic boundaries and overlap.

    Strategy:
    1. Split by double newlines (paragraphs) first
    2. If paragraph too large, split by sentences
    3. Add overlap between chunks for context continuity

    Args:
        text: Text to chunk
        max_chunk_size: Maximum characters per chunk (default: from env CHUNK_MAX_SIZE or 1000)
        overlap_size: Characters to overlap between chunks (default: from env CHUNK_OVERLAP_SIZE or 150)

    Returns:
        List of chunk dictionaries with metadata
    """
    # Use environment variables if parameters not provided
    if max_chunk_size is None:
        max_chunk_size = int(os.getenv("CHUNK_MAX_SIZE", "1000"))
    if overlap_size is None:
        overlap_size = int(os.getenv("CHUNK_OVERLAP_SIZE", "150"))

    # If text is small enough, return as single chunk
    if len(text) <= max_chunk_size:
        return [{
            "text": text,
            "chunk_index": 0,
            "total_chunks": 1,
            "chunk_size": len(text),
            "is_chunked": False
        }]

    chunks = []

    # Split by paragraphs first (double newline)
    paragraphs = re.split(r'\n\n+', text)

    current_chunk = ""
    overlap_buffer = ""

    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph exceeds limit
        if len(current_chunk) + len(para) + 2 > max_chunk_size and current_chunk:
            # Save current chunk
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap from end of previous
            if len(current_chunk) > overlap_size:
                overlap_buffer = current_chunk[-overlap_size:]
                current_chunk = overlap_buffer + "\n\n" + para
            else:
                current_chunk = para
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

        # If this paragraph itself is too large, split by sentences
        if len(current_chunk) > max_chunk_size * 1.5:
            # Split oversized chunk by sentences
            sentences = re.split(r'(?<=[.!?])\s+', current_chunk)
            temp_chunk = ""

            for sentence in sentences:
                if len(temp_chunk) + len(sentence) > max_chunk_size and temp_chunk:
                    chunks.append(temp_chunk.strip())
                    # Add overlap
                    if len(temp_chunk) > overlap_size:
                        temp_chunk = temp_chunk[-overlap_size:] + " " + sentence
                    else:
                        temp_chunk = sentence
                else:
                    temp_chunk += (" " if temp_chunk else "") + sentence

            current_chunk = temp_chunk

    # Add last chunk
    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Build result with metadata
    total_chunks = len(chunks)
    result = []

    for idx, chunk in enumerate(chunks):
        result.append({
            "text": chunk,
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "chunk_size": len(chunk),
            "is_chunked": total_chunks > 1,
            "has_overlap": idx > 0 and overlap_size > 0
        })

    return result


def add_chunk_markers(chunk_data: Dict[str, any]) -> str:
    """
    Add visual markers to chunked text for clarity.

    Args:
        chunk_data: Chunk dictionary with metadata

    Returns:
        Text with chunk markers prepended
    """
    if not chunk_data["is_chunked"]:
        return chunk_data["text"]

    marker = f"[Part {chunk_data['chunk_index'] + 1}/{chunk_data['total_chunks']}]"
    return f"{marker}\n\n{chunk_data['text']}"


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of tokens (1 token ≈ 4 characters for English).

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    # Simple heuristic: 1 token ≈ 4 characters
    # More accurate would use tiktoken, but adds dependency
    return len(text) // 4


def should_chunk(text: str, threshold: int = 1000) -> bool:
    """
    Determine if text should be chunked.

    Args:
        text: Text to evaluate
        threshold: Character threshold for chunking

    Returns:
        True if text should be chunked
    """
    return len(text) > threshold
