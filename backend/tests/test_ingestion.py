import os
import sys
import logging

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.pipeline.ingestion import IngestionPipeline
from storage.qdrant_store import QdrantLocalStore
from storage.bm25_store import LocalBM25Store
from storage.file_store import LocalFileStore

# Mocking progress callback
def progress_bar(progress, message):
    bar_length = 20
    filled_length = int(bar_length * progress / 100)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\rProgress: [{bar}] {progress}% - {message}')
    sys.stdout.flush()
    if progress == 100:
        print()

def test_full_ingestion():
    logging.basicConfig(level=logging.INFO)
    
    file_path = "sample.pdf"
    doc_id = "test_doc_001"
    source_file = "sample.pdf"

    # Initialize storage implementations (local mode)
    vector_store = QdrantLocalStore()
    bm25_store = LocalBM25Store()
    file_store = LocalFileStore()

    # Create pipeline
    pipeline = IngestionPipeline(
        vector_store=vector_store,
        bm25_store=bm25_store,
        file_store=file_store
    )

    print(f"\nStarting ingestion for: {source_file}")
    try:
        pipeline.run(
            file_path=file_path,
            doc_id=doc_id,
            source_file=source_file,
            progress_callback=progress_bar
        )
        print("\nIngestion test PASSED")
        
        # Verify storage
        print("\nVerifying storage contents...")
        
        # 1. Qdrant
        hits = vector_store.search(vector=[0.0]*1024, top_k=10, filters={"doc_id": doc_id})
        print(f"Qdrant: Found {len(hits)} chunks for doc_id {doc_id}")
        
        # 2. BM25
        bm25_hits = bm25_store.search(doc_id, "architecture", top_k=3)
        print(f"BM25: Found {len(bm25_hits)} matches for 'architecture'")
        
        # 3. FileStore
        parents = file_store.load_parent_chunks(doc_id)
        print(f"FileStore: Loaded {len(parents)} parent chunks")
        
    except Exception as e:
        print(f"\nIngestion test FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not os.path.exists("sample.pdf"):
        print("Error: sample.pdf not found. Run backend/tests/create_sample_pdf.py first.")
    else:
        test_full_ingestion()
