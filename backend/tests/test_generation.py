import os
import sys
import json
from unittest.mock import MagicMock, patch

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.generate.prompt_builder import PromptBuilder
from core.generate.llm_client import LLMClient
from models.query import RetrievedContext
from models.chunk import ChunkMetadata

def test_prompt_builder():
    print("Testing PromptBuilder...")
    
    # Create dummy context
    metadata = ChunkMetadata(
        chunk_id="c1",
        parent_id="p1",
        prev_chunk_id=None,
        next_chunk_id="c2",
        doc_id="d1",
        source_file="test.pdf",
        page_number=1,
        page_range=[1, 1],
        char_start=0,
        char_end=100,
        section_title="Intro",
        subsection_title=None,
        heading_level=1,
        section_path="Intro",
        block_type="text",
        token_count=20,
        chunk_index=0,
        total_chunks=10,
        is_near_heading=True,
        chunk_level="child",
        embedding_model="bge",
        created_at="2024-01-01T00:00:00Z"
    )
    
    ctx = RetrievedContext(
        child_chunk_id="c1",
        parent_text="This is the parent text for context.",
        metadata=metadata,
        rerank_score=0.95
    )
    
    question = "What is this about?"
    messages = PromptBuilder.build_messages(question, [ctx])
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "document-grounded assistant" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "test.pdf" in messages[1]["content"]
    assert "Page 1" in messages[1]["content"]
    assert "Intro" in messages[1]["content"]
    assert "This is the parent text for context." in messages[1]["content"]
    assert question in messages[1]["content"]
    
    print("PromptBuilder tests PASSED")

def test_llm_client_sync():
    print("Testing LLMClient sync call (MOCKED)...")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a mocked response."}}
            ]
        }
        mock_client.post.return_value = mock_response
        
        client = LLMClient()
        response = client.generate([{"role": "user", "content": "hello"}], stream=False)
        
        assert response == "This is a mocked response."
        assert mock_client.post.called
    
    print("LLMClient sync tests PASSED")

def test_llm_client_streaming():
    print("Testing LLMClient streaming (MOCKED)...")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Setup mock stream response
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            'data: [DONE]'
        ]
        mock_client.stream.return_value.__enter__.return_value = mock_response
        
        client = LLMClient()
        gen = client.generate([{"role": "user", "content": "hello"}], stream=True)
        
        tokens = list(gen)
        assert "".join(tokens) == "Hello world"
        assert mock_client.stream.called
    
    print("LLMClient streaming tests PASSED")

if __name__ == "__main__":
    test_prompt_builder()
    test_llm_client_sync()
    test_llm_client_streaming()
    print("\nAll Generation Component Unit Tests PASSED (Logic only)")
