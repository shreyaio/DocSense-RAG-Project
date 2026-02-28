import logging
from typing import List
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from models.chunk import ChildChunk
from config.settings import settings

logger = logging.getLogger(__name__)

class Embedder:
    """
    Handles embedding generation for document chunks.
    - Uses singleton-style model loading to save memory.
    - Supports batched embedding and L2 normalisation.
    """
    
    _model = None

    def __init__(self):
        self.config = settings.embedding
        self._load_model()

    def _load_model(self):
        """Loads the sentence-transformer model onto CPU."""
        if Embedder._model is None:
            logger.info(f"Loading embedding model: {self.config.model_name}...")
            # We explicitly use CPU as per architecture guidelines (No Docker/Free Tier)
            Embedder._model = SentenceTransformer(self.config.model_name, device="cpu")
        self.model = Embedder._model

    def embed_chunks(self, chunks: List[ChildChunk]) -> List[ChildChunk]:
        """
        Generates embeddings for a list of ChildChunks in batches.
        Updates the 'embedding' field of each chunk in-place.
        """
        if not chunks:
            return chunks

        texts = [c.text for c in chunks]
        
        # Generate embeddings
        # BGE models work best with normalize_embeddings=True for cosine similarity
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self.config.normalise
        )

        # Attach to chunks as list of floats
        for i, chunk in enumerate(chunks):
            chunk.embedding = embeddings[i].tolist()

        return chunks

    def embed_query(self, query: str) -> List[float]:
        """
        Generates an embedding for a single query string.
        Applies the query prefix required by BGE models.
        """
        # BGE requires a specific prefix for queries to perform optimally
        prefixed_query = f"{self.config.query_prefix}{query}"
        
        embedding = self.model.encode(
            prefixed_query,
            normalize_embeddings=self.config.normalise
        )
        
        return embedding.tolist()
