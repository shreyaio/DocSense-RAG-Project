from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
import yaml
import os

class ChunkingConfig(BaseModel):
    parent_chunk_size: int = 512
    parent_chunk_overlap: int = 64
    child_chunk_size: int = 128
    child_chunk_overlap: int = 16
    min_chunk_tokens: int = 40
    separators: list[str] = ["\n\n", "\n", ". ", " "]

class EmbeddingConfig(BaseModel):
    model_name: str = "BAAI/bge-large-en-v1.5"
    batch_size: int = 32
    vector_dim: int = 1024
    query_prefix: str = "Represent this sentence for searching relevant passages: "
    normalise: bool = True

class QdrantConfig(BaseModel):
    mode: str = "local"
    local_path: str = "./data/qdrant_store"
    cloud_url: str = ""
    collection_name: str = "rag_chunks"
    hnsw_m: int = 16
    hnsw_ef_construct: int = 100
    hnsw_ef: int = 64

class RetrievalConfig(BaseModel):
    dense_top_k: int = 20
    sparse_top_k: int = 20
    rrf_k: int = 60
    rerank_top_k: int = 20
    final_top_k: int = 5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

class LLMConfig(BaseModel):
    provider: str = "openrouter"
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "mistralai/mistral-7b-instruct"
    fallback_model: str = "google/gemma-3-27b-it"
    max_tokens: int = 1024
    temperature: float = 0.1
    stream: bool = True

class AppSettings(BaseSettings):
    chunking: ChunkingConfig = ChunkingConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    qdrant: QdrantConfig = QdrantConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    llm: LLMConfig = LLMConfig()
    openrouter_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def load_settings(config_path: str = "backend/config/config.yaml") -> AppSettings:
    """Loads settings from config.yaml and applies env overrides."""
    
    # Try multiple paths for convenience during testing vs running
    paths_to_try = [
        config_path,
        "config.yaml",
        "config/config.yaml",
        os.path.join(os.path.dirname(__file__), "config.yaml")
    ]
    
    yaml_data = {}
    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
            break
            
    # Manually map yaml sections to our sub-models
    return AppSettings(
        chunking=ChunkingConfig(**yaml_data.get("chunking", {})),
        embedding=EmbeddingConfig(**yaml_data.get("embedding", {})),
        qdrant=QdrantConfig(**yaml_data.get("qdrant", {})),
        retrieval=RetrievalConfig(**yaml_data.get("retrieval", {})),
        llm=LLMConfig(**yaml_data.get("llm", {}))
    )

# Global settings instance
settings = load_settings()
