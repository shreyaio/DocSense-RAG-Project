import logging
from typing import Union, Generator
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse

from models.query import QueryRequest, QueryResponse
from core.pipeline.retrieval import RetrievalPipeline

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get RetrievalPipeline from app state
def get_retrieval_pipeline(request: Request) -> RetrievalPipeline:
    return request.app.state.retrieval_pipeline

@router.post("/query", summary="Query the RAG system using a question and document ID")
def query_system(
    request_data: QueryRequest,
    pipeline: RetrievalPipeline = Depends(get_retrieval_pipeline)
):
    """
    1. Orchestrates retrieval and generation via RetrievalPipeline.
    2. Synchronous def for CPU processing.
    3. Supports streaming results based on config settings.
    """
    try:
        logger.info(f"Querying system for: '{request_data.question}' on docs: {request_data.doc_ids}")
        
        # Execute the pipeline
        # Note: If streaming is enabled in config.yaml, it returns a generator.
        result = pipeline.run(request_data)
        
        # Check if result is a generator (streaming mode)
        if isinstance(result, Generator):
            # Wrap the generator as SSE stream logic
            # Simplest for now: raw string chunks. Frontend handles SSE convention.
            return StreamingResponse(
                result, 
                media_type="text/event-stream"
            )
        
        # Non-streaming mode returns a plain QueryResponse model
        return result
        
    except Exception as e:
        logger.exception("Query pipeline execution failed.")
        raise HTTPException(status_code=500, detail=str(e))
