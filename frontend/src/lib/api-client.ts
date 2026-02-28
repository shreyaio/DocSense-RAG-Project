/**
 * DocSense API Client
 * Single source for all backend communication.
 * Maps to the SSOT API contract endpoints.
 */

const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api";

/* ============================================
   TYPES — mirrors backend Pydantic models
   ============================================ */

export interface IngestionJob {
  job_id: string;
  doc_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  message: string;
  created_at: string;
  completed_at: string | null;
}

export interface DocumentRecord {
  doc_id: string;
  filename: string;
  file_path: string;
  page_count: number;
  total_chunks: number;
  indexed_at: string;
  status: "pending" | "processing" | "completed" | "failed";
  embedding_model: string;
}

export interface QueryFilters {
  page_range?: number[] | null;
  section_title?: string | null;
  block_type?: string | null;
}

export interface QueryRequest {
  question: string;
  doc_ids?: string[] | null;
  top_k?: number;
  filters?: QueryFilters | null;
}

export interface Citation {
  doc_id: string;
  source_file: string;
  page_number: number;
  page_range: number[];
  section_path: string | null;
  chunk_text_preview: string;
  relevance_score: number;
}

export interface RetrievalStats {
  dense_hits: number;
  sparse_hits: number;
  fused_candidates: number;
  reranked_from: number;
  final_count: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  citations: Citation[];
  model_used: string;
  retrieval_stats: RetrievalStats;
}

export interface SummarizeRequest {
  doc_id: string;
  mode: "summary" | "key_points";
}

export interface SummarizeResponse {
  doc_id: string;
  mode: string;
  output?: string;
  model_used?: string;
  chunk_count_used?: number;
  status?: "success" | "busy";
  message?: string;
}

export interface HealthResponse {
  status: string;
  qdrant_ok: boolean;
  models_loaded: boolean;
}

/* ============================================
   API FUNCTIONS
   ============================================ */

/** POST /ingest — Upload a PDF for ingestion. */
export async function uploadDocument(
  file: File
): Promise<{ job_id: string; doc_id: string; message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

/** GET /ingest/status/{job_id} — Poll ingestion progress. */
export async function getIngestionStatus(
  jobId: string
): Promise<IngestionJob> {
  const res = await fetch(`${API_BASE}/ingest/status/${jobId}`);
  if (!res.ok) throw new Error("Failed to fetch job status");
  return res.json();
}

/** GET /documents — List all indexed documents. */
export async function getDocuments(): Promise<DocumentRecord[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

/** DELETE /documents/{doc_id} — Remove a document and all its data. */
export async function deleteDocument(
  docId: string
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete document");
  return res.json();
}

/** POST /query — Query documents. Supports SSE streaming. */
export async function queryDocument(
  request: QueryRequest,
  onToken?: (token: string) => void
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Query failed");
  }

  const contentType = res.headers.get("content-type") || "";

  // SSE streaming
  if (contentType.includes("text/event-stream") && onToken && res.body) {
    return handleSSEStream(res.body, onToken);
  }

  return res.json();
}

async function handleSSEStream(
  body: ReadableStream<Uint8Array>,
  onToken: (token: string) => void
): Promise<QueryResponse> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: QueryResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data === "[DONE]") continue;
        try {
          const parsed = JSON.parse(data);
          if (parsed.token) onToken(parsed.token);
          if (parsed.response) finalResponse = parsed.response;
        } catch {
          onToken(data);
        }
      }
    }
  }

  if (finalResponse) return finalResponse;
  throw new Error("Stream ended without a complete response");
}

/** POST /summarize — Generate document summary or key points. */
export async function summarizeDocument(
  request: SummarizeRequest
): Promise<SummarizeResponse> {
  const res = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Summarization failed");
  }
  return res.json();
}

/** GET /health — Check backend health. */
export async function healthCheck(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}
