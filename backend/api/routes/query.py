import logging
import json
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

@router.get("/debug-stream", summary="Debug streaming endpoint - Simple text stream test")
def debug_stream():
    """
    Minimal test endpoint for streaming without LLM/retrieval logic.
    Returns: SSE stream with proper {"token": "..."} and {"response": {...}} format.
    Used to verify frontend streaming works correctly.
    """
    logger.info("Debug stream endpoint called")
    
    def test_generator():
        logger.debug("Starting debug stream generator")
        test_chunks = ["hello ", "from ", "RAG ", "App ", "streaming!"]
        for chunk in test_chunks:
            logger.debug(f"Debug chunk: {repr(chunk)}")
            yield chunk
        logger.debug("Debug stream generator complete")
    
    def sse_wrapper(generator):
        chunk_count = 0
        for chunk in generator:
            chunk_count += 1
            chunk_str = str(chunk)
            logger.debug(f"Debug SSE chunk {chunk_count}: {repr(chunk_str)}")
            yield f"data: {json.dumps({'token': chunk_str})}\n\n"
        
        # Send a minimal final response
        final_payload = {"response": {"question": "debug", "answer": "test complete", "citations": [], "model_used": "debug", "retrieval_stats": None}}
        logger.debug(f"Debug SSE stream completed: {chunk_count} chunks, sending final response")
        yield f"data: {json.dumps(final_payload)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        sse_wrapper(test_generator()),
        media_type="text/event-stream"
    )

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
            logger.debug("Streaming mode: wrapping generator with SSE formatting")

            def sse_wrapper(generator):
                for chunk in generator:
                    chunk_str = str(chunk)

                    # Try to detect if this is full QueryResponse JSON
                    try:
                        parsed = json.loads(chunk_str)
                        if isinstance(parsed, dict) and "answer" in parsed:
                            # This is the final assembled QueryResponse
                            logger.debug(f"SSE: Detected final response, wrapping as 'response'")
                            yield f"data: {json.dumps({'response': parsed})}\n\n"
                            continue
                    except Exception:
                        pass

                    # Otherwise treat as streaming token
                    logger.debug(f"SSE: Wrapping as token: {repr(chunk_str[:30])}")
                    yield f"data: {json.dumps({'token': chunk_str})}\n\n"

                logger.debug("SSE: Sending [DONE]")
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                sse_wrapper(result),
                media_type="text/event-stream"
            )
        
        # Non-streaming mode returns a plain QueryResponse model
        logger.debug("Non-streaming mode: returning QueryResponse directly")
        return result
        
    except Exception as e:
        logger.exception("Query pipeline execution failed.")
        raise HTTPException(status_code=500, detail=str(e))
