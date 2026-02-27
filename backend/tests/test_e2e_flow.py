import os
import sys
import logging
import time
from dotenv import load_dotenv

# Add backend to sys.path to allow imports like 'from core...'
# Assuming script is run from project root
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load environment variables from .env
load_dotenv()

from core.pipeline.ingestion import IngestionPipeline
from core.pipeline.retrieval import RetrievalPipeline
from storage.qdrant_store import QdrantLocalStore
from storage.bm25_store import LocalBM25Store
from storage.file_store import LocalFileStore
from models.query import QueryRequest
from config.settings import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("e2e_test")

def progress_callback(progress, message):
    sys.stdout.write(f"\r[Ingestion] {progress}%: {message}")
    sys.stdout.flush()
    if progress == 100:
        print("\n")

def run_e2e_test():
    print("="*60)
    print("RAG SYSTEM END-TO-END VERIFICATION")
    print("="*60)

    # 1. Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not found in environment.")
        print("Please check your .env file.")
        return

    # 2. Configuration Overrides for testing
    settings.llm.stream = False # Set to false for easier printing in test script
    
    # 3. Initialize Storage
    print("\n[1/4] Initializing Storage...")
    vector_store = QdrantLocalStore()
    bm25_store = LocalBM25Store()
    file_store = LocalFileStore()
    print("Storage initialized (Local Mode).")

    # 4. Run Ingestion
    pdf_path = "sample.pdf"
    if not os.path.exists(pdf_path):
        print(f"ERROR: {pdf_path} not found. Please run 'python backend/tests/create_sample_pdf.py' first.")
        return

    doc_id = f"test_doc_{int(time.time())}"
    print(f"\n[2/4] Starting Ingestion for '{pdf_path}' (Doc ID: {doc_id})...")
    
    ingestion_pipeline = IngestionPipeline(vector_store, bm25_store, file_store)
    
    start_time = time.time()
    ingestion_pipeline.run(
        file_path=pdf_path,
        doc_id=doc_id,
        source_file="sample.pdf",
        progress_callback=progress_callback
    )
    ingestion_duration = time.time() - start_time
    print(f"Ingestion completed in {ingestion_duration:.2f} seconds.")

    # 5. Run Retrieval & Generation
    print("\n[3/4] Running Retrieval & Generation Pipeline...")
    retrieval_pipeline = RetrievalPipeline(vector_store, bm25_store, file_store)
    
    # Test Question - Adjust this based on your sample.pdf content
    test_question = "What is the core architecture of this RAG system?"
    print(f"Question: '{test_question}'")
    
    request = QueryRequest(
        question=test_question,
        doc_ids=[doc_id]
    )
    
    start_time = time.time()
    response = retrieval_pipeline.run(request)
    retrieval_duration = time.time() - start_time
    
    # 6. Display Results
    print("\n[4/4] Final Results:")
    print("-" * 30)
    print(f"ANSWER:\n{response.answer}")
    print("-" * 30)
    print(f"CITATIONS ({len(response.citations)}):")
    for i, citation in enumerate(response.citations):
        print(f"[{i+1}] {citation.source_file} (Page {citation.page_number}) - Section: {citation.section_path}")
        print(f"    Preview: {citation.chunk_text_preview[:100]}...")
    
    print("-" * 30)
    print("RETRIEVAL STATS:")
    print(f" - Dense Hits: {response.retrieval_stats.dense_hits}")
    print(f" - Sparse Hits: {response.retrieval_stats.sparse_hits}")
    print(f" - RRF Fused Candidates: {response.retrieval_stats.fused_candidates}")
    print(f" - Reranked From: {response.retrieval_stats.reranked_from}")
    print(f" - Final Context Count: {response.retrieval_stats.final_count}")
    print(f" - Total Time: {retrieval_duration:.2f} seconds")
    print("-" * 30)

    print("\nVerification Complete!")

if __name__ == "__main__":
    try:
        run_e2e_test()
    except Exception as e:
        logger.error(f"E2E Test Failed: {e}", exc_info=True)
        sys.exit(1)
