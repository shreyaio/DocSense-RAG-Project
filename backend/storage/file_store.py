import os
import json
from typing import List, Dict
from backend.models.chunk import ParentChunk
from backend.storage.base import FileStore

class LocalFileStore(FileStore):
    """
    Implements FileStore using the local disk.
    - Stores parent chunk JSON for efficient lookup during context building.
    - Stores raw PDFs.
    """

    def __init__(self, 
                 parent_chunks_path: str = "./data/parent_chunks",
                 uploads_path: str = "./data/uploads"):
        self.parent_chunks_path = parent_chunks_path
        self.uploads_path = uploads_path
        os.makedirs(self.parent_chunks_path, exist_ok=True)
        os.makedirs(self.uploads_path, exist_ok=True)

    def save_parent_chunks(self, doc_id: str, parents: List[ParentChunk]) -> None:
        path = os.path.join(self.parent_chunks_path, f"{doc_id}.json")
        data = {p.parent_id: p.model_dump() for p in parents}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_parent_chunks(self, doc_id: str) -> Dict[str, ParentChunk]:
        path = os.path.join(self.parent_chunks_path, f"{doc_id}.json")
        if not os.path.exists(path):
            return {}
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return {pid: ParentChunk(**p_data) for pid, p_data in data.items()}

    def save_pdf(self, doc_id: str, file_bytes: bytes) -> str:
        # For now, we use doc_id + .pdf
        path = os.path.join(self.uploads_path, f"{doc_id}.pdf")
        with open(path, "wb") as f:
            f.write(file_bytes)
        return path

    def delete_document(self, doc_id: str) -> None:
        # Delete parent chunks
        p_path = os.path.join(self.parent_chunks_path, f"{doc_id}.json")
        if os.path.exists(p_path):
            os.remove(p_path)
            
        # Delete PDF
        u_path = os.path.join(self.uploads_path, f"{doc_id}.pdf")
        if os.path.exists(u_path):
            os.remove(u_path)
