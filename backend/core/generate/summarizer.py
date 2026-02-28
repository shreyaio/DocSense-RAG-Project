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

    def summarize(self, request_data: SummarizeRequest) -> SummarizeResponse:
        """
        1. Loads parent chunks for context.
        2. Respects token/chunk limits from config.
        3. Builds grounded summarization prompt.
        4. Calls LLM Client for synchronous result.
        """
        doc_id = request_data.doc_id
        mode = request_data.mode
        
        logger.info(f"Summarizing doc_id={doc_id} in mode={mode}")
        
        # 1. Load Parent Chunks (memory explosion risk note: loads full doc for global context)
        # Using the base signature without filters as we need global order
        parents_map = self.file_store.load_parent_chunks(doc_id)
        if not parents_map:
            raise FileNotFoundError(f"Document {doc_id} not found or empty.")
            
        # 2. Select first N chunks based on config
        max_chunks = getattr(settings, "summarization", {}).get("max_chunks", 10)
        
        # In current LocalFileStore, iteration order matches insertion order (doc order)
        parent_list = list(parents_map.values())[:max_chunks]
        context_text = "\n\n".join([p.text for p in parent_list])
        
        # 3. Build Prompt via PromptBuilder
        messages = PromptBuilder.build_summarization_prompt(context_text, mode)
        
        # 4. Generate Output (Sync def for core processing)
        # Forcing stream=False as per summarization requirements
        output = self.llm.generate(messages, stream=False)
        
        return SummarizeResponse(
            doc_id=doc_id,
            mode=mode,
            output=str(output),
            model_used=settings.llm.model,
            chunk_count_used=len(parent_list)
        )
