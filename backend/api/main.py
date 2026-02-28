import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from storage.qdrant_store import QdrantLocalStore
from storage.bm25_store import LocalBM25Store
from storage.file_store import LocalFileStore
from core.pipeline.ingestion import IngestionPipeline
from core.pipeline.retrieval import RetrievalPipeline
from core.generate.llm_client import LLMClient
from core.generate.summarizer import Summarizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup: Initialize singletons ---
    logger.info("Initializing RAG backend storage and pipelines...")
    
    # 1. Initialize Storage Implementations
    vector_store = QdrantLocalStore()
    bm25_store = LocalBM25Store()
    file_store = LocalFileStore()
    
    # 2. Initialize Pipelines (Pre-loading ML models once via class-singletons)
    ingestion_pipeline = IngestionPipeline(
        vector_store=vector_store,
        bm25_store=bm25_store,
        file_store=file_store
    )
    
    retrieval_pipeline = RetrievalPipeline(
        vector_store=vector_store,
        bm25_store=bm25_store,
        file_store=file_store
    )
    
    llm_client = LLMClient()
    summarizer = Summarizer(file_store, llm_client)
    
    # 3. Store in app.state for dependency injection
    app.state.vector_store = vector_store
    app.state.bm25_store = bm25_store
    app.state.file_store = file_store
    app.state.ingestion_pipeline = ingestion_pipeline
    app.state.retrieval_pipeline = retrieval_pipeline
    app.state.llm_client = llm_client
    app.state.summarizer = summarizer
    
    # In-memory job store for ingestion status tracking (Rule 631)
    app.state.jobs_db = {}
    
    logger.info("Initialization complete. All systems ready.")
    
    yield
    
    # --- Shutdown: Cleanup if needed ---
    logger.info("Shutting down RAG backend...")

# Create FastAPI instance
app = FastAPI(
    title="DocSense RAG API",
    description="Deterministic Hybrid RAG with Parent-Child Chunking",
    version="1.0.0",
    lifespan=lifespan
)

# Global CORS Configuration (Minimal for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"], # Common frontend ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}

# Import and include routers (Implementing routers next)
from api.routes import ingest, query, documents, summarize

app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(query.router, prefix="/api", tags=["Retrieval"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(summarize.router, prefix="/api", tags=["Summarization"])

@app.get("/", tags=["System"])
def root():
    return {"message": "DocSense RAG API is running."}
