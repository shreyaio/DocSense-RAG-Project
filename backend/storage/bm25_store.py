import os
import pickle
import json
from typing import List, Tuple, Dict
from rank_bm25 import BM25Okapi
from backend.models.chunk import ChildChunk
from backend.storage.base import BM25Store

class LocalBM25Store(BM25Store):
    """
    Implements BM25Store using rank-bm25 and local pickle files.
    Index is built per document to allow efficient targeted searching.
    """

    def __init__(self, base_path: str = "./data/bm25_indexes"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def build(self, doc_id: str, chunks: List[ChildChunk]) -> None:
        # 1. Tokenize corpus (simple whitespace and lowercase for now)
        # In a more advanced version, we might use a proper stemmer
        corpus = [c.text.lower().split() for c in chunks]
        bm25 = BM25Okapi(corpus)
        
        # 2. Map corpus index to chunk_id
        mapping = {i: c.metadata.chunk_id for i, c in enumerate(chunks)}
        
        # 3. Save index and mapping
        pkl_path = os.path.join(self.base_path, f"{doc_id}.pkl")
        map_path = os.path.join(self.base_path, f"{doc_id}_map.json")
        
        with open(pkl_path, "wb") as f:
            pickle.dump(bm25, f)
            
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

    def search(self, doc_id: str, query: str, top_k: int) -> List[Tuple[str, float]]:
        pkl_path = os.path.join(self.base_path, f"{doc_id}.pkl")
        map_path = os.path.join(self.base_path, f"{doc_id}_map.json")
        
        if not os.path.exists(pkl_path) or not os.path.exists(map_path):
            return []
            
        with open(pkl_path, "rb") as f:
            bm25 = pickle.load(f)
            
        with open(map_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
            
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0: # Only return actual matches
                results.append((mapping[str(idx)], float(scores[idx])))
                
        return results

    def delete(self, doc_id: str) -> None:
        for suffix in [".pkl", "_map.json"]:
            path = os.path.join(self.base_path, f"{doc_id}{suffix}")
            if os.path.exists(path):
                os.remove(path)
