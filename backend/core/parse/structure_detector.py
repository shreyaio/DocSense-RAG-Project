from typing import List, Dict, Any, Optional
from backend.models.chunk import ParsedBlock
import fitz

class StructureDetector:
    """
    Analyzes ParsedBlocks to build a hierarchical section tree and assign section paths.
    Uses native PDF TOC if available, otherwise relies on heading blocks.
    """

    def detect(self, blocks: List[ParsedBlock], file_path: Optional[str] = None) -> List[ParsedBlock]:
        """
        Enriches ParsedBlocks with section_path.
        """
        toc = []
        if file_path:
            try:
                doc = fitz.open(file_path)
                toc = doc.get_toc() # List of [level, title, page]
                doc.close()
            except Exception:
                toc = []

        if toc:
            return self._enrich_with_toc(blocks, toc)
        else:
            return self._enrich_with_headings(blocks)

    def _enrich_with_toc(self, blocks: List[ParsedBlock], toc: List[List[Any]]) -> List[ParsedBlock]:
        """
        Uses native TOC to assign section paths.
        toc entry: [level, title, page]
        """
        # Sort TOC by page number and then level
        sorted_toc = sorted(toc, key=lambda x: (x[2], x[0]))
        
        last_path = None
        toc_idx = 0
        
        for b in blocks:
            # Advance toc_idx for all TOC entries that occur on or before this block's page
            while toc_idx < len(sorted_toc) and sorted_toc[toc_idx][2] <= b.page_number:
                # Update the active section path
                last_path = self._get_path_at_index(sorted_toc, toc_idx)
                toc_idx += 1
            
            b.section_path = last_path
            
        return blocks

    def _get_path_at_index(self, sorted_toc: List[List[Any]], index: int) -> str:
        path = []
        target_level = sorted_toc[index][0]
        
        i = index
        while i >= 0 and len(path) < target_level:
            curr_level, curr_title, curr_page = sorted_toc[i]
            # If we found an ancestor or the target itself
            if curr_level == target_level - len(path):
                path.insert(0, curr_title)
            i -= 1
        return " > ".join(path) if path else None

    def _enrich_with_headings(self, blocks: List[ParsedBlock]) -> List[ParsedBlock]:
        """
        Infers structure from blocks flagged as 'heading'.
        Uses a clean stack-based approach.
        """
        section_stack = []
        
        for b in blocks:
            if b.block_type == "heading" and b.heading_level is not None:
                level = b.heading_level
                title = b.text.strip()
                
                # Truncate stack to level-1 to handle H1 -> H3 -> H2 transitions
                section_stack = section_stack[:level - 1]
                section_stack.append(title)
                
            b.section_path = " > ".join(section_stack) if section_stack else None
            
        return blocks
