from pydantic import BaseModel

class ParsedBlock(BaseModel):
    text: str
    page_number: int
    block_type: str                  # "text" | "table" | "caption" | "heading"
    font_size: float | None = None
    font_name: str | None = None
    bounding_box: list[float] | None = None # [x0, y0, x1, y1]
    section_path: str | None = None         # "Chapter 3 > 3.2 > 3.2.1"
    heading_level: int | None = None        # 1 | 2 | 3 | None

class ChunkMetadata(BaseModel):
    # Identity
    chunk_id: str                    # sha256(doc_id + str(page_number) + str(char_start))
    parent_id: str
    prev_chunk_id: str | None        # None only for first chunk of document
    next_chunk_id: str | None        # None only for last chunk of document
    # Source location
    doc_id: str
    source_file: str
    page_number: int                 # first page of chunk
    page_range: list[int]            # always two ints: [42, 42] or [42, 43]
    char_start: int
    char_end: int
    # Document structure
    section_title: str | None = None
    subsection_title: str | None = None
    heading_level: int | None = None
    section_path: str | None = None         # "Chapter 3 > 3.2 Lipid Oxidation"
    # Chunk properties
    block_type: str                  # "text" | "table" | "caption"
    token_count: int                 # child chunk token count
    chunk_index: int                 # absolute position in document
    total_chunks: int                # total child chunks in this document
    is_near_heading: bool            # True if within 2 chunks of a heading block
    chunk_level: str                 # always "child"
    # Indexing info
    embedding_model: str
    created_at: str                  # ISO 8601 UTC

class ChildChunk(BaseModel):
    metadata: ChunkMetadata
    text: str
    embedding: list[float] | None = None    # None before embedding step

class ParentChunk(BaseModel):
    parent_id: str
    doc_id: str
    text: str
    page_range: list[int]
    section_path: str | None = None
    child_ids: list[str]
