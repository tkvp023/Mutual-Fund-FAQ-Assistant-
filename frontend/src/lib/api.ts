const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types matching FastAPI Pydantic schemas ─────────────────────────────── */

export interface ChatResponse {
  answer:           string;
  query:            string;
  session_id:       string;
  source_funds:     string[];
  source_sections:  string[];
  source_urls:      string[];
  num_chunks:       number;
  context_summary:  string;
  model:            string;
  input_tokens:     number;
  output_tokens:    number;
  response_time_ms: number;
}

export interface FundInfo {
  name:         string;
  slug:         string;
  category:     string;
  sub_category: string;
  url:          string;
  risk:         string;
  color:        string;
}

export interface FundsResponse {
  funds:               FundInfo[];
  total:               number;
  suggested_questions: string[];
}

export interface HealthResponse {
  status:          string;
  pipeline_loaded: boolean;
  chunks_in_db:    number;
  collection:      string;
  version:         string;
}

/* ── API calls ──────────────────────────────────────────────────────────── */

export async function sendMessage(
  query: string,
  sessionId: string,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ query, session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json();
}

export async function getFunds(): Promise<FundsResponse> {
  const res = await fetch(`${API_BASE}/api/funds`);
  if (!res.ok) throw new Error(`Failed to fetch funds: ${res.status}`);
  return res.json();
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function getHistory(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/chat/history/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`);
  return res.json();
}

export async function clearHistory(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/chat/history/${sessionId}`, {
    method: "DELETE",
  });
  return res.json();
}
