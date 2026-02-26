from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
from config.settings import settings


class Reranker:
    """
    Refines search results using a cross-encoder model.
    Model name is loaded from config.yaml (retrieval.reranker_model).
    Runs on CPU for free-tier compatibility.
    """

    _model = None

    def __init__(self):
        self.config = settings.retrieval
        self._load_model()

    def _load_model(self):
        if Reranker._model is None:
            # Fix 2: Load model name from config, never hardcode it
            model_name = self.config.reranker_model
            print(f"Loading reranker model: {model_name}...")
            Reranker._model = CrossEncoder(model_name, device="cpu")
        self.model = Reranker._model

    def rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scores (query, passage) pairs and sorts results by relevance.
        Each candidate must have 'payload' containing the 'text' field (child chunk text).
        Note: 'text' is stored in Qdrant payload alongside ChunkMetadata fields.
        """
        if not candidates:
            return []

        # Fix 5 (consumed here): 'text' is now present in payload because qdrant_store.upsert
        # explicitly stores chunk.text in the payload dict alongside metadata fields.
        pairs = [[query, c["payload"].get("text", "")] for c in candidates]

        scores = self.model.predict(pairs)

        # Attach scores and sort
        for i, candidate in enumerate(candidates):
            candidate["rerank_score"] = float(scores[i])

        # Sort descending by rerank score
        sorted_results = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

        return sorted_results[:self.config.final_top_k]
