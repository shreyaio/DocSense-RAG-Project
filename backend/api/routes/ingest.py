import hashlib
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, BackgroundTasks

from core.pipeline.ingestion import IngestionPipeline
from models.document import IngestionJob, IngestionStatus
from storage.base import FileStore

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependencies to get components from app state
def get_ingestion_pipeline(request: Request) -> IngestionPipeline:
    return request.app.state.ingestion_pipeline

def get_file_store(request: Request) -> FileStore:
    return request.app.state.file_store

@router.post("/ingest", response_model=IngestionJob, summary="Upload a PDF and ingest it into the RAG system")
async def ingest_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    file_store: FileStore = Depends(get_file_store)
):
    """
    1. Reads file bytes and generates deterministic doc_id (SHA-256).
    2. Saves file via FileStore.save_pdf() (Strict SSOT compliance).
    3. Dispatches ingestion pipeline to BackgroundTasks (Immediate response).
    4. Returns IngestionJob.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        # Read file bytes for hashing
        file_bytes = await file.read()
        
        # Deterministic doc_id for deduplication tracking (SHA-256 slice as per SSOT logic)
        doc_id = hashlib.sha256(file_bytes).hexdigest()[:16]
        job_id = str(uuid.uuid4())
        
        logger.info(f"Uploading file '{file.filename}' with generated doc_id: {doc_id}, job_id: {job_id}")
        
        # Save bytes via FileStore - Ensures zero disk leak from local temp files
        saved_path = file_store.save_pdf(doc_id, file_bytes)
        
        # In-memory job store update (SSOT Rule 631)
        # We fetch jobs_db from app state via request.app
        jobs_db = request.app.state.jobs_db
        
        # Create IngestionJob record
        job = IngestionJob(
            job_id=job_id,
            doc_id=doc_id,
            status=IngestionStatus.pending,
            progress=0,
            message="Queued for processing",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        jobs_db[job_id] = job
        
        # Callback to update the in-memory job state from the background pipeline
        def progress_callback(progress: int, message: str):
            target_job = jobs_db.get(job_id)
            if not target_job:
                return
            
            target_job.progress = progress
            target_job.message = message
            
            if progress == 100:
                target_job.status = IngestionStatus.completed
                target_job.completed_at = datetime.now(timezone.utc).isoformat()
            elif progress < 0: # Convention handled in route wrapper if needed
                target_job.status = IngestionStatus.failed
            else:
                target_job.status = IngestionStatus.processing
        
        # Wrapped pipeline run to catch errors and update job status
        def run_pipeline_with_cleanup():
            try:
                pipeline.run(
                    file_path=saved_path,
                    doc_id=doc_id,
                    source_file=file.filename,
                    progress_callback=progress_callback
                )
            except Exception as e:
                logger.error(f"Background ingestion failed for {doc_id}: {e}")
                progress_callback(-1, f"Error: {str(e)}")

        # Dispatch to BackgroundTasks - Never block the HTTP response (SSOT Rule 630)
        background_tasks.add_task(run_pipeline_with_cleanup)
        
        return job
    
    except Exception as e:
        logger.exception(f"Ingestion initiation failed for {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await file.close()

@router.get("/ingest/status/{job_id}", response_model=IngestionJob, summary="Get the status of a document ingestion job")
def get_ingest_status(job_id: str, request: Request):
    """
    Returns the current status of an ingestion job from the in-memory store.
    SSOT Rule 353 compliant.
    """
    jobs_db = request.app.state.jobs_db
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return jobs_db[job_id]
