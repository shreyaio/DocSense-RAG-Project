import hashlib
from datetime import datetime, timezone
from typing import List, Tuple
from models.chunk import ChildChunk, ParentChunk, ChunkMetadata, ParsedBlock
from config.settings import settings

class MetadataBuilder:
    """
    Builds full ChunkMetadata objects for child chunks.
    Ensures deterministic IDs and correct linkage.
    """

    def finalize_chunks(self, 
                       doc_id: str, 
                       source_file: str,
                       original_blocks: List[ParsedBlock],
                       parents: List[ParentChunk], 
                       children: List[ChildChunk]) -> Tuple[List[ParentChunk], List[ChildChunk]]:
        """
        Populates all metadata fields for children and updates parent linkages with authoritative IDs.
        """
        final_children = []
        total_chunks = len(children)
        created_at = datetime.now(timezone.utc).isoformat()
        
        # 1. First Pass: Generate Authoritative IDs and Populate Structure Fields
        authoritative_id_map = {} # temp_id -> auth_id
        
        # Identify heading chunks indices for is_near_heading calc
        heading_indices = [i for i, c in enumerate(children) if c.metadata.block_type == "heading"]
        
        for i, child in enumerate(children):
            meta = child.metadata
            temp_id = meta.chunk_id
            
            # Auth ID: sha256(doc_id + str(page_number) + str(char_start))
            auth_id = hashlib.sha256(f"{doc_id}{meta.page_number}{meta.char_start}".encode()).hexdigest()
            authoritative_id_map[temp_id] = auth_id
            
            # Populate basic fixed fields
            meta.chunk_id = auth_id
            meta.source_file = source_file
            meta.total_chunks = total_chunks
            meta.created_at = created_at
            
            # Extract section info from section_path
            # Example: "Chapter 3 > 3.2 > 3.2.1"
            if meta.section_path:
                parts = [p.strip() for p in meta.section_path.split(">")]
                meta.section_title = parts[0] if len(parts) > 0 else None
                meta.subsection_title = parts[1] if len(parts) > 1 else None
                # heading_level is already set in chunker for heading blocks
                # For text blocks, we might infer it from the last heading, 
                # but the model only requires it if available.
            
            # Determine is_near_heading
            meta.is_near_heading = any(abs(i - h_idx) <= 2 for h_idx in heading_indices)
            
            final_children.append(child)

        # 2. Second Pass: Link prev/next and Update Parent IDs
        for i, child in enumerate(final_children):
            meta = child.metadata
            if i > 0:
                meta.prev_chunk_id = final_children[i-1].metadata.chunk_id
            if i < total_chunks - 1:
                meta.next_chunk_id = final_children[i+1].metadata.chunk_id
                
        # 3. Update Parent child_ids with authoritative IDs
        for parent in parents:
            new_child_ids = []
            for tid in parent.child_ids:
                if tid in authoritative_id_map:
                    new_child_ids.append(authoritative_id_map[tid])
                else:
                    # If tid was already an auth id or missing (shouldn't happen)
                    new_child_ids.append(tid)
            parent.child_ids = new_child_ids

        return parents, final_children
