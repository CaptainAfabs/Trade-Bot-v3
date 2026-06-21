"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, type Profile, type ScoredStock } from "@/lib/api";
import { scoreColor } from "@/components/score";

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
      <div>
        <Link href="/dashboard" className="text-sm text-brg hover:underline">&larr; Dashboard</Link>
        <h1 className="mt-1 text-2xl font-semibold text-brg-900">Score a ticker</h1>
        {profile && (
          <p className="text-sm text-ink-muted">
            Weighted for <strong>{profile.name}</strong> · {profile.risk} risk · {profile.timeline} timeline
          </p>
        )}
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
      {scored && <ScoreView scored={scored} />}
    </div>
  );
}

/* ─────────── Cleaner score view ─────────── */

function ScoreView({ scored }: { scored: ScoredStock }) {
  const composite = scored.score.composite ?? 0;
  const threshold = scored.score.support_required;
  const clears = composite >= threshold;
  const c = scoreColor(scored.score.composite);

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className={`rounded-2xl border-2 p-6 ${c.bg} ${c.border}`}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-2xl font-bold text-brg-900">
              {scored.snapshot.ticker}
              <span className="ml-2 text-lg font-normal text-ink-muted">{scored.snapshot.company_name}</span>
            </h2>
            <div className="mt-1 flex items-center gap-2 text-sm text-ink-muted flex-wrap">
              {scored.snapshot.sector && (
                <span className="rounded-full bg-cream-50 border border-cream-300 px-2 py-0.5 text-xs">
                  {scored.snapshot.sector}
                </span>
              )}
              {scored.snapshot.industry && (
                <span className="rounded-full bg-cream-50 border border-cream-300 px-2 py-0.5 text-xs">
                  {scored.snapshot.industry}
                </span>
              )}
              <span className="text-base font-semibold text-brg-900 tabular-nums">
                ${scored.snapshot.current_price?.toFixed(2)}
              </span>
              {scored.snapshot.market_cap_usd && (
                <span className="text-xs">
                  · mcap ${(scored.snapshot.market_cap_usd / 1e9).toFixed(0)}B
                </span>
              )}
            </div>
          </div>
          <div className={`rounded-xl ${c.chip} px-5 py-3 text-right shrink-0`}>
            <div className="text-4xl font-bold tabular-nums leading-none">{composite.toFixed(1)}</div>
            <div className="text-xs mt-1 opacity-90">grade {scored.score.grade}</div>
          </div>
        </div>

        {/* Threshold bar */}
        <div className="mt-5">
          <ThresholdBar composite={composite} threshold={threshold} />
          <p className={`mt-2 text-sm font-medium ${clears ? "text-success" : "text-danger"}`}>
            {scored.score.note}
          </p>
        </div>
      </div>

      {/* Strong / weak */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-success/40 bg-success/5 p-4">
          <h3 className="text-xs uppercase tracking-wider font-semibold text-success">Strong pillars</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {scored.score.drivers_positive.length > 0
              ? scored.score.drivers_positive.map((d, i) => (
                  <li key={i} className="flex items-baseline gap-2">
                    <span className="text-success">▲</span>
                    <span>{d}</span>
                  </li>
                ))
              : <li className="text-ink-soft text-sm">No standout strengths.</li>}
          </ul>
        </div>
        <div className="rounded-xl border border-danger/40 bg-danger/5 p-4">
          <h3 className="text-xs uppercase tracking-wider font-semibold text-danger">Weak pillars</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {scored.score.drivers_negative.length > 0
              ? scored.score.drivers_negative.map((d, i) => (
                  <li key={i} className="flex items-baseline gap-2">
                    <span className="text-danger">▼</span>
                    <span>{d}</span>
                  </li>
                ))
              : <li className="text-ink-soft text-sm">No standout weaknesses.</li>}
          </ul>
        </div>
      </div>

      {/* Pillar grid */}
      <section>
        <h3 className="text-xs uppercase tracking-wider font-semibold text-brg mb-2">All 8 pillars (click for details)</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-1.5">
          {scored.score.pillars.map((p) => {
            const pc = scoreColor(p.score);
            return (
              <a key={p.name} href={`#pillar-${p.name}`} className={`rounded-md border p-2 text-center transition-transform hover:scale-105 ${pc.bg} ${pc.border} ${pc.text}`}>
                <div className="text-[9px] uppercase tracking-wide opacity-70">{p.name}</div>
                <div className="text-lg font-bold tabular-nums">
                  {p.score === null ? "—" : p.score.toFixed(0)}
                </div>
                <div className="text-[9px] opacity-60">weight {p.weight}</div>
              </a>
            );
          })}
        </div>
      </section>

      {/* Detailed metrics per pillar — always visible, organized */}
      <section className="space-y-3">
        <h3 className="text-xs uppercase tracking-wider font-semibold text-brg">Detailed metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {scored.snapshot.pillars.map((p) => {
            const pillarScore = scored.score.pillars.find((s) => s.name === p.name);
            const pc = scoreColor(pillarScore?.score ?? null);
            return (
              <div
                key={p.name}
                id={`pillar-${p.name}`}
                className={`rounded-lg border ${pc.border} bg-cream-50`}
              >
                <header className={`px-3 py-2 border-b border-cream-300 flex items-baseline justify-between rounded-t-lg ${pc.bg}`}>
                  <span className={`text-xs font-bold uppercase tracking-wider ${pc.text}`}>{p.name}</span>
                  {pillarScore?.score != null && (
                    <span className={`text-sm font-bold tabular-nums ${pc.text}`}>
                      {pillarScore.score.toFixed(0)}<span className="text-[10px] opacity-70 ml-1">w {pillarScore.weight}</span>
                    </span>
                  )}
                </header>
                <dl className="divide-y divide-cream-200">
                  {Object.entries(p.items).map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between px-3 py-1">
                      <dt className="text-xs text-ink-muted">{k}</dt>
                      <dd className="text-sm tabular-nums">{formatMetric(v)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            );
          })}
        </div>
      </section>

      <p className="text-xs text-ink-soft text-center">
        sources: {scored.snapshot.sources.join(" · ")} · as of {new Date(scored.snapshot.as_of).toLocaleString()}
      </p>
    </div>
  );
}

function ThresholdBar({ composite, threshold }: { composite: number; threshold: number }) {
  const compPct = Math.max(0, Math.min(100, composite));
  const threshPct = Math.max(0, Math.min(100, threshold));
  const clears = composite >= threshold;
  return (
    <div className="space-y-1">
      <div className="relative h-3 rounded-full bg-cream-200 overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 ${clears ? "bg-success" : "bg-danger"} transition-all`}
          style={{ width: `${compPct}%` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-ink"
          style={{ left: `${threshPct}%` }}
          title={`Threshold ${threshold.toFixed(0)}`}
        />
      </div>
      <div className="flex justify-between text-[10px] text-ink-soft">
        <span>0</span>
        <span>your threshold: {threshold.toFixed(0)}</span>
        <span>100</span>
      </div>
    </div>
  );
}

function formatMetric(v: number | null): string {
  if (v === null) return "—";
  if (Math.abs(v) >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (Math.abs(v) >= 1e9)  return `${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6)  return `${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3)  return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return v.toFixed(2);
}

export default function ScorePage() {
  return (
    <Suspense fallback={<p className="mx-auto max-w-5xl px-6 py-10 text-sm text-ink-soft">Loading…</p>}>
      <ScoreInner />
    </Suspense>
  );
}
