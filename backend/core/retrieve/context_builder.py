from typing import List, Dict, Any
from storage.base import FileStore
from models.query import RetrievedContext
from models.chunk import ChunkMetadata
from config.settings import settings

class ContextBuilder:
    """
    Assembles final context for the LLM by fetching parent chunks and deduplicating.
    """

    def __init__(self, file_store: FileStore):
        self.file_store = file_store
        # Cache for loaded parents to avoid repetitive disk reads during a single query
        self._parent_cache = {}

    def build(self, reranked_results: List[Dict[str, Any]]) -> List[RetrievedContext]:
        """
        Converts search results into full context by fetching parent text.
        Deduplicates by parent_id.
        """
        # Memory Expansion Fix 5: Pre-collect unique parent_ids per doc_id for batched loading
        docs_to_parents = {}
        for res in reranked_results:
            m = ChunkMetadata(**res["metadata"])
            d_id, p_id = m.doc_id, m.parent_id
            if d_id not in docs_to_parents:
                docs_to_parents[d_id] = set()
            docs_to_parents[d_id].add(p_id)
        
        # Reset cache and batch load
        self._parent_cache = {}
        for d_id, p_ids in docs_to_parents.items():
            self._parent_cache[d_id] = self.file_store.load_parent_chunks(d_id, parent_ids=list(p_ids))

        final_context = []
        seen_parent_ids = set()
        
        for res in reranked_results:
            metadata = ChunkMetadata(**res["metadata"])
            parent_id = metadata.parent_id
            doc_id = metadata.doc_id
            
            if parent_id in seen_parent_ids:
                continue
                
            # Fetch from pre-loaded cache
            parent_text = ""
            doc_cache = self._parent_cache.get(doc_id, {})
            if parent_id in doc_cache:
                parent_text = doc_cache[parent_id].text
            
            if parent_text:
                final_context.append(RetrievedContext(
                    child_chunk_id=res["chunk_id"],
                    parent_text=parent_text,
                    metadata=metadata,
                    rerank_score=res.get("rerank_score", 0.0)
                ))
                seen_parent_ids.add(parent_id)
                
        return final_context

    def _get_parent_text(self, doc_id: str, parent_id: str) -> str:
        """
        Loads parent chunks for a document and finds the specific text.
        Uses a local cache for the duration of the query.
        """
        if doc_id not in self._parent_cache:
            parents = self.file_store.load_parent_chunks(doc_id)
            self._parent_cache[doc_id] = parents
            
        parent_map = self._parent_cache[doc_id]
        if parent_id in parent_map:
            return parent_map[parent_id].text
            
        return ""
