import logging
from typing import Optional
from storage.base import FileStore
from core.generate.llm_client import LLMClient
from core.generate.prompt_builder import PromptBuilder
from models.query import SummarizeRequest, SummarizeResponse
from config.settings import settings

logger = logging.getLogger(__name__)

class Summarizer:
    """
    On-demand document summarization service.
    Follows SSOT separation of concerns: core logic only (No FastAPI).
    """
    
    def __init__(self, file_store: FileStore, llm: LLMClient):
        self.file_store = file_store
        self.llm = llm
        self.cache = {} # In-memory cache for demo safety
        self.last_request_time = 0.0

    def summarize(self, request_data: SummarizeRequest) -> SummarizeResponse:
        """
        1. Checks cache for existing results.
        2. Throttles rapid repeat requests.
        3. Loads parent chunks for context.
        """
        import time
        doc_id = request_data.doc_id
        mode = request_data.mode
        
        # 0. Check Cache (SSOT Rule: Don't recompute expensive operations)
        cache_key = f"{doc_id}_{mode}"
        if cache_key in self.cache:
            logger.info(f"Returning cached summary for {doc_id} [{mode}]")
            return self.cache[cache_key]

        # 0.1 Simple Throttle
        now = time.time()
        if now - self.last_request_time < 2.0:
            logger.warning(f"Summarization throttled for {doc_id}. Waiting 2s...")
            time.sleep(2.0)
        self.last_request_time = time.time()
        
        logger.info(f"Summarizing doc_id={doc_id} in mode={mode}")
        
        # 1. Load Parent Chunks (memory explosion risk note: loads full doc for global context)
        # Using the base signature without filters as we need global order
        parents_map = self.file_store.load_parent_chunks(doc_id)
        if not parents_map:
            raise FileNotFoundError(f"Document {doc_id} not found or empty.")
            
        # 2. Select first N chunks based on config
        max_chunks = settings.summarization.max_chunks
        
        # In current LocalFileStore, iteration order matches insertion order (doc order)
        parent_list = list(parents_map.values())[:max_chunks]
        context_text = "\n\n".join([p.text for p in parent_list])
        
        # 3. Build Prompt via PromptBuilder
        messages = PromptBuilder.build_summarization_prompt(context_text, mode)
        
        # 4. Generate Output (Sync def for core processing)
        # Forcing stream=False as per summarization requirements
        try:
            output = self.llm.generate(messages, stream=False)
        except Exception as e:
            logger.error(f"Summarization LLM call failed: {e}")
            return SummarizeResponse(
                doc_id=doc_id,
                mode=mode,
                status="busy",
                message="System is busy. Please try again shortly."
            )
        
        res = SummarizeResponse(
            doc_id=doc_id,
            mode=mode,
            output=str(output),
            model_used=settings.llm.model,
            chunk_count_used=len(parent_list),
            status="success"
        )
        self.cache[cache_key] = res
        return res
