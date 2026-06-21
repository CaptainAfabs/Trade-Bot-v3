const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Risk = "low" | "medium" | "high";
export type Timeline = "short" | "medium" | "long" | "generational";

export interface Profile {
  id: number;
  user_id: number;
  name: string;
  risk: Risk;
  timeline: Timeline;
  capital_usd: number;
  min_market_cap_usd: number;
  max_position_pct: number;
  max_sector_pct: number;
  sectors_exclude: string[];
  sectors_prefer: string[];
  dividend_only: boolean;
  esg_only: boolean;
  follow_investors: string[];
  is_default: boolean;
}

export interface ProfileIn {
  name: string;
  risk: Risk;
  timeline: Timeline;
  capital_usd: number;
  sectors_exclude?: string[];
  is_default?: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  // 204 No Content (e.g. DELETE) has an empty body — don't try to parse it.
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  const text = await res.text();
  return (text ? JSON.parse(text) : (undefined as T)) as T;
}

export interface Pillar { name: string; items: Record<string, number | null> }

export interface StockSnapshot {
  ticker: string;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap_usd: number | null;
  current_price: number | null;
  currency: string;
  pillars: Pillar[];
  sources: string[];
  as_of: string;
}

export interface PillarScore { name: string; score: number | null; weight: number }

export interface CompositeScore {
  composite: number | null;
  grade: string;
  risk: Risk;
  timeline: Timeline;
  pillars: PillarScore[];
  drivers_positive: string[];
  drivers_negative: string[];
  support_required: number;
  note: string | null;
}

export interface ScoredStock {
  snapshot: StockSnapshot;
  score: CompositeScore;
}

export interface Investor {
  slug: string;
  display_name: string;
  kind: "fund" | "politician" | "individual";
  cik: string | null;
  bio: string | null;
  photo_url: string | null;
  description: string | null;
}

export interface Holding {
  name: string;
  cusip: string | null;
  cls: string | null;
  value_usd: number | null;
  shares: number | null;
  pct_portfolio: number | null;
}

export interface InvestorDetail extends Investor {
  period: string | null;
  filed: string | null;
  accession: string | null;
  total_value_usd: number | null;
  top_holdings: Holding[];
  holdings_note: string | null;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listProfiles: () => request<Profile[]>("/api/profiles"),
  createProfile: (p: ProfileIn) =>
    request<Profile>("/api/profiles", { method: "POST", body: JSON.stringify(p) }),
  deleteProfile: (id: number) =>
    request<void>(`/api/profiles/${id}`, { method: "DELETE" }),
  getStock: (ticker: string) =>
    request<StockSnapshot>(`/api/stocks/${ticker}`),
  scoreStock: (ticker: string, risk: Risk, timeline: Timeline) =>
    request<ScoredStock>(`/api/stocks/${ticker}/score?risk=${risk}&timeline=${timeline}`),
  listInvestors: () => request<Investor[]>("/api/investors"),
  getInvestor: (slug: string) =>
    request<InvestorDetail>(`/api/investors/${slug}`),
  addInvestor: (query: string) =>
    request<Investor>("/api/investors", { method: "POST", body: JSON.stringify({ query }) }),
  chat: (profile_id: number, message: string) =>
    request<{ reply: string; stop_reason: string }>("/api/chat", {
      method: "POST", body: JSON.stringify({ profile_id, message }),
    }),
  chatHistory: (profile_id: number) =>
    request<{ role: string; content: string }[]>(`/api/chat/history/${profile_id}`),
  clearChat: (profile_id: number) =>
    request<void>(`/api/chat/history/${profile_id}`, { method: "DELETE" }),
  backtest: (ticker: string, years = 5) =>
    request<{
      ticker: string; start_date: string; end_date: string;
      total_return_pct: number; annualized_return_pct: number;
      max_drawdown_pct: number; annualized_vol_pct: number; sharpe: number | null;
    }>(`/api/backtest/${ticker}?years=${years}`),
  getPortfolio: (profile_id: number) =>
    request<{
      n_positions: number;
      n_unvalued: number;
      total_value_usd: number;
      total_cost_usd: number;
      total_pnl_usd: number;
      total_pnl_pct: number;
      by_sector_pct: Record<string, number>;
      holdings: Array<{
        id: number; ticker: string; shares: number; avg_cost_usd: number;
        current_price_usd: number | null; market_value_usd: number | null;
        cost_basis_usd: number; pnl_usd: number | null; pnl_pct: number | null;
        weight_pct: number | null; sector: string | null; notes: string | null;
      }>;
    }>(`/api/portfolio/${profile_id}`),
  addHolding: (h: { profile_id: number; ticker: string; shares: number; avg_cost_usd: number; notes?: string }) =>
    request<{ id: number }>("/api/portfolio", { method: "POST", body: JSON.stringify(h) }),
  removeHolding: (id: number) =>
    request<void>(`/api/portfolio/${id}`, { method: "DELETE" }),
  monthlyReview: (profile_id: number) =>
    request<{ review: string; n_entries?: number }>(`/api/journal/${profile_id}/monthly-review`),
  previewDigest: (profile_id: number) =>
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/email/digest/${profile_id}/preview`,
  getRecommendations: (profile_id: number, limit = 15, force_refresh = false) =>
    request<{
      profile_id: number; risk: Risk; timeline: Timeline;
      support_required: number;
      picks: Array<{
        ticker: string; name: string | null; sector: string | null;
        price: number | null; score: number | null; grade: string;
        clears_threshold: boolean; drivers: string[]; sources: string[];
        followed_by: string[]; investor_boost: number;
      }>;
      n_cleared: number; n_near_misses: number; universe_size: number;
      cached: boolean;
    }>(`/api/recommendations?profile_id=${profile_id}&limit=${limit}${force_refresh ? "&force_refresh=true" : ""}`),
  followInvestor: (profile_id: number, slug: string) =>
    request<Profile>(`/api/profiles/${profile_id}/follow/${slug}`, { method: "POST" }),
  unfollowInvestor: (profile_id: number, slug: string) =>
    request<Profile>(`/api/profiles/${profile_id}/follow/${slug}`, { method: "DELETE" }),
  listNews: (params: { ticker?: string; min_impact?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.ticker) q.set("ticker", params.ticker);
    if (params.min_impact) q.set("min_impact", String(params.min_impact));
    if (params.limit) q.set("limit", String(params.limit));
    return request<{
      id: number; source: string; url: string; title: string;
      published_at: string | null; tickers: string[];
      sentiment: number | null; impact: number | null;
    }[]>(`/api/news?${q}`);
  },
};
