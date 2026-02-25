from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from backend.models.chunk import ChildChunk
from backend.storage.base import VectorStore
from backend.config.settings import settings
import os

class QdrantLocalStore(VectorStore):
    """
    Implements VectorStore using Qdrant in local storage mode.
    """

    def __init__(self):
        self.config = settings.qdrant
        self.client = QdrantClient(path=self.config.local_path)
        self._ensure_collection()

    def _ensure_collection(self):
        if not self.collection_exists():
            print(f"Creating Qdrant collection: {self.config.collection_name}")
            self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=rest.VectorParams(
                    size=settings.embedding.vector_dim,
                    distance=rest.Distance.COSINE
                ),
                hnsw_config=rest.HnswConfigDiff(
                    m=self.config.hnsw_m,
                    ef_construct=self.config.hnsw_ef_construct
                )
            )
            # Create payload indexes for faster filtering
            for field in ["page_number", "section_title", "block_type", "doc_id"]:
                self.client.create_payload_index(
                    collection_name=self.config.collection_name,
                    field_name=field,
                    field_schema=rest.PayloadSchemaType.KEYWORD if field != "page_number" else rest.PayloadSchemaType.INTEGER
                )

    def collection_exists(self) -> bool:
        collections = self.client.get_collections().collections
        return any(c.name == self.config.collection_name for c in collections)

    def upsert(self, chunks: List[ChildChunk]) -> None:
        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue
                
            points.append(rest.PointStruct(
                id=chunk.metadata.chunk_id,
                vector=chunk.embedding,
                payload=chunk.metadata.model_dump()
            ))
            
        if points:
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=points
            )

    def search(self, vector: List[float], top_k: int, filters: Optional[Dict] = None) -> List[Dict]:
        query_filter = None
        if filters:
            must_clauses = []
            for key, value in filters.items():
                if value is not None:
                    must_clauses.append(rest.FieldCondition(
                        key=key,
                        match=rest.MatchValue(value=value)
                    ))
            if must_clauses:
                query_filter = rest.Filter(must=must_clauses)

        results = self.client.search(
            collection_name=self.config.collection_name,
            query_vector=vector,
            limit=top_k,
            query_filter=query_filter,
            search_params=rest.SearchParams(hnsw_ef=self.config.hnsw_ef)
        )
        
        return [
            {
                "chunk_id": r.id,
                "score": r.score,
                "payload": r.payload
            } 
            for r in results
        ]

    def delete_document(self, doc_id: str) -> None:
        self.client.delete(
            collection_name=self.config.collection_name,
            points_selector=rest.FilterSelector(
                filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="doc_id",
                            match=rest.MatchValue(value=doc_id)
                        )
                    ]
                )
            )
        )
