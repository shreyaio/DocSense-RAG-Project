import os
import sys
import numpy as np

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from storage.qdrant_store import QdrantLocalStore
from storage.bm25_store import LocalBM25Store
from storage.file_store import LocalFileStore
from models.chunk import ChildChunk, ChunkMetadata, ParentChunk

def test_storage():
    print("--- Testing Storage Layer ---")
    doc_id = "test_doc_456"
    
    # Setup dummy data
    metadata = ChunkMetadata(
        chunk_id="c1", parent_id="p1", doc_id=doc_id, source_file="test.pdf",
        page_number=1, page_range=[1,1], char_start=0, char_end=10,
        section_path="Intro", block_type="text", token_count=5,
        chunk_index=0, total_chunks=1, is_near_heading=False,
        chunk_level="child", embedding_model="test-model", created_at="now"
    )
    chunks = [ChildChunk(text="Hello world test", metadata=metadata, embedding=[0.1] * 1024)]
    parents = [ParentChunk(parent_id="p1", doc_id=doc_id, text="Hello world parent", page_range=[1,1], section_path="Intro", child_ids=["c1"])]

    # 1. Test Qdrant
    print("Testing Qdrant Store...")
    v_store = QdrantLocalStore()
    v_store.upsert(chunks)
    hits = v_store.search([0.1] * 1024, top_k=5, filters={"doc_id": doc_id})
    print(f"Qdrant hits: {len(hits)}")
    
    # 2. Test BM25
    print("Testing BM25 Store...")
    b_store = LocalBM25Store()
    b_store.build(doc_id, chunks)
    b_results = b_store.search(doc_id, "hello", top_k=5)
    print(f"BM25 results: {b_results}")
    
    # 3. Test FileStore
    print("Testing File Store...")
    f_store = LocalFileStore()
    f_store.save_parent_chunks(doc_id, parents)
    loaded_parents = f_store.load_parent_chunks(doc_id)
    print(f"Loaded parents: {len(loaded_parents)}")
    
    # 4. Cleanup
    print("Cleaning up...")
    v_store.delete_document(doc_id)
    b_store.delete(doc_id)
    f_store.delete_document(doc_id)
    print("Done.")

if __name__ == "__main__":
    test_storage()
