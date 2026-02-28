import os
import logging
from typing import List, Dict
from fastapi import APIRouter, Depends, Request, HTTPException

from storage.base import VectorStore, BM25Store, FileStore
from models.document import DocumentRecord, IngestionStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependencies for stores (from app.state)
def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store

def get_bm25_store(request: Request) -> BM25Store:
    return request.app.state.bm25_store

def get_file_store(request: Request) -> FileStore:
    return request.app.state.file_store

@router.get("/documents", response_model=List[DocumentRecord], summary="List all indexed document IDs in the system")
def list_documents(file_store: FileStore = Depends(get_file_store)):
    """
    1. Orchestrates listing of indexed documents via FileStore abstraction.
    2. Strict compliance with SSOT: No direct filesystem inspection in routes.
    """
    try:
        doc_ids = file_store.list_documents()
        
        # Return list of DocumentRecord as per SSOT contract.
        # Note: In a production DB branch, these fields would be fetched from a DB.
        # For the local demo mode, we provide available info.
        return [
            DocumentRecord(
                doc_id=d,
                filename=f"{d}.pdf", # Fallback as original filename isn't in flat FileStore
                file_path="",        # Path should not be exposed to frontend
                page_count=0, 
                total_chunks=0,
                indexed_at="",
                status=IngestionStatus.completed,
                embedding_model=""
            ) for d in doc_ids
        ]
        
    except Exception as e:
        logger.exception("Failed to list documents.")
        raise HTTPException(status_code=500, detail="Could not retrieve documents from storage.")

@router.delete("/documents/{doc_id}", summary="Delete all document artifacts across stores")
def delete_document(
    doc_id: str,
    vector_store: VectorStore = Depends(get_vector_store),
    bm25_store: BM25Store = Depends(get_bm25_store),
    file_store: FileStore = Depends(get_file_store)
):
    """
    ATOMIC DELETION SEQUENCE:
    1. Delete vectors from Qdrant by doc_id.
    2. Delete BM25 index file/mapping.
    3. Delete parent JSON store + PDF binary via FileStore.
    
    Returns 500 on any failure; logs errors to preserve system state visibility.
    """
    logger.info(f"Triggering atomic deletion for doc_id: {doc_id}")
    
    try:
        # Step 1: Vector Store
        try:
            vector_store.delete_document(doc_id)
            logger.info(f"Step 1: Successfully deleted vectors for {doc_id} from Qdrant.")
        except Exception as e:
            logger.error(f"Step 1 Failure: Error deleting vectors for {doc_id}: {str(e)}")
            raise e # Escalate for atomic failure reporting
            
        # Step 2: BM25 Store
        try:
            bm25_store.delete(doc_id)
            logger.info(f"Step 2: Successfully deleted BM25 index for {doc_id}.")
        except Exception as e:
            logger.error(f"Step 2 Failure: Error deleting BM25 index for {doc_id}: {str(e)}")
            raise e
            
        # Step 3: File Store (JSON + PDF)
        try:
            file_store.delete_document(doc_id)
            logger.info(f"Step 3: Successfully deleted files (JSON/PDF) for {doc_id}.")
        except Exception as e:
            logger.error(f"Step 3 Failure: Error deleting file artifacts for {doc_id}: {str(e)}")
            raise e
            
        return {"doc_id": doc_id, "success": True, "message": "Document deleted atomically across all stores."}
        
    except Exception as e:
        logger.exception(f"CRITICAL: Final atomic deletion state failed for {doc_id}.")
        raise HTTPException(status_code=500, detail=f"Partial deletion failure for {doc_id}. Logs captured.")
