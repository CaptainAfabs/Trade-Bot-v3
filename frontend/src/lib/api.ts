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
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listProfiles: () => request<Profile[]>("/api/profiles"),
  createProfile: (p: ProfileIn) =>
    request<Profile>("/api/profiles", { method: "POST", body: JSON.stringify(p) }),
  deleteProfile: (id: number) =>
    request<void>(`/api/profiles/${id}`, { method: "DELETE" }),
  getStock: (ticker: string) =>
    request<{ ticker: string; note: string }>(`/api/stocks/${ticker}`),
};
