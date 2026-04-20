const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SimulateRequest {
  entry_id: number;
  gw: number;
  league_id: number;
  mode: "Live" | "Pre-GW";
  n_sims: number;
  rivals_to_sim: number;
}

export interface RivalSummary {
  entry: number;
  name: string;
  league_rank: number;
  p10: number;
  p50: number;
  p90: number;
}

export interface PlayerProjection {
  player: string;
  pos: string;
  p10: number;
  p50: number;
  p90: number;
  mean: number;
}

export interface SimulateResponse {
  run_id: string;
  my_p10: number;
  my_p50: number;
  my_p90: number;
  rank_p10: number;
  rank_p50: number;
  rank_p90: number;
  p_win: number;
  p_top3: number;
  rivals_summary: RivalSummary[];
  player_projections: PlayerProjection[];
  rank_histogram: { rank: number; count: number }[];
}

export interface RiskEntry {
  name: string;
  element_id: number;
  position: string;
  sell_urgency: number;
  risk_factors: string[];
  reasoning: string;
}

export interface Recommendation {
  rank: number;
  player_out: string;
  player_out_id: number;
  player_in: string;
  player_in_id: number;
  position: string;
  cost_hit: number;
  reasoning: string;
  confidence: "High" | "Medium" | "Low";
  projected_rank_p50?: number;
  projected_rank_p10?: number;
  projected_rank_p90?: number;
  rank_improvement?: number;
  projected_pts_p50?: number;
  suggestion_id?: number;
  thumbs_up: number;
  thumbs_down: number;
  user_vote?: number | null;
}

export interface AdvisorResponse {
  risk_analysis: RiskEntry[];
  recommendations: Recommendation[];
  current_rank_p50: number;
  community_context_used: boolean;
  community_votes_count: number;
  message?: string | null;
}

export interface MetaAnalysisData {
  id?: number;
  summary?: string;
  liked_patterns?: string[];
  rejected_patterns?: string[];
  gameweek_range?: string;
  created_at?: string;
}

export interface StatsData {
  total_runs: number;
  total_votes: number;
  total_suggestions: number;
}

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkErr) {
    throw new Error(
      `Cannot reach backend at ${API_BASE}. Is the server running? (${String(networkErr)})`
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      detail = parsed.detail ?? body;
    } catch {}
    throw new Error(`HTTP ${res.status}: ${detail || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
  simulate: (req: SimulateRequest) =>
    fetchApi<SimulateResponse>("/api/simulate", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  advisor: (req: {
    run_id: string;
    budget: number;
    free_transfers: number;
    session_id: string;
    entry_id: number;
    gw: number;
  }) =>
    fetchApi<AdvisorResponse>("/api/advisor", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  castVote: (suggestion_id: number, session_id: string, value: 1 | -1) =>
    fetchApi<{ ok: boolean; thumbs_up: number; thumbs_down: number; net_votes: number }>(
      "/api/votes",
      {
        method: "POST",
        body: JSON.stringify({ suggestion_id, session_id, value }),
      }
    ),

  getMeta: () => fetchApi<MetaAnalysisData>("/api/meta"),

  runMeta: () =>
    fetchApi<MetaAnalysisData>("/api/meta/run", { method: "POST" }),

  getStats: () => fetchApi<StatsData>("/api/stats"),

  health: () => fetchApi<{ status: string; db: string }>("/health"),
};
