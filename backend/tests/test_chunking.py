import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.parse.pdf_parser import PDFParser
from core.parse.structure_detector import StructureDetector
from core.chunk.chunker import Chunker
from core.chunk.metadata_builder import MetadataBuilder
from models.chunk import ParsedBlock

def test_chunking_flow():
    print("--- Testing Chunking Flow ---")
    
    # Create synthetic blocks for testing
    blocks = [
        ParsedBlock(text="Title Chapter 1", page_number=1, block_type="heading", heading_level=1, section_path="Chapter 1"),
        ParsedBlock(text="This is some text in the first section. It should be split into parent and child chunks if it is long enough.", page_number=1, block_type="text", section_path="Chapter 1"),
        ParsedBlock(text="| Col1 | Col2 |\n|---|---|\n| Data1 | Data2 |", page_number=1, block_type="table", section_path="Chapter 1"),
        ParsedBlock(text="Title Chapter 2", page_number=2, block_type="heading", heading_level=1, section_path="Chapter 2"),
        ParsedBlock(text="More content here.", page_number=2, block_type="text", section_path="Chapter 2")
    ]
    
    chunker = Chunker()
    builder = MetadataBuilder()
    
    print("Stage 1: Chunking...")
    parents, children = chunker.chunk_document("test_doc_123", blocks)
    print(f"Created {len(parents)} parents and {len(children)} children.")
    
    print("\nStage 2: Finalizing Metadata...")
    parents, children = builder.finalize_chunks(
        doc_id="test_doc_123",
        source_file="test.pdf",
        original_blocks=blocks,
        parents=parents,
        children=children
    )
    
    # Verification
    for i, p in enumerate(parents):
        print(f"Parent {i} id: {p.parent_id[:8]}... (Section: {p.section_path}, Children: {len(p.child_ids)})")
        
    for i, c in enumerate(children[:5]):
        print(f"Child {i} id: {c.metadata.chunk_id[:8]}... (Parent: {c.metadata.parent_id[:8]}..., Prev: {str(c.metadata.prev_chunk_id)[:8]}..., Next: {str(c.metadata.next_chunk_id)[:8]}...)")

if __name__ == "__main__":
    test_chunking_flow()
