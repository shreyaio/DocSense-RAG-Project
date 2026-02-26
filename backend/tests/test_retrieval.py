import os
import sys
from unittest.mock import MagicMock

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.retrieve.query_analyser import QueryAnalyser
from core.retrieve.hybrid_search import HybridSearcher
from core.retrieve.reranker import Reranker
from core.retrieve.context_builder import ContextBuilder
from models.query import QueryFilters
from models.chunk import ChildChunk, ChunkMetadata, ParentChunk

def test_query_analyser():
    print("Testing QueryAnalyser...")
    analyser = QueryAnalyser()
    
    # Test page detection
    q1 = "What is mentioned on page 42?"
    f1 = analyser.analyse(q1)
    assert f1.page_range == [42, 42]
    
    # Test range detection
    q2 = "Summarize pages 10 to 15."
    f2 = analyser.analyse(q2)
    assert f2.page_range == [10, 15]
    
    # Test table detection
    q3 = "Show me the table on growth rates."
    f3 = analyser.analyse(q3)
    assert f3.block_type == "table"
    
    print("QueryAnalyser tests PASSED")

def test_hybrid_search_logic():
    print("Testing HybridSearcher logic (MOCKED)...")
    
    # Mock dependencies
    v_store = MagicMock()
    b_store = MagicMock()
    embedder = MagicMock()
    
    # Setup mock returns
    embedder.embed_query.return_value = [0.1] * 1024
    v_store.search.return_value = [
        {"chunk_id": "c1", "payload": {"doc_id": "d1", "parent_id": "p1", "text": "text1", "page_number": 1, "page_range": [1,1], "char_start": 0, "char_end": 10, "block_type": "text", "token_count": 5, "chunk_index": 0, "total_chunks": 1, "is_near_heading": False, "chunk_level": "child", "embedding_model": "bge", "created_at": "now", "section_path": "Intro"}}
    ]
    b_store.search.return_value = [("c2", 15.5)] # ID, score
    
    searcher = HybridSearcher(v_store, b_store, embedder)
    results = searcher.search("test query", ["d1"], QueryFilters())
    
    # Verify both arms were called
    assert embedder.embed_query.called
    assert v_store.search.called
    assert b_store.search.called
    
    print("HybridSearcher logic tests PASSED")

def test_context_builder():
    print("Testing ContextBuilder...")
    
    f_store = MagicMock()
    # Mock parent chunk
    p1 = ParentChunk(parent_id="p1", doc_id="d1", text="This is the full parent text.", page_range=[1,1], child_ids=["c1"])
    f_store.load_parent_chunks.return_value = {"p1": p1}
    
    builder = ContextBuilder(f_store)
    
    # Dummy results (duplicated parents)
    results = [
        {"chunk_id": "c1", "payload": {"doc_id": "d1", "parent_id": "p1", "text": "child1", "page_number": 1, "page_range": [1,1], "char_start": 0, "char_end": 10, "block_type": "text", "token_count": 5, "chunk_index": 0, "total_chunks": 2, "is_near_heading": False, "chunk_level": "child", "embedding_model": "bge", "created_at": "now", "section_path": "Intro"}},
        {"chunk_id": "c2", "payload": {"doc_id": "d1", "parent_id": "p1", "text": "child2", "page_number": 1, "page_range": [1,1], "char_start": 11, "char_end": 20, "block_type": "text", "token_count": 5, "chunk_index": 1, "total_chunks": 2, "is_near_heading": False, "chunk_level": "child", "embedding_model": "bge", "created_at": "now", "section_path": "Intro"}}
    ]
    
    context = builder.build(results)
    
    # Should deduplicate to 1 context item (shared parent)
    assert len(context) == 1
    assert context[0].parent_text == "This is the full parent text."
    
    print("ContextBuilder tests PASSED")

if __name__ == "__main__":
    test_query_analyser()
    test_hybrid_search_logic()
    test_context_builder()
    print("\nAll Retrieval Component Unit Tests PASSED (Logic only)")
