import os
import sys
import numpy as np

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.embed.embedder import Embedder
from models.chunk import ChildChunk, ChunkMetadata

def test_embedding_flow():
    print("--- Testing Embedding Flow ---")
    
    # 1. Create dummy chunks
    dummy_metadata = {
        "chunk_id": "test_1",
        "parent_id": "p_1",
        "doc_id": "doc_1",
        "source_file": "test.pdf",
        "page_number": 1,
        "page_range": [1, 1],
        "char_start": 0,
        "char_end": 10,
        "block_type": "text",
        "token_count": 5,
        "chunk_index": 0,
        "total_chunks": 1,
        "is_near_heading": False,
        "chunk_level": "child",
        "embedding_model": "BAAI/bge-large-en-v1.5",
        "created_at": "now"
    }
    
    chunks = [
        ChildChunk(text="Artificial Intelligence is transforming the world.", metadata=ChunkMetadata(**dummy_metadata)),
        ChildChunk(text="RAG systems combine retrieval with generation.", metadata=ChunkMetadata(**dummy_metadata))
    ]
    
    # 2. Initialize Embedder
    try:
        # Note: This will download the model (~1.3GB) if not cached.
        # However, the user is installing dependencies first.
        embedder = Embedder()
        
        print(f"Embedding {len(chunks)} chunks...")
        enriched_chunks = embedder.embed_chunks(chunks)
        
        # 3. Verify
        for i, chunk in enumerate(enriched_chunks):
            emb = chunk.embedding
            print(f"Chunk {i} embedding size: {len(emb)}")
            # Verify L2 normalization: sum of squares should be ~1
            norm = np.linalg.norm(emb)
            print(f"Chunk {i} vector norm: {norm:.4f}")
            
        print("\nTesting query embedding...")
        query_emb = embedder.embed_query("What is AI?")
        print(f"Query embedding size: {len(query_emb)}")
        print(f"Query vector norm: {np.linalg.norm(query_emb):.4f}")
        
    except ImportError as e:
        print(f"Required libraries (sentence-transformers, torch) not found: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_embedding_flow()
