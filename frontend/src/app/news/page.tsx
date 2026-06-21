"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type News = Awaited<ReturnType<typeof api.listNews>>;

export default function NewsPage() {
  const [items, setItems] = useState<News | null>(null);
  const [minImpact, setMinImpact] = useState(0);
  const [ticker, setTicker] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    try {
      setItems(await api.listNews({
        limit: 100,
        min_impact: minImpact,
        ticker: ticker.trim() || undefined,
      }));
    } catch (e) { setErr((e as Error).message); }
  }
  useEffect(() => { refresh(); }, [minImpact, ticker]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 space-y-5">
      <div>
        <Link href="/dashboard" className="text-sm text-brg hover:underline">&larr; Dashboard</Link>
        <h1 className="mt-1 text-2xl font-semibold text-brg-900">Market news</h1>
        <p className="text-sm text-ink-muted">
          Ingested hourly from 12 RSS sources · sentiment + impact scored by Claude Haiku.
        </p>
      </div>

      <div className="rounded-2xl border border-cream-300 bg-cream-50 p-4 flex flex-wrap items-end gap-3">
        <Field label="Min impact (0-5)">
          <input
            type="range" min={0} max={5} step={1}
            value={minImpact}
            onChange={(e) => setMinImpact(Number(e.target.value))}
            className="w-40 accent-[var(--brg-700)]"
          />
          <span className="ml-2 text-sm tabular-nums">{minImpact}</span>
        </Field>
        <Field label="Filter by ticker">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="e.g. NVDA"
            maxLength={10}
            className="w-32 rounded-md border border-cream-300 bg-white px-3 py-1.5 text-sm"
          />
        </Field>
      </div>

      {err && <p className="text-sm text-danger">{err}</p>}

      <div className="rounded-2xl border border-cream-300 bg-cream-50">
        {!items && <p className="p-4 text-sm text-ink-soft">Loading…</p>}
        {items && items.length === 0 && (
          <p className="p-4 text-sm text-ink-soft">No matches. Try lowering impact or clearing the ticker filter.</p>
        )}
        <ul className="divide-y divide-cream-200">
          {items?.map((it) => (
            <li key={it.id} className="p-3 flex items-start gap-3 text-sm">
              <Dot s={it.sentiment} />
              <div className="flex-1">
                <a href={it.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:text-brg">
                  {it.title}
                </a>
                <div className="mt-0.5 text-xs text-ink-soft">
                  {it.source}
                  {it.tickers.length > 0 && (
                    <> · <span className="text-brg">{it.tickers.join(", ")}</span></>
                  )}
                  {it.published_at && <> · {new Date(it.published_at).toLocaleString()}</>}
                </div>
              </div>
              {it.impact != null && (
                <div className="text-xs whitespace-nowrap text-ink-soft">impact {it.impact.toFixed(0)}</div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-ink-soft">{label}</span>
      <div className="flex items-center">{children}</div>
    </div>
  );
}

function Dot({ s }: { s: number | null }) {
  const color =
    s === null     ? "bg-cream-300" :
    s > 0.15       ? "bg-success" :
    s < -0.15      ? "bg-danger" :
    "bg-gold";
  return <span className={`mt-1.5 inline-block h-2 w-2 rounded-full shrink-0 ${color}`} title={`sentiment ${s?.toFixed(2) ?? '—'}`} />;
}
