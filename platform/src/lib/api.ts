import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/v1`,
  headers: { "Content-Type": "application/json" },
});

// Inject API key from localStorage (client-side only)
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const key = localStorage.getItem("lucent_api_key");
    if (key) config.headers.Authorization = `Bearer ${key}`;
  }
  return config;
});

export interface Run {
  id: string;
  endpoint_url: string;
  status: string;
  corpus_version: string;
  composite_score: number | null;
  score_adversarial: number | null;
  score_tool_misuse: number | null;
  score_hallucination: number | null;
  score_recovery: number | null;
  score_latency: number | null;
  score_cost: number | null;
  latency_p50: number | null;
  latency_p95: number | null;
  latency_p99: number | null;
  prompt_count: number;
  completed_count: number;
  failed_count: number;
  scorer_version: string;
  manifest_sha256: string | null;
  weights_version: string;
  weights_snapshot: Record<string, number>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export type RunSummary = Pick<Run, "id" | "endpoint_url" | "status" | "composite_score" | "prompt_count" | "completed_count" | "failed_count" | "created_at">;

export interface Result {
  id: string;
  run_id: string;
  prompt_id: string;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  score_adversarial: number | null;
  score_tool_misuse: number | null;
  score_hallucination: number | null;
  score_recovery: number | null;
  score_latency: number | null;
  score_cost: number | null;
  composite_score: number | null;
  status: string;
  captured_at: string | null;
  scored_at: string | null;
  rationale_adversarial?: unknown;
  rationale_tool_misuse?: unknown;
  rationale_hallucination?: { rationale: string; claims?: Array<{ text: string; grounded: boolean; is_temporal: boolean }> } | null;
  rationale_recovery?: { turns: Array<{ ordinal: number; score: number; error_type: string; rationale: string }> } | null;
  tool_call_graph?: unknown;
  recovery_turns?: Array<{ response_text: string; injection: string; original_goal: string; error_type: string }> | null;
  prompt_snapshot?: { text: string; expected_behavior: string } | null;
  raw_payload?: Record<string, unknown> | null;
  error?: string;
}

export interface Prompt {
  id: string;
  text: string;
  category: string;
  subcategory: string | null;
  severity: string;
  expected_behavior: string;
  corpus_version: string;
  upvotes: number;
  created_at: string;
}

export const runsApi = {
  export: (id: string) => api.get<Blob>(`/runs/${id}/export`, { responseType: "blob" }).then((r) => r.data),
  create: (data: { endpoint_url: string; headers?: Record<string, string>; system_prompt?: string }) =>
    api.post<Run>("/runs", data, { headers: { "Idempotency-Key": crypto.randomUUID() } }).then((r) => r.data),
  list: (page = 1) =>
    api.get<RunSummary[]>("/runs", { params: { page } }).then((r) => r.data),
  get: (id: string) =>
    api.get<Run>(`/runs/${id}`).then((r) => r.data),
  results: (id: string, page = 1) =>
    api.get<Result[]>(`/runs/${id}/results`, { params: { page } }).then((r) => r.data),
  trace: (runId: string, promptId: string) =>
    api.get<Result>(`/runs/${runId}/results/${promptId}`).then((r) => r.data),
};

export const leaderboardApi = {
  get: (sortBy = "composite_score", page = 1, corpusVersion?: string) =>
    api
      .get<Run[]>("/leaderboard", {
        params: { sort_by: sortBy, page, corpus_version: corpusVersion },
      })
      .then((r) => r.data),
};

export const promptsApi = {
  list: (params?: { category?: string; severity?: string; version?: string }) =>
    api.get<Prompt[]>("/prompts", { params }).then((r) => r.data),
  contribute: (data: { text: string; category: string; severity: string; expected_behavior: string }) =>
    api.post<Prompt>("/prompts/contribute", data).then((r) => r.data),
  upvote: (id: string) =>
    api.post<Prompt>(`/prompts/${id}/upvote`).then((r) => r.data),
};
