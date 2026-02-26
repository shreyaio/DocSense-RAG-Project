from typing import List, Dict, Any
from storage.base import FileStore
from models.query import RetrievedContext
from models.chunk import ChunkMetadata

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
        # Fix 4: Reset cache per request — prevents memory growth and stale data.
        self._parent_cache = {}
        final_context = []
        seen_parent_ids = set()
        
        for res in reranked_results:
            payload = res["payload"]
            # 'text' was added to the Qdrant payload for the reranker (Fix 5).
            # Strip it before constructing ChunkMetadata, which doesn't have a 'text' field.
            metadata_dict = {k: v for k, v in payload.items() if k != "text"}
            metadata = ChunkMetadata(**metadata_dict)
            
            parent_id = metadata.parent_id
            doc_id = metadata.doc_id
            
            # Avoid redundant context if multiple children point to same parent
            if parent_id in seen_parent_ids:
                continue
                
            # Fetch parent text
            parent_text = self._get_parent_text(doc_id, parent_id)
            
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
