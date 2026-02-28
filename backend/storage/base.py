from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from models.chunk import ChildChunk, ParentChunk

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: List[ChildChunk]) -> None:
        pass

    @abstractmethod
    def search(self, vector: List[float], top_k: int, filters: Optional[Dict] = None) -> List[Dict]:
        pass

    @abstractmethod
    def get_by_ids(self, chunk_ids: List[str]) -> List[Dict]:
        """Fetch full payloads for a list of chunk_ids. Used to resolve sparse-only hits."""
        pass

    @abstractmethod
    def delete_document(self, doc_id: str) -> None:
        pass

    @abstractmethod
    def collection_exists(self) -> bool:
        pass

class BM25Store(ABC):
    @abstractmethod
    def build(self, doc_id: str, chunks: List[ChildChunk]) -> None:
        pass

    @abstractmethod
    def search(self, doc_id: str, query: str, top_k: int) -> List[Tuple[str, float]]:
        pass

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        pass

class FileStore(ABC):
    @abstractmethod
    def save_parent_chunks(self, doc_id: str, parents: List[ParentChunk]) -> None:
        pass

    @abstractmethod
    def load_parent_chunks(self, doc_id: str, parent_ids: Optional[List[str]] = None) -> Dict[str, ParentChunk]:
        pass

    @abstractmethod
    def list_documents(self) -> List[str]:
        """Returns a list of all indexed document IDs."""
        pass

    @abstractmethod
    def save_pdf(self, doc_id: str, file_bytes: bytes) -> str:
        pass

    @abstractmethod
    def delete_document(self, doc_id: str) -> None:
        pass
