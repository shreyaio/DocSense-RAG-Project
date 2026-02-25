import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.parse.pdf_parser import PDFParser
from core.parse.structure_detector import StructureDetector

def test_parsing_flow(pdf_path: str):
    print(f"--- Testing Parsing Flow for: {pdf_path} ---")
    
    parser = PDFParser()
    detector = StructureDetector()
    
    print("Stage 1: Parsing...")
    blocks = parser.parse(pdf_path)
    print(f"Extracted {len(blocks)} blocks.")
    
    # Print sample blocks
    for i, b in enumerate(blocks[:10]):
        print(f"Block {i} [{b.block_type}]: {b.text[:100]}... (Page {b.page_number})")
        
    print("\nStage 2: Structure Detection...")
    enriched_blocks = detector.detect(blocks, pdf_path)
    
    # Print sample enriched blocks
    for i, b in enumerate(enriched_blocks[:20]):
        if b.block_type == "heading" or i % 5 == 0:
            print(f"Block {i} [{b.block_type}] (Path: {b.section_path}): {b.text[:50]}...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if os.path.exists(pdf_path):
            test_parsing_flow(pdf_path)
        else:
            print(f"File not found: {pdf_path}")
    else:
        print("Please provide a PDF file path.")
