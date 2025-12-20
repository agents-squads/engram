"""
Embedding Truncation Wrapper for Matryoshka Representation Learning (MRL).

Supports models like qwen3-embedding:4b that output larger embeddings
but can be safely truncated to smaller dimensions (e.g., 2560 -> 1536).
"""

from typing import List, Union
import logging

logger = logging.getLogger(__name__)


class TruncateEmbedder:
    """
    Wrapper around mem0's embedder that truncates embeddings to target dimensions.

    Useful for MRL-compatible models that output high-dimensional embeddings
    but can be truncated without significant quality loss.
    """

    def __init__(self, base_embedder, target_dims: int):
        """
        Initialize truncate embedder.

        Args:
            base_embedder: The original mem0 embedder instance
            target_dims: Target number of dimensions to truncate to
        """
        self.base_embedder = base_embedder
        self.target_dims = target_dims
        logger.info(f"TruncateEmbedder initialized: truncating to {target_dims} dimensions")

    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings and truncate to target dimensions.

        Args:
            text: Single text string or list of texts

        Returns:
            Truncated embedding(s)
        """
        # Get embeddings from base embedder
        embeddings = self.base_embedder.embed(text)

        # Handle single embedding
        if isinstance(embeddings, list) and isinstance(embeddings[0], float):
            original_dims = len(embeddings)
            if original_dims > self.target_dims:
                truncated = embeddings[:self.target_dims]
                logger.debug(f"Truncated embedding from {original_dims} to {self.target_dims} dims")
                return truncated
            return embeddings

        # Handle batch of embeddings
        elif isinstance(embeddings, list) and isinstance(embeddings[0], list):
            truncated_batch = []
            for emb in embeddings:
                original_dims = len(emb)
                if original_dims > self.target_dims:
                    truncated_batch.append(emb[:self.target_dims])
                else:
                    truncated_batch.append(emb)

            if len(embeddings) > 0 and len(embeddings[0]) > self.target_dims:
                logger.debug(f"Truncated {len(embeddings)} embeddings from {len(embeddings[0])} to {self.target_dims} dims")

            return truncated_batch

        return embeddings

    def __getattr__(self, name):
        """Forward all other attributes to base embedder."""
        return getattr(self.base_embedder, name)
