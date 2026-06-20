"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Profile, type ScoredStock } from "@/lib/api";

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProfiles().then(setProfiles).catch((e) => setError(e.message));
  }, []);

  const defaultProfile = profiles?.find((p) => p.is_default) ?? profiles?.[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 space-y-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-brg-900">Dashboard</h1>
        <Link href="/" className="text-sm text-brg hover:underline">+ New profile</Link>
      </div>

      {error && (
        <p className="text-sm text-danger">
          Backend unreachable. Start it with{" "}
          <code className="rounded bg-cream-200 px-1.5 py-0.5">uvicorn app.main:app --reload</code>.
          ({error})
        </p>
      )}

      {profiles && profiles.length === 0 && (
        <div className="rounded-xl border border-cream-300 bg-cream-50 p-8 text-center">
          <p className="text-ink-muted">No profile yet.</p>
          <Link href="/" className="mt-4 inline-block rounded-full bg-brg px-5 py-2 text-cream-50">
            Start onboarding
          </Link>
        </div>
      )}

      {profiles && profiles.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {profiles.map((p) => <ProfileCard key={p.id} profile={p} />)}
        </div>
      )}

      {defaultProfile && (
        <TickerLookup profile={defaultProfile} />
      )}
    </div>
  );
}

function ProfileCard({ profile: p }: { profile: Profile }) {
  return (
    <div className="rounded-xl border border-cream-300 bg-cream-50 p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold text-brg-900">{p.name}</h3>
        {p.is_default && (
          <span className="rounded-full bg-brg px-2 py-0.5 text-xs text-cream-50">default</span>
        )}
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-y-1 text-sm">
        <dt className="text-ink-soft">Capital</dt>
        <dd className="text-right tabular-nums">${p.capital_usd.toLocaleString()}</dd>
        <dt className="text-ink-soft">Risk</dt>
        <dd className="text-right capitalize">{p.risk}</dd>
        <dt className="text-ink-soft">Timeline</dt>
        <dd className="text-right capitalize">{p.timeline}</dd>
        <dt className="text-ink-soft">Max position</dt>
        <dd className="text-right tabular-nums">{p.max_position_pct}%</dd>
        <dt className="text-ink-soft">Max sector</dt>
        <dd className="text-right tabular-nums">{p.max_sector_pct}%</dd>
      </dl>
    </div>
  );
}

function TickerLookup({ profile }: { profile: Profile }) {
  const [ticker, setTicker] = useState("AAPL");
  const [scored, setScored] = useState<ScoredStock | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  async function lookup(t: string = ticker) {
    setLoading(true); setErr(null); setScored(null);
    try {
      const r = await api.scoreStock(t, profile.risk, profile.timeline);
      setScored(r);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-cream-300 bg-cream-50 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-brg">
        Look up a stock (scored for {profile.name})
      </h2>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => { e.preventDefault(); lookup(ticker.toUpperCase()); }}
      >
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="AAPL"
          maxLength={10}
          className="flex-1 rounded-md border border-cream-300 bg-white px-3 py-2 text-sm focus:border-brg focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brg px-4 py-2 text-sm text-cream-50 hover:bg-brg-800 disabled:opacity-50"
        >
          {loading ? "Scoring…" : "Score"}
        </button>
      </form>

      {err && <p className="mt-3 text-sm text-danger">{err}</p>}

      {scored && (
        <div className="mt-6 space-y-5">
          <div className="flex items-baseline justify-between border-b border-cream-300 pb-3">
            <div>
              <h3 className="text-xl font-semibold text-brg-900">
                {scored.snapshot.ticker} — {scored.snapshot.company_name}
              </h3>
              <p className="text-sm text-ink-muted">
                {scored.snapshot.sector} · {scored.snapshot.industry} ·{" "}
                ${scored.snapshot.current_price?.toFixed(2)}
              </p>
            </div>
            <ScoreBadge score={scored.score.composite} grade={scored.score.grade} />
          </div>

          <p className={`text-sm ${
            (scored.score.composite ?? 0) >= scored.score.support_required
              ? "text-success" : "text-danger"
          }`}>
            {scored.score.note}
          </p>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
            {scored.score.pillars.map((p) => (
              <PillarBlock key={p.name} pillar={p} />
            ))}
          </div>

          <details
            open={expanded}
            onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open)}
            className="rounded-md border border-cream-300 bg-cream-50/50"
          >
            <summary className="cursor-pointer p-3 text-sm font-medium text-brg">
              All 60+ data points
            </summary>
            <div className="space-y-4 p-4">
              {scored.snapshot.pillars.map((p) => (
                <div key={p.name}>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
                    {p.name}
                  </h4>
                  <div className="mt-1 grid grid-cols-1 gap-y-0.5 text-sm sm:grid-cols-2">
                    {Object.entries(p.items).map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b border-cream-200 py-1">
                        <span className="text-ink-soft">{k}</span>
                        <span className="tabular-nums">
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
              ))}
            </div>
          </details>

          <p className="text-xs text-ink-soft">
            sources: {scored.snapshot.sources.join(", ")} · {new Date(scored.snapshot.as_of).toLocaleString()}
          </p>
        </div>
      )}
    </section>
  );
}

function ScoreBadge({ score, grade }: { score: number | null; grade: string }) {
  const tone =
    score === null ? "bg-cream-200 text-ink-soft" :
    score >= 75   ? "bg-brg text-cream-50" :
    score >= 65   ? "bg-brg-500 text-cream-50" :
    score >= 55   ? "bg-gold text-brg-900" :
    "bg-danger/80 text-cream-50";
  return (
    <div className={`rounded-lg px-4 py-2 text-right ${tone}`}>
      <div className="text-2xl font-bold tabular-nums">{score?.toFixed(1) ?? "N/A"}</div>
      <div className="text-xs opacity-90">grade {grade}</div>
    </div>
  );
}

function PillarBlock({ pillar }: { pillar: import("@/lib/api").PillarScore }) {
  const tone =
    pillar.score === null   ? "border-cream-300 bg-cream-50 text-ink-soft" :
    pillar.score >= 75      ? "border-brg bg-brg/10 text-brg-900" :
    pillar.score >= 60      ? "border-brg-400 bg-brg/5 text-brg-800" :
    pillar.score >= 45      ? "border-cream-300 bg-cream-50 text-ink" :
    "border-danger/40 bg-danger/5 text-danger";
  return (
    <div className={`rounded-md border p-2 text-center ${tone}`}>
      <div className="text-[10px] uppercase tracking-wide opacity-70">{pillar.name}</div>
      <div className="text-lg font-semibold tabular-nums">
        {pillar.score === null ? "—" : pillar.score.toFixed(0)}
      </div>
      <div className="text-[10px] opacity-60">w {pillar.weight}</div>
    </div>
  );
}
