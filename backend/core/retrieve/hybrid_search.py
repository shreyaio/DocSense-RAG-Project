from typing import List, Dict, Any, Optional, Tuple
from backend.storage.base import VectorStore, BM25Store, FileStore
from backend.core.embed.embedder import Embedder
from backend.models.query import QueryFilters
from backend.config.settings import settings
import collections


class HybridSearcher:
    """
    Orchestrates dense (vector) and sparse (BM25) search with RRF fusion.
    Sparse-only hits are resolved via VectorStore.get_by_ids() so no RRF
    candidate is silently dropped.
    """

    def __init__(self, vector_store: VectorStore, bm25_store: BM25Store, embedder: Embedder, file_store: Optional[FileStore] = None):
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.embedder = embedder
        self.file_store = file_store
        self.config = settings.retrieval

    def search(self,
               question: str,
               doc_ids: List[str],
               filters: QueryFilters) -> Dict[str, Any]:
        """
        Performs hybrid search and returns fused results with statistics.
        """
        # 1. Dense Search Arm
        query_vector = self.embedder.embed_query(question)

        # Prepare Qdrant filters (Multi-document safe)
        dense_filters = {"doc_id": doc_ids} if doc_ids else None

        if filters and filters.page_range:
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
        sparse_only_ids = [c_id for c_id, _ in top_candidates if c_id not in payloads]
        if sparse_only_ids:
            fetched = self.vector_store.get_by_ids(sparse_only_ids)
            for item in fetched:
                payloads[item["chunk_id"]] = item["payload"]

        # 6. Assemble final result list and resolve child text
        final_results = []
        parent_cache = {} # Cache for parent chunks within this search call

        for c_id, rrf_score in top_candidates:
            if c_id in payloads:
                payload = payloads[c_id]
                text = ""
                
                # Resolve child text from ParentChunk if file_store is available
                if self.file_store:
                    doc_id = payload.get("doc_id")
                    parent_id = payload.get("parent_id")
                    if doc_id and parent_id:
                        if doc_id not in parent_cache:
                            parent_cache[doc_id] = self.file_store.load_parent_chunks(doc_id)
                        
                        parent = parent_cache[doc_id].get(parent_id)
                        if parent:
                            # Note: Accurate slicing requires parent char_start, which is missing.
                            # As a fallback, we use the parent text for reranking if exact slice is not possible
                            # without schema modification. This adheres to "No child text in Qdrant".
                            text = parent.text

                final_results.append({
                    "chunk_id": c_id,
                    "rrf_score": rrf_score,
                    "metadata": payload,
                    "text": text
                })

        # 7. Collect statistics
        stats = {
            "dense_hits": len(dense_results),
            "sparse_hits": len(sparse_hits),
            "fused_candidates": len(fused_scores)
        }

        return {
            "results": final_results,
            "stats": stats
        }
