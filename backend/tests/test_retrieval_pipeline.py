import os
import sys
from unittest.mock import MagicMock, patch

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.pipeline.retrieval import RetrievalPipeline
from models.query import QueryRequest, QueryFilters
from models.chunk import ChunkMetadata

def test_retrieval_pipeline_full_flow():
    print("Testing RetrievalPipeline full flow (MOCKED)...")
    
    # Mock stores
    v_store = MagicMock()
    b_store = MagicMock()
    f_store = MagicMock()
    
    # Patch components inside the retrieval module
    with patch("core.pipeline.retrieval.QueryAnalyser") as mock_analyser_cls, \
         patch("core.pipeline.retrieval.HybridSearcher") as mock_searcher_cls, \
         patch("core.pipeline.retrieval.Reranker") as mock_reranker_cls, \
         patch("core.pipeline.retrieval.ContextBuilder") as mock_builder_cls, \
         patch("core.pipeline.retrieval.PromptBuilder") as mock_prompt_cls, \
         patch("core.pipeline.retrieval.LLMClient") as mock_llm_cls:
        
        # Setup mocks
        mock_analyser = mock_analyser_cls.return_value
        mock_searcher = mock_searcher_cls.return_value
        mock_reranker = mock_reranker_cls.return_value
        mock_builder = mock_builder_cls.return_value
        mock_prompt = mock_prompt_cls.return_value
        mock_llm = mock_llm_cls.return_value
        
        pipeline = RetrievalPipeline(v_store, b_store, f_store)
        
        # 1. Searcher output
        mock_searcher.search.return_value = {
            "results": [{"chunk_id": "c1", "metadata": {"doc_id": "d1", "parent_id": "p1"}, "text": "child text"}],
            "stats": {"dense_hits": 5, "sparse_hits": 5, "fused_candidates": 10}
        }
        
        # 2. Reranker output
        mock_reranker.rerank.return_value = [{"chunk_id": "c1", "metadata": {"doc_id": "d1", "parent_id": "p1"}, "text": "child text", "rerank_score": 0.9}]
        
        # 3. Context Builder output
        dummy_meta = MagicMock(spec=ChunkMetadata)
        dummy_meta.doc_id = "d1"
        dummy_meta.source_file = "test.pdf"
        dummy_meta.page_number = 1
        dummy_meta.page_range = [1, 1]
        dummy_meta.section_path = "Intro"
        
        mock_ctx = MagicMock()
        mock_ctx.metadata = dummy_meta
        mock_ctx.parent_text = "Full parent text here."
        mock_ctx.rerank_score = 0.9
        mock_builder.build.return_value = [mock_ctx]
        
        # 4. LLM output (sync)
        from config.settings import settings
        settings.llm.stream = False
        mock_llm.generate.return_value = "The answer is 42."
        
        # Run pipeline
        req = QueryRequest(question="What is the answer?", doc_ids=["d1"])
        response = pipeline.run(req)
        
        # Assertions
        assert response.answer == "The answer is 42."
        assert len(response.citations) == 1
        assert response.retrieval_stats.dense_hits == 5
        assert response.retrieval_stats.fused_candidates == 10
        assert response.retrieval_stats.reranked_from == 1
        assert response.retrieval_stats.final_count == 1
        
        # Verify sequence and order
        mock_analyser.analyse.assert_called_once()
        mock_searcher.search.assert_called_once()
        mock_reranker.rerank.assert_called_once()
        mock_builder.build.assert_called_once()
        mock_llm.generate.assert_called_once()

    print("RetrievalPipeline full flow tests PASSED")

def test_retrieval_pipeline_no_results():
    print("Testing RetrievalPipeline logic when no results are found...")
    
    v_store = MagicMock()
    b_store = MagicMock()
    f_store = MagicMock()
    
    with patch("core.pipeline.retrieval.HybridSearcher") as mock_searcher_cls, \
         patch("core.pipeline.retrieval.LLMClient") as mock_llm_cls:
        
        pipeline = RetrievalPipeline(v_store, b_store, f_store)
        mock_searcher = mock_searcher_cls.return_value
        mock_llm = mock_llm_cls.return_value
        
        # Search returns empty results
        mock_searcher.search.return_value = {
            "results": [],
            "stats": {"dense_hits": 0, "sparse_hits": 0, "fused_candidates": 0}
        }
        
        req = QueryRequest(question="Invalid query?")
        response = pipeline.run(req)
        
        # Should return "not found" instead of calling LLM
        assert response.answer == "not found in document"
        assert response.retrieval_stats.final_count == 0
        assert not mock_llm.generate.called
        
    print("RetrievalPipeline no-results tests PASSED")

def test_retrieval_pipeline_streaming_path():
    print("Testing RetrievalPipeline streaming path...")
    
    v_store = MagicMock()
    b_store = MagicMock()
    f_store = MagicMock()
    
    with patch("core.pipeline.retrieval.HybridSearcher") as mock_searcher_cls, \
         patch("core.pipeline.retrieval.LLMClient") as mock_llm_cls, \
         patch("core.pipeline.retrieval.ContextBuilder") as mock_builder_cls:
        
        from config.settings import settings
        settings.llm.stream = True
        
        pipeline = RetrievalPipeline(v_store, b_store, f_store)
        mock_searcher = mock_searcher_cls.return_value
        mock_llm = mock_llm_cls.return_value
        mock_builder = mock_builder_cls.return_value
        
        # Setup search output
        mock_searcher.search.return_value = {
            "results": [{"chunk_id": "c1", "metadata": {}, "text": ""}],
            "stats": {}
        }
        mock_builder.build.return_value = [MagicMock()] # dummy context
        
        # Mock generator
        def dummy_gen():
            yield "token1"
            yield "token2"
        mock_llm.generate.return_value = dummy_gen()
        
        req = QueryRequest(question="Stream me")
        response = pipeline.run(req)
        
        # Response should be a generator
        assert hasattr(response, "__iter__")
        tokens = list(response)
        assert tokens == ["token1", "token2"]
        
    print("RetrievalPipeline streaming path tests PASSED")

if __name__ == "__main__":
    test_retrieval_pipeline_full_flow()
    test_retrieval_pipeline_no_results()
    test_retrieval_pipeline_streaming_path()
    print("\nAll Retrieval Pipeline Orchestration Unit Tests PASSED")
