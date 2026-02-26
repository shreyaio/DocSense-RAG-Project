import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from typing import List, Dict, Any, Tuple
from models.chunk import ParsedBlock
from collections import Counter
import re

class PDFParser:
    """
    Two-pass PDF Parser:
    Pass 1 (PyMuPDF): Extract text blocks, font metrics, and detect repetitive headers/footers.
    Pass 2 (pdfplumber): Detect tables and extract them as markdown.
    """

    def __init__(self, header_footer_threshold: int = 3):
        self.header_footer_threshold = header_footer_threshold

    def parse(self, file_path: str) -> List[ParsedBlock]:
        """
        Main entry point for parsing a PDF.
        """
        # Pass 1: Extract blocks and metrics using PyMuPDF
        raw_blocks, font_stats = self._extract_raw_blocks(file_path)
        
        # Identify headers/footers to suppress
        suppress_hashes = self._identify_repetitive_blocks(raw_blocks)
        
        # Pass 2: Extract tables using pdfplumber
        tables_per_page = self._extract_tables(file_path)
        
        # Merge and refine
        final_blocks = self._merge_blocks(raw_blocks, tables_per_page, suppress_hashes, font_stats)
        
        return final_blocks

    def _extract_raw_blocks(self, file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extracts all text blocks with font info and page numbers.
        Also computes global font statistics for heading detection.
        """
        doc = fitz.open(file_path)
        blocks = []
        all_font_sizes = []

        for page_num, page in enumerate(doc):
            page_dict = page.get_text("dict")
            for b in page_dict["blocks"]:
                if b["type"] == 0:  # Text block
                    block_text = ""
                    block_font_sizes = []
                    block_fonts = []
                    
                    for line in b["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"]
                            block_font_sizes.append(span["size"])
                            block_fonts.append(span["font"])
                            all_font_sizes.append(span["size"])
                        block_text += " "
                    
                    blocks.append({
                        "text": block_text.strip(),
                        "page_number": page_num + 1,
                        "bbox": list(b["bbox"]), # [x0, y0, x1, y1]
                        "font_size": max(block_font_sizes) if block_font_sizes else 0,
                        "font_name": Counter(block_fonts).most_common(1)[0][0] if block_fonts else None,
                        "type": "text"
                    })

        doc.close()
        
        font_stats = {
            "median_size": pd.Series(all_font_sizes).median() if all_font_sizes else 0,
            "max_size": max(all_font_sizes) if all_font_sizes else 0
        }
        
        return blocks, font_stats

    def _identify_repetitive_blocks(self, blocks: List[Dict[str, Any]]) -> set:
        """
        Detects text that appears at the same Y-position on multiple pages.
        Used to filter out headers and footers.
        """
        pos_text_counts = Counter()
        for b in blocks:
            # Hash based on rounded Y-position and text content
            pos_hash = (round(b["bbox"][1], 0), b["text"].strip())
            pos_text_counts[pos_hash] += 1
            
        suppress = {pos_hash for pos_hash, count in pos_text_counts.items() 
                   if count >= self.header_footer_threshold}
        return suppress

    def _extract_tables(self, file_path: str) -> Dict[int, List[Dict[str, Any]]]:
        """
        Uses pdfplumber to detect and extract tables as markdown.
        Returns a dict mapping page_number -> list of table dicts.
        """
        tables_per_page = {}
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_tables = []
                found_tables = page.find_tables()
                for table in found_tables:
                    # Extract table data
                    table_data = table.extract()
                    if table_data:
                        # Convert to markdown using pandas
                        df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        md_text = df.to_markdown(index=False)
                        page_tables.append({
                            "text": md_text,
                            "bbox": list(table.bbox), # [x0, y0, x1, y1]
                            "type": "table"
                        })
                tables_per_page[i + 1] = page_tables
        return tables_per_page

    def _merge_blocks(self, 
                     raw_blocks: List[Dict[str, Any]], 
                     tables_per_page: Dict[int, List[Dict[str, Any]]],
                     suppress_hashes: set,
                     font_stats: Dict[str, Any]) -> List[ParsedBlock]:
        """
        Merges text blocks and tables, suppresses headers/footers, and assigns block types.
        """
        final_blocks = []
        processed_table_indices = set() # Per page, which raw blocks were absorbed by tables

        # Group raw blocks by page for easier merging
        blocks_by_page = {}
        for b in raw_blocks:
            p = b["page_number"]
            if p not in blocks_by_page:
                blocks_by_page[p] = []
            blocks_by_page[p].append(b)

        all_page_nums = sorted(list(set(list(blocks_by_page.keys()) + list(tables_per_page.keys()))))

        for p in all_page_nums:
            page_raw = blocks_by_page.get(p, [])
            page_tables = tables_per_page.get(p, [])
            
            # 1. Add tables
            for t in page_tables:
                final_blocks.append(ParsedBlock(
                    text=t["text"],
                    page_number=p,
                    block_type="table",
                    bounding_box=t["bbox"]
                ))

            # 2. Add text blocks that don't overlap with tables and aren't headers/footers
            for b in page_raw:
                # Check header/footer suppression
                pos_hash = (round(b["bbox"][1], 0), b["text"].strip())
                if pos_hash in suppress_hashes:
                    continue
                
                # Check table overlap
                is_inside_table = False
                for t in page_tables:
                    if self._is_overlap(b["bbox"], t["bbox"]):
                        is_inside_table = True
                        break
                
                if is_inside_table:
                    continue

                # Determine if it's a heading
                block_type = "text"
                heading_level = None
                if b["font_size"] > font_stats["median_size"] * 1.1:
                    block_type = "heading"
                    # Simple heuristic for level: larger is higher
                    if b["font_size"] > font_stats["median_size"] * 1.5:
                        heading_level = 1
                    elif b["font_size"] > font_stats["median_size"] * 1.3:
                        heading_level = 2
                    else:
                        heading_level = 3

                final_blocks.append(ParsedBlock(
                    text=b["text"],
                    page_number=p,
                    block_type=block_type,
                    font_size=b["font_size"],
                    font_name=b["font_name"],
                    bounding_box=b["bbox"],
                    heading_level=heading_level
                ))

        # Sort by page then Y-position
        final_blocks.sort(key=lambda x: (x.page_number, x.bounding_box[1] if x.bounding_box else 0))
        return final_blocks

    def _is_overlap(self, bbox1: List[float], bbox2: List[float]) -> bool:
        """
        Check if two bounding boxes overlap significantly.
        bbox format: [x0, y0, x1, y1]
        """
        # pdfplumber and fitz use similar bbox formats but wait
        # fitz: x0, y0, x1, y1
        # pdfplumber: x0, top, x1, bottom (which is x0, y0, x1, y1)
        
        # Check if bbox1 is inside or significantly overlaps bbox2
        return not (bbox1[2] < bbox2[0] or 
                    bbox1[0] > bbox2[2] or 
                    bbox1[3] < bbox2[1] or 
                    bbox1[1] > bbox2[3])

