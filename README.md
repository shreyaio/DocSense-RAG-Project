# DocSense – Hybrid Retrieval-Augmented Generation System

## Overview

DocSense is a modular Retrieval-Augmented Generation (RAG) system designed for intelligent interaction with long-form PDF documents. The system enables users to upload documents, perform hybrid retrieval over indexed content, and generate grounded summaries and context-aware responses using large language models.

This project was implemented from scratch with a focus on retrieval quality, architectural clarity, and extensibility.

---

## What is Retrieval-Augmented Generation (RAG)?

Retrieval-Augmented Generation (RAG) is a framework that enhances large language models by grounding their responses in external knowledge sources.

Instead of relying solely on a model’s internal training data, a RAG system:

1. Ingests and indexes documents  
2. Retrieves relevant content based on a user query  
3. Supplies retrieved context to a language model  
4. Generates responses conditioned on that context  

This approach improves factual accuracy, reduces hallucinations, and enables interaction with domain-specific or private data.

---

## Architectural Design

This implementation extends a standard RAG pipeline with structural enhancements to improve contextual coherence, retrieval precision, and scalability.

### Hybrid Retrieval Strategy

The system combines:

- Dense vector retrieval using semantic embeddings (Qdrant)
- Sparse keyword-based retrieval using BM25

Hybrid retrieval improves recall by balancing semantic similarity with lexical matching, resulting in more robust document grounding.

---

### Parent–Child Chunking Strategy

Rather than retrieving isolated micro-chunks directly, the ingestion pipeline implements a hierarchical chunking mechanism:

- Documents are split into fine-grained child chunks for embedding
- Larger parent sections are preserved for contextual reconstruction
- Parent-child relationships are stored in structured metadata

At query time:

- Retrieval operates on embedded child chunks
- Corresponding parent sections are reconstructed
- Duplicate parent sections are deduplicated
- Context is assembled at the parent level before generation

This significantly improves response coherence and reduces fragmentation in generated answers.

---

### Metadata-Aware Context Construction

Each indexed chunk stores structured metadata including:

- Document identifier  
- Parent identifier  
- Chunk index and positional information  
- Section hierarchy (where available)

Metadata is leveraged for:

- Parent-level reranking  
- Context reconstruction  
- Summary generation  
- Future extensibility into multi-document retrieval and citation-aware responses  

---

### Modular Ingestion Pipeline

The ingestion pipeline is divided into distinct, extensible stages:

1. PDF parsing and text extraction  
2. Semantic chunking  
3. Embedding generation  
4. Vector indexing in Qdrant  
5. BM25 sparse index creation  
6. Parent chunk persistence for contextual assembly  

Each stage is independently extendable and designed to support future integration with distributed processing or background task queues.

---

### Generation Layer Design

The generation layer includes:

- Controlled token management  
- Rate-limit handling and retry logic  
- Separation between summarization and interactive chat flows  
- Support for model fallback  

This ensures system stability under API constraints and production-like conditions.

---

## Tech Stack

### Backend
- Python  
- FastAPI  
- Qdrant (Vector Database)  
- BM25 (Sparse Retrieval)  
- httpx  
- OpenRouter / LLM APIs  

### Frontend
- React  
- Tailwind CSS  
- Grid-based layout system  
- Resizable split-pane interface  

---


## Author

Shreya Shah
