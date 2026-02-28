import logging
from fastapi import APIRouter, Depends, Request, HTTPException

from core.generate.summarizer import Summarizer
from models.query import SummarizeRequest, SummarizeResponse
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get Summarizer from app state
def get_summarizer(request: Request) -> Summarizer:
    return request.app.state.summarizer

@router.post("/summarize", response_model=SummarizeResponse, summary="Generate a summary or key points for a document")
def summarize_document(
    request_data: SummarizeRequest,
    summarizer: Summarizer = Depends(get_summarizer)
):
    """
    On-demand document summarization (SSOT compliant):
    1. Delegated purely to core/generate/summarizer.py.
    2. Zero business logic inside the route.
    """
    try:
        return summarizer.summarize(request_data)
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Summarization service failed.")
        raise HTTPException(status_code=500, detail="Internal processing error during summarization.")
