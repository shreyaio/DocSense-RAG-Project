import hashlib
from typing import List, Tuple, Dict, Any
import tiktoken
from models.chunk import ParsedBlock, ParentChunk, ChildChunk, ChunkMetadata
from config.settings import settings

class Chunker:
    """
    Implements section-aware parent-child chunking.
    - Groups ParsedBlocks by section boundary.
    - Splits text into parent chunks (512 tokens).
    - Subdivides into child chunks (128 tokens).
    - Tables/Headings are atomic (never split).
    """

    def __init__(self):
        # Using cl100k_base (standard for GPT-4/Mistral/etc) for token estimation
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.config = settings.chunking

    def chunk_document(self, doc_id: str, blocks: List[ParsedBlock]) -> Tuple[List[ParentChunk], List[ChildChunk]]:
        """
        Main entry point for chunking a document's parsed blocks.
        """
        parent_chunks = []
        child_chunks = []
        
        # 1. Group blocks by section_path to prevent cross-section chunks
        section_groups = self._group_by_section(blocks)
        
        absolute_chunk_index = 0
        cumulative_offset = 0
        
        for section_path, section_blocks in section_groups:
            buffer_text = ""
            buffer_blocks = []
            buffer_start_offset = cumulative_offset
            
            for block in section_blocks:
                # Tables and Headings are treated as atomic to preserve structure/type
                if block.block_type in ["table", "heading"]:
                    # Process buffered text first
                    if buffer_text:
                        # Use full buffer including trailing spaces to maintain char synchronization
                        p, c, absolute_chunk_index = self._process_text_segment(
                            doc_id, section_path, buffer_text, absolute_chunk_index, buffer_blocks, buffer_start_offset
                        )
                        parent_chunks.extend(p)
                        child_chunks.extend(c)
                        buffer_text = ""
                        buffer_blocks = []
                    
                    # Process atomic block (table or heading)
                    p, c, absolute_chunk_index = self._process_atomic_block(
                        doc_id, section_path, block, absolute_chunk_index, cumulative_offset
                    )
                    parent_chunks.extend(p)
                    child_chunks.extend(c)
                    cumulative_offset += len(block.text) + 1
                else:
                    if not buffer_text:
                        buffer_start_offset = cumulative_offset
                    buffer_text += block.text + " "
                    buffer_blocks.append(block)
                    cumulative_offset += len(block.text) + 1

            # Process remaining buffer
            if buffer_text:
                p, c, absolute_chunk_index = self._process_text_segment(
                    doc_id, section_path, buffer_text, absolute_chunk_index, buffer_blocks, buffer_start_offset
                )
                parent_chunks.extend(p)
                child_chunks.extend(c)

        return parent_chunks, child_chunks

    def _group_by_section(self, blocks: List[ParsedBlock]) -> List[Tuple[str, List[ParsedBlock]]]:
        groups = []
        if not blocks:
            return groups
            
        current_path = blocks[0].section_path
        current_group = []
        
        for b in blocks:
            if b.section_path != current_path:
                groups.append((current_path, current_group))
                current_path = b.section_path
                current_group = [b]
            else:
                current_group.append(b)
        
        groups.append((current_path, current_group))
        return groups

    def _process_text_segment(self, 
                             doc_id: str, 
                             section_path: str, 
                             text: str, 
                             start_index: int, 
                             contributing_blocks: List[ParsedBlock],
                             segment_start_offset: int) -> Tuple[List[ParentChunk], List[ChildChunk], int]:
        parents = []
        children = []
        current_index = start_index

        pages = [b.page_number for b in contributing_blocks]
        page_range = [min(pages), max(pages)]

        # Get all tokens for the segment
        full_tokens = self.encoder.encode(text)
        parent_ranges = self._get_token_ranges(len(full_tokens), self.config.parent_chunk_size, self.config.parent_chunk_overlap)

        for p_start, p_end in parent_ranges:
            # Deterministic character start based on decoded token length
            abs_parent_char_start = segment_start_offset + len(self.encoder.decode(full_tokens[:p_start]))
            parent_id = hashlib.sha256(f"{doc_id}{section_path}{abs_parent_char_start}".encode()).hexdigest()
            
            p_text = self.encoder.decode(full_tokens[p_start:p_end])
            
            # Sub-split into children using absolute indices relative to segment start
            parent_len = p_end - p_start
            child_ranges_rel = self._get_token_ranges(parent_len, self.config.child_chunk_size, self.config.child_chunk_overlap)
            
            child_ids_for_parent = []
            for c_start_rel, c_end_rel in child_ranges_rel:
                c_start_abs = p_start + c_start_rel
                c_end_abs = p_start + c_end_rel
                c_text = self.encoder.decode(full_tokens[c_start_abs:c_end_abs])
                
                abs_child_char_start = segment_start_offset + len(self.encoder.decode(full_tokens[:c_start_abs]))
                
                metadata = ChunkMetadata(
                    chunk_id=f"temp_{current_index}",
                    parent_id=parent_id,
                    prev_chunk_id=None,
                    next_chunk_id=None,
                    doc_id=doc_id,
                    source_file="",
                    page_number=self._find_page_for_offset(contributing_blocks, abs_child_char_start - segment_start_offset),
                    page_range=page_range,
                    char_start=abs_child_char_start,
                    char_end=abs_child_char_start + len(c_text),
                    section_path=section_path,
                    block_type="text",
                    token_count=len(self.encoder.encode(c_text)),
                    chunk_index=current_index,
                    total_chunks=0,
                    is_near_heading=False,
                    chunk_level="child",
                    embedding_model=settings.embedding.model_name,
                    created_at=""
                )
                child = ChildChunk(text=c_text, metadata=metadata)
                children.append(child)
                child_ids_for_parent.append(metadata.chunk_id)
                current_index += 1

            parent = ParentChunk(
                parent_id=parent_id,
                doc_id=doc_id,
                text=p_text,
                page_range=page_range,
                section_path=section_path,
                child_ids=child_ids_for_parent
            )
            parents.append(parent)

        return parents, children, current_index

    def _get_token_ranges(self, total_tokens: int, size: int, overlap: int) -> List[Tuple[int, int]]:
        """Helper to compute token index ranges (start, end) without string matching."""
        ranges = []
        s = 0
        while s < total_tokens:
            e = min(s + size, total_tokens)
            ranges.append((s, e))
            if e >= total_tokens:
                break
            s = e - overlap
            if s < 0: s = 0
        return ranges

    def _find_page_for_offset(self, blocks: List[ParsedBlock], offset_in_segment: int) -> int:
        current = 0
        for b in blocks:
            current += len(b.text) + 1
            if current > offset_in_segment:
                return b.page_number
        return blocks[-1].page_number if blocks else 1

    def _process_atomic_block(self, doc_id: str, section_path: str, block: ParsedBlock, start_index: int, offset: int) -> Tuple[List[ParentChunk], List[ChildChunk], int]:
        parent_id = hashlib.sha256(f"{doc_id}{section_path}{offset}".encode()).hexdigest()
        page_range = [block.page_number, block.page_number]
        
        metadata = ChunkMetadata(
            chunk_id=f"temp_{start_index}",
            parent_id=parent_id,
            prev_chunk_id=None,
            next_chunk_id=None,
            doc_id=doc_id,
            source_file="",
            page_number=block.page_number,
            page_range=page_range,
            char_start=offset,
            char_end=offset + len(block.text),
            section_path=section_path,
            block_type=block.block_type,
            token_count=len(self.encoder.encode(block.text)),
            chunk_index=start_index,
            total_chunks=0,
            is_near_heading=False,
            chunk_level="child",
            embedding_model=settings.embedding.model_name,
            created_at="",
            heading_level=block.heading_level if block.block_type == "heading" else None
        )
        
        child = ChildChunk(text=block.text, metadata=metadata)
        
        parent = ParentChunk(
            parent_id=parent_id,
            doc_id=doc_id,
            text=block.text,
            page_range=page_range,
            section_path=section_path,
            child_ids=[metadata.chunk_id]
        )
        
        return [parent], [child], start_index + 1

    def _recursive_split(self, text: str, size: int, overlap: int) -> List[str]:
        # Implementation maintained to keep required public signature
        tokens = self.encoder.encode(text)
        if len(tokens) <= size:
            return [text]

        chunks = []
        ranges = self._get_token_ranges(len(tokens), size, overlap)
        for s, e in ranges:
            chunks.append(self.encoder.decode(tokens[s:e]))
        return chunks
