"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, type Profile, type ScoredStock } from "@/lib/api";
import { PillarBlock, ScoreBadge, scoreColor } from "@/components/score";

function ScoreInner() {
  const sp = useSearchParams();
  const initialTicker = sp.get("ticker")?.toUpperCase() ?? "";
  const [profile, setProfile] = useState<Profile | null>(null);
  const [ticker, setTicker] = useState(initialTicker);
  const [scored, setScored] = useState<ScoredStock | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.listProfiles().then((ps) => setProfile(ps.find((p) => p.is_default) ?? ps[0] ?? null));
  }, []);

  useEffect(() => {
    if (profile && initialTicker) lookup(initialTicker, profile);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  async function lookup(t: string, p: Profile | null = profile) {
    if (!p) return;
    setLoading(true); setErr(null); setScored(null);
    try { setScored(await api.scoreStock(t.toUpperCase(), p.risk, p.timeline)); }
    catch (e) { setErr((e as Error).message); }
    finally { setLoading(false); }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <div className="flex items-baseline justify-between">
        <div>
          <Link href="/dashboard" className="text-sm text-brg hover:underline">&larr; Dashboard</Link>
          <h1 className="mt-1 text-2xl font-semibold text-brg-900">Score a ticker</h1>
          {profile && (
            <p className="text-sm text-ink-muted">
              Scored for profile <strong>{profile.name}</strong> · {profile.risk} risk · {profile.timeline} timeline
            </p>
          )}
        </div>
      </div>

      <form
        className="rounded-2xl border border-cream-300 bg-cream-50 p-4 flex gap-2"
        onSubmit={(e) => { e.preventDefault(); if (ticker.trim()) lookup(ticker); }}
      >
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="AAPL"
          maxLength={10}
          className="flex-1 rounded-md border border-cream-300 bg-white px-4 py-2.5 text-base focus:border-brg focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brg px-6 py-2.5 text-base text-cream-50 hover:bg-brg-800 disabled:opacity-50"
        >
          {loading ? "Scoring…" : "Score"}
        </button>
      </form>

      {err && <p className="text-sm text-danger">{err}</p>}

      {scored && (
        <div className="space-y-5">
          <div className="rounded-2xl border border-cream-300 bg-cream-50 p-5 flex items-baseline justify-between">
            <div>
              <h2 className="text-xl font-semibold text-brg-900">
                {scored.snapshot.ticker} — {scored.snapshot.company_name}
              </h2>
              <p className="text-sm text-ink-muted">
                {scored.snapshot.sector} · {scored.snapshot.industry} · ${scored.snapshot.current_price?.toFixed(2)}
              </p>
            </div>
            <ScoreBadge score={scored.score.composite} grade={scored.score.grade} size="lg" />
          </div>

          <p className={`text-sm ${
            (scored.score.composite ?? 0) >= scored.score.support_required
              ? "text-success" : "text-danger"
          }`}>
            {scored.score.note}
          </p>

          <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-7">
            {scored.score.pillars.map((p) => <PillarBlock key={p.name} pillar={p} />)}
          </div>

          {scored.score.drivers_positive.length > 0 && (
            <div className="rounded-md border border-success/40 bg-success/10 p-3 text-sm">
              <strong className="text-success">Strong:</strong>{" "}
              <span className="text-ink-muted">{scored.score.drivers_positive.join(", ")}</span>
            </div>
          )}
          {scored.score.drivers_negative.length > 0 && (
            <div className="rounded-md border border-danger/40 bg-danger/10 p-3 text-sm">
              <strong className="text-danger">Weak:</strong>{" "}
              <span className="text-ink-muted">{scored.score.drivers_negative.join(", ")}</span>
            </div>
          )}

          <details className="rounded-2xl border border-cream-300 bg-cream-50">
            <summary className="cursor-pointer p-4 text-sm font-semibold text-brg">All 60+ data points (deeper dive)</summary>
            <div className="space-y-4 p-4 max-h-[600px] overflow-y-auto">
              {scored.snapshot.pillars.map((p) => {
                const matching = scored.score.pillars.find((s) => s.name === p.name);
                const c = scoreColor(matching?.score ?? null);
                return (
                  <div key={p.name} className={`rounded-md border p-3 ${c.bg} ${c.border}`}>
                    <h4 className={`text-xs font-bold uppercase tracking-wider ${c.text}`}>
                      {p.name} {matching?.score != null && `· ${matching.score.toFixed(0)}`}
                    </h4>
                    <div className="mt-1 grid grid-cols-1 gap-y-0.5 text-sm sm:grid-cols-2">
                      {Object.entries(p.items).map(([k, v]) => (
                        <div key={k} className="flex justify-between border-b border-cream-200 py-1">
                          <span className="text-ink-soft text-xs">{k}</span>
                          <span className="tabular-nums text-xs">
                            {v === null
                              ? "—"
                              : Math.abs(v) >= 1e9 ? `${(v / 1e9).toFixed(2)}B`
                              : Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(2)}M`
                              : v.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </details>

          <p className="text-xs text-ink-soft">
            sources: {scored.snapshot.sources.join(", ")} · as of {new Date(scored.snapshot.as_of).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
}

export default function ScorePage() {
  return (
    <Suspense fallback={<p className="mx-auto max-w-5xl px-6 py-10 text-sm text-ink-soft">Loading…</p>}>
      <ScoreInner />
    </Suspense>
  );
}
