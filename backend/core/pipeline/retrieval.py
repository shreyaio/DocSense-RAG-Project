import logging
from typing import List, Optional, Union, Generator
from models.query import QueryRequest, QueryResponse, RetrievalStats, Citation, QueryFilters
from core.retrieve.query_analyser import QueryAnalyser
from core.retrieve.hybrid_search import HybridSearcher
from core.retrieve.reranker import Reranker
from core.retrieve.context_builder import ContextBuilder
from core.generate.prompt_builder import PromptBuilder
from core.generate.llm_client import LLMClient
from storage.base import VectorStore, BM25Store, FileStore
from core.embed.embedder import Embedder
from config.settings import settings
logger = logging.getLogger(__name__)

class RetrievalPipeline:
    """
    Authoritative Orchestrator for retrieval -> generation.
    Enforces the exact sequence and rules defined in Section 9.
    """

    def __init__(self, 
                 vector_store: VectorStore, 
                 bm25_store: BM25Store, 
                 file_store: FileStore):
        # Initialise shared components
        self.embedder = Embedder()
        self.analyser = QueryAnalyser()
        # HybridSearcher must receive file_store to attach text to candidates
        self.searcher = HybridSearcher(vector_store, bm25_store, self.embedder, file_store)
        self.reranker = Reranker()
        self.context_builder = ContextBuilder(file_store)
        self.llm_client = LLMClient()
        self.prompt_builder = PromptBuilder()

    def run(self, request: QueryRequest) -> Union[QueryResponse, Generator[str, None, None]]:
        """
        Main execution flow for a user query.
        Sequence: analyse -> search -> rerank -> build_context -> build_prompt -> call_llm
        """
        logger.info(f"Starting retrieval pipeline for: '{request.question}'")

        # 1. Analyse Query
        # Extract filters (page range, section title, etc.) from the question
        filters = self.analyser.analyse(request.question, request.filters)
        
        # 2. Hybrid Search (Dense + Sparse + RRF)
        # Sequence Rule 2 & 3: Dense and Sparse in parallel logic + RRF fusion occurs inside HybridSearcher
        doc_ids = request.doc_ids or []
        search_output = self.searcher.search(
            question=request.question, 
            doc_ids=doc_ids, 
            filters=filters
        )
        
        # Logic to handle the return format (could be List or Dict depending on stats requirement)
        # We enforce that HybridSearcher returns a dict with 'results' and 'stats'
        if isinstance(search_output, dict):
            candidates = search_output.get("results", [])
            stats_dict = search_output.get("stats", {})
        else:
            candidates = search_output
            stats_dict = {
                "dense_hits": 0, 
                "sparse_hits": 0, 
                "fused_candidates": len(candidates),
                "reranked_from": 0,
                "final_count": 0
            }

        # 3. Guard: No Results
        # Sequence Rule: If zero candidates, immediately return without LLM call
        if not candidates:
            return self._not_found_response(request.question, stats_dict)

        # 4. Reranker
        # Sequence Rule 4: Operates ONLY on fused results from hybrid search
        # Reranker receives candidates with 'text' attached
        reranked_results = self.reranker.rerank(request.question, candidates)
        
        # Update rerank stats
        stats_dict["reranked_from"] = len(candidates)
        stats_dict["final_count"] = len(reranked_results)

        # 5. Context Builder
        # Sequence Rule 5: Fetch parents via FileStore ONLY, deduplicate
        contexts = self.context_builder.build(reranked_results)
        
        # Guard: Check if context building yielded anything usage-ready
        if not contexts:
            return self._not_found_response(request.question, stats_dict)

        # 6. Prompt Builder
        # Sequence Rule 6: Compiles messages from contexts and system prompt
        messages = self.prompt_builder.build_messages(request.question, contexts)

        # 7. LLM Client
        # Sequence Rule 7: Handle streaming vs sync based on configuration
        stream_mode = settings.llm.stream
        
        if stream_mode:
            logger.info("Streaming response initiated.")
            
            # Streaming Metadata Fix 6: Yield metadata chunk first to preserve citations/stats
            def stream_wrapper():
                metadata_chunk = self._assemble_response(
                    question=request.question,
                    answer="", # Answer is streamed
                    contexts=contexts,
                    stats_dict=stats_dict
                )
                yield metadata_chunk.model_dump_json() + "\n"
                
                # Note: Prefix with newline to separate from metadata in simpler frontend consumers
                for chunk in self.llm_client.generate(messages, stream=True):
                    yield str(chunk)
                    
            return stream_wrapper()
        else:
            answer = self.llm_client.generate(messages, stream=False)
            
            # 8. Assemble QueryResponse
            return self._assemble_response(
                question=request.question,
                answer=str(answer),
                contexts=contexts,
                stats_dict=stats_dict
            )

    def _not_found_response(self, question: str, stats_dict: dict) -> QueryResponse:
        """Returns a QueryResponse indicating no information was found."""
        return QueryResponse(
            question=question,
            answer="not found in document",
            citations=[],
            model_used=settings.llm.model,
            retrieval_stats=RetrievalStats(
                dense_hits=stats_dict.get("dense_hits", 0),
                sparse_hits=stats_dict.get("sparse_hits", 0),
                fused_candidates=stats_dict.get("fused_candidates", 0),
                reranked_from=stats_dict.get("reranked_from", 0),
                final_count=0
            )
        )

    def _assemble_response(self, 
                           question: str, 
                           answer: str, 
                           contexts: list, 
                           stats_dict: dict) -> QueryResponse:
        """Assembles the final QueryResponse with citations and stats."""
        citations = []
        for ctx in contexts:
            citations.append(Citation(
                doc_id=ctx.metadata.doc_id,
                source_file=ctx.metadata.source_file,
                page_number=ctx.metadata.page_number,
                page_range=ctx.metadata.page_range,
                section_path=ctx.metadata.section_path,
                chunk_text_preview=ctx.parent_text[:200],
                relevance_score=ctx.rerank_score
            ))

        return QueryResponse(
            question=question,
            answer=answer,
            citations=citations,
            model_used=settings.llm.model,
            retrieval_stats=RetrievalStats(
                dense_hits=stats_dict.get("dense_hits", 0),
                sparse_hits=stats_dict.get("sparse_hits", 0),
                fused_candidates=stats_dict.get("fused_candidates", 0),
                reranked_from=stats_dict.get("reranked_from", 0),
                final_count=len(contexts)
            )
        )
