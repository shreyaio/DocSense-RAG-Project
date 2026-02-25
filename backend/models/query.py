from pydantic import BaseModel
from models.chunk import ChunkMetadata

class QueryFilters(BaseModel):
    page_range: list[int] | None = None     # [start_page, end_page]
    section_title: str | None = None
    block_type: str | None = None

class QueryRequest(BaseModel):
    question: str
    doc_ids: list[str] | None = None        # None = search all documents
    top_k: int = 5
    filters: QueryFilters | None = None

class Citation(BaseModel):
    doc_id: str
    source_file: str
    page_number: int
    page_range: list[int]
    section_path: str | None = None
    chunk_text_preview: str          # first 200 chars of parent chunk
    relevance_score: float

class RetrievedContext(BaseModel):
    child_chunk_id: str
    parent_text: str
    metadata: ChunkMetadata
    rerank_score: float

class RetrievalStats(BaseModel):
    dense_hits: int
    sparse_hits: int
    fused_candidates: int
    reranked_from: int
    final_count: int

class QueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    model_used: str
    retrieval_stats: RetrievalStats
