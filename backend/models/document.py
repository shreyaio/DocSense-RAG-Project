from pydantic import BaseModel
from enum import Enum

class IngestionStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class IngestionJob(BaseModel):
    job_id: str
    doc_id: str
    status: IngestionStatus
    progress: int                    # 0–100
    message: str
    created_at: str
    completed_at: str | None = None

class DocumentRecord(BaseModel):
    doc_id: str
    filename: str
    file_path: str
    page_count: int
    total_chunks: int
    indexed_at: str
    status: IngestionStatus
    embedding_model: str
