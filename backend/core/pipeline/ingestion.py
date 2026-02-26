import logging
import time
from typing import List, Callable, Optional
from core.parse.pdf_parser import PDFParser
from core.parse.structure_detector import StructureDetector
from core.chunk.chunker import Chunker
from core.chunk.metadata_builder import MetadataBuilder
from core.embed.embedder import Embedder
from storage.base import VectorStore, BM25Store, FileStore
from models.chunk import ParsedBlock, ChildChunk, ParentChunk

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Orchestrates the ingestion process:
    parse -> structure_detect -> chunk -> build_metadata -> embed -> store
    """

    def __init__(self, 
                 vector_store: VectorStore, 
                 bm25_store: BM25Store, 
                 file_store: FileStore):
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.file_store = file_store
        
        # Initialize components
        self.parser = PDFParser()
        self.structure_detector = StructureDetector()
        self.chunker = Chunker()
        self.metadata_builder = MetadataBuilder()
        self.embedder = Embedder()

    def run(self, 
            file_path: str, 
            doc_id: str, 
            source_file: str,
            progress_callback: Optional[Callable[[int, str], None]] = None):
        """
        Runs the full ingestion pipeline for a single PDF.
        """
        try:
            def update_progress(progress: int, message: str):
                if progress_callback:
                    progress_callback(progress, message)
                logger.info(f"[{doc_id}] {progress}%: {message}")

            update_progress(5, "Starting processing")

            # Save PDF to persistence storage
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            self.file_store.save_pdf(doc_id, file_bytes)
            update_progress(8, "PDF saved to storage")

            # 1. Parsing
            update_progress(10, "Parsing PDF layout")
            raw_blocks = self.parser.parse(file_path)
            update_progress(25, f"Extracted {len(raw_blocks)} blocks")

            # 2. Structure Detection
            update_progress(30, "Detecting document structure")
            enriched_blocks = self.structure_detector.detect(raw_blocks, file_path)
            update_progress(35, "Structure enrichment complete")

            # 3. Chunking
            update_progress(40, "Creating parent-child chunks")
            parents, children = self.chunker.chunk_document(doc_id, enriched_blocks)
            update_progress(50, f"Generated {len(parents)} parents and {len(children)} children")

            # 4. Metadata Building
            update_progress(55, "Finalizing metadata and IDs")
            parents, children = self.metadata_builder.finalize_chunks(
                doc_id=doc_id,
                source_file=source_file,
                original_blocks=enriched_blocks,
                parents=parents,
                children=children
            )
            update_progress(60, "Metadata finalized")

            # 5. Embedding
            update_progress(65, "Generating embeddings (this may take a moment)")
            # Note: embedder.py updates chunks in-place as per previous implementations
            children = self.embedder.embed_chunks(children)
            update_progress(85, "Embedding complete")

            # 6. Storage
            update_progress(90, "Indexing vectors in Qdrant")
            self.vector_store.upsert(children)

            update_progress(95, "Building BM25 index")
            self.bm25_store.build(doc_id, children)

            update_progress(98, "Saving parent chunks for context retrieval")
            self.file_store.save_parent_chunks(doc_id, parents)

            update_progress(100, "Ingestion completed successfully")
            
        except Exception as e:
            logger.exception(f"Ingestion failed for {doc_id}")
            if progress_callback:
                progress_callback(-1, str(e)) # Use -1 to indicate failure
            raise e
