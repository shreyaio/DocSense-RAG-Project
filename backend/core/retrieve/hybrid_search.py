from typing import List, Dict, Any, Optional, Tuple
from storage.base import VectorStore, BM25Store
from core.embed.embedder import Embedder
from models.query import QueryFilters
from config.settings import settings
import collections


class HybridSearcher:
    """
    Orchestrates dense (vector) and sparse (BM25) search with RRF fusion.
    Sparse-only hits are resolved via VectorStore.get_by_ids() so no RRF
    candidate is silently dropped.
    """

    def __init__(self, vector_store: VectorStore, bm25_store: BM25Store, embedder: Embedder):
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.embedder = embedder
        self.config = settings.retrieval

    def search(self,
               question: str,
               doc_ids: List[str],
               filters: QueryFilters) -> List[Dict[str, Any]]:
        """
        Performs hybrid search and returns fused results.
        """
        # 1. Dense Search Arm
        query_vector = self.embedder.embed_query(question)

        # Prepare Qdrant filters
        dense_filters = {"doc_id": doc_ids[0]} if doc_ids and len(doc_ids) == 1 else None
        # Note: Multi-doc dense filtering requires an 'any' filter — Phase 1 limitation.

        if filters.page_range:
            # Simple page filter for dense arm if single page
            if filters.page_range[0] == filters.page_range[1]:
                if not dense_filters:
                    dense_filters = {}
                dense_filters["page_number"] = filters.page_range[0]

        dense_results = self.vector_store.search(
            vector=query_vector,
            top_k=self.config.dense_top_k,
            filters=dense_filters
        )

        # 2. Sparse Search Arm
        sparse_hits = []
        for d_id in doc_ids:
            hits = self.bm25_store.search(d_id, question, top_k=self.config.sparse_top_k)
            sparse_hits.extend(hits)

        # Sort combined sparse hits by score and take top_k
        sparse_hits = sorted(sparse_hits, key=lambda x: x[1], reverse=True)[:self.config.sparse_top_k]

        # 3. RRF Fusion — rrf_score = sum(1 / (k + rank))
        rrf_k = self.config.rrf_k
        fused_scores: Dict[str, float] = collections.defaultdict(float)
        payloads: Dict[str, Dict] = {}

        for rank, hit in enumerate(dense_results, 1):
            c_id = hit["chunk_id"]
            fused_scores[c_id] += 1.0 / (rrf_k + rank)
            payloads[c_id] = hit["payload"]

        for rank, (c_id, score) in enumerate(sparse_hits, 1):
            fused_scores[c_id] += 1.0 / (rrf_k + rank)
            # Payload will be resolved below for any sparse-only hits

        # 4. Sort and select top candidates
        fused_sorted = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        top_candidates = fused_sorted[:self.config.rerank_top_k]

        # 5. Fix 3: Resolve payloads for sparse-only hits via get_by_ids.
        # Without this, chunks that BM25 found but dense search missed are silently dropped,
        # which defeats the entire purpose of RRF fusion.
        sparse_only_ids = [c_id for c_id, _ in top_candidates if c_id not in payloads]
        if sparse_only_ids:
            fetched = self.vector_store.get_by_ids(sparse_only_ids)
            for item in fetched:
                payloads[item["chunk_id"]] = item["payload"]

        # 6. Assemble final result list (only include candidates with resolved payloads)
        final_results = []
        for c_id, rrf_score in top_candidates:
            if c_id in payloads:
                final_results.append({
                    "chunk_id": c_id,
                    "rrf_score": rrf_score,
                    "payload": payloads[c_id]
                })

        return final_results
