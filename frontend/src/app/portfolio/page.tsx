"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Profile } from "@/lib/api";

type PortfolioData = Awaited<ReturnType<typeof api.getPortfolio>>;

export default function PortfolioPage() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [profileId, setProfileId] = useState<number | null>(null);
  const [data, setData] = useState<PortfolioData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.listProfiles().then((ps) => {
      setProfiles(ps);
      const def = ps.find((p) => p.is_default) ?? ps[0];
      if (def) setProfileId(def.id);
    }).catch((e) => setErr(e.message));
  }, []);

  async function refresh() {
    if (profileId == null) return;
    try { setData(await api.getPortfolio(profileId)); }
    catch (e) { setErr((e as Error).message); }
  }
  useEffect(() => { refresh(); }, [profileId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!profiles) {
    return <p className="mx-auto max-w-3xl px-6 py-10 text-sm text-ink-soft">Loading…</p>;
  }
  if (profiles.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-ink-muted">Create a profile first.</p>
        <Link href="/" className="mt-4 inline-block rounded-full bg-brg px-5 py-2 text-cream-50">Start onboarding</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-brg-900">Portfolio</h1>
        <div className="flex items-center gap-2">
          <select
            value={profileId ?? ""}
            onChange={(e) => setProfileId(Number(e.target.value))}
            className="rounded-md border border-cream-300 bg-white px-3 py-2 text-sm"
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {profileId != null && (
            <a
              href={api.previewDigest(profileId)}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border border-cream-300 bg-cream-50 px-3 py-2 text-sm text-brg hover:border-brg"
            >
              Preview email digest
            </a>
          )}
        </div>
      </div>

      {err && <p className="text-sm text-danger">{err}</p>}

      {data && <Summary data={data} />}
      {profileId != null && <AddHoldingForm profileId={profileId} onAdded={refresh} />}
      {data && <HoldingsTable data={data} onChanged={refresh} />}
      {profileId != null && <MonthlyReview profileId={profileId} />}
    </div>
  );
}

function Summary({ data }: { data: PortfolioData }) {
  const pnlClass = data.total_pnl_usd >= 0 ? "text-success" : "text-danger";
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <Stat label="Positions" value={data.n_positions.toString()} />
      <Stat label="Market value" value={`$${data.total_value_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
      <Stat label="Cost basis" value={`$${data.total_cost_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
      <Stat
        label="P/L"
        value={`${data.total_pnl_usd >= 0 ? "+" : ""}$${data.total_pnl_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${data.total_pnl_pct.toFixed(1)}%)`}
        className={pnlClass}
      />
    </section>
  );
}

function Stat({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return (
    <div className="rounded-xl border border-cream-300 bg-cream-50 p-4">
      <div className="text-[11px] uppercase tracking-wide text-ink-soft">{label}</div>
      <div className={`mt-1 text-xl font-semibold tabular-nums ${className}`}>{value}</div>
    </div>
  );
}

function HoldingsTable({ data, onChanged }: { data: PortfolioData; onChanged: () => void }) {
  if (data.holdings.length === 0) {
    return <p className="text-sm text-ink-soft">No holdings yet — add one above.</p>;
  }
  async function remove(id: number) {
    if (!confirm("Remove this holding?")) return;
    await api.removeHolding(id);
    onChanged();
  }
  return (
    <section className="rounded-xl border border-cream-300 bg-cream-50 overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-cream-200/60 text-left text-xs uppercase tracking-wide text-ink-soft">
          <tr>
            <th className="p-3">Ticker</th>
            <th className="p-3 text-right">Shares</th>
            <th className="p-3 text-right">Avg cost</th>
            <th className="p-3 text-right">Price</th>
            <th className="p-3 text-right">Value</th>
            <th className="p-3 text-right">P/L</th>
            <th className="p-3 text-right">Weight</th>
            <th className="p-3">Sector</th>
            <th className="p-3"></th>
          </tr>
        </thead>
        <tbody>
          {data.holdings.map((h) => (
            <tr key={h.id} className="border-t border-cream-200">
              <td className="p-3 font-semibold text-brg-900">{h.ticker}</td>
              <td className="p-3 text-right tabular-nums">{h.shares.toFixed(2)}</td>
              <td className="p-3 text-right tabular-nums">${h.avg_cost_usd.toFixed(2)}</td>
              <td className="p-3 text-right tabular-nums">{h.current_price_usd ? `$${h.current_price_usd.toFixed(2)}` : "—"}</td>
              <td className="p-3 text-right tabular-nums">{h.market_value_usd ? `$${h.market_value_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—"}</td>
              <td className={`p-3 text-right tabular-nums ${(h.pnl_pct ?? 0) >= 0 ? "text-success" : "text-danger"}`}>
                {h.pnl_pct === null ? "—" : `${h.pnl_pct >= 0 ? "+" : ""}${h.pnl_pct.toFixed(1)}%`}
              </td>
              <td className="p-3 text-right tabular-nums">{h.weight_pct?.toFixed(1) ?? "—"}%</td>
              <td className="p-3 text-ink-muted">{h.sector ?? "—"}</td>
              <td className="p-3 text-right">
                <button onClick={() => remove(h.id)} className="text-xs text-ink-soft hover:text-danger">remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AddHoldingForm({ profileId, onAdded }: { profileId: number; onAdded: () => void }) {
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");
  const [cost, setCost] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      await api.addHolding({
        profile_id: profileId,
        ticker: ticker.toUpperCase(),
        shares: Number(shares),
        avg_cost_usd: Number(cost),
      });
      setTicker(""); setShares(""); setCost("");
      onAdded();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-cream-300 bg-cream-50 p-4 flex flex-wrap gap-2 items-end">
      <Field label="Ticker"><input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} className="w-24 rounded-md border border-cream-300 bg-white px-3 py-2 text-sm" required maxLength={10} /></Field>
      <Field label="Shares"><input type="number" step="0.0001" value={shares} onChange={(e) => setShares(e.target.value)} className="w-28 rounded-md border border-cream-300 bg-white px-3 py-2 text-sm" required /></Field>
      <Field label="Avg cost (USD)"><input type="number" step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} className="w-32 rounded-md border border-cream-300 bg-white px-3 py-2 text-sm" required /></Field>
      <button disabled={busy} className="rounded-md bg-brg px-4 py-2 text-sm text-cream-50 hover:bg-brg-800 disabled:opacity-50">
        {busy ? "Adding…" : "+ Add"}
      </button>
      {err && <span className="text-xs text-danger">{err}</span>}
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wide text-ink-soft">{label}</span>
      {children}
    </label>
  );
}

function MonthlyReview({ profileId }: { profileId: number }) {
  const [review, setReview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setBusy(true); setErr(null);
    try {
      const r = await api.monthlyReview(profileId);
      setReview(r.review);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-cream-300 bg-cream-50 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-brg">Monthly Claude review</h2>
        <button
          onClick={load}
          disabled={busy}
          className="rounded-md bg-brg px-3 py-1.5 text-xs text-cream-50 hover:bg-brg-800 disabled:opacity-50"
        >
          {busy ? "Reviewing…" : review ? "Re-review" : "Run review"}
        </button>
      </div>
      {err && <p className="mt-2 text-sm text-danger">{err}</p>}
      {review && (
        <pre className="mt-3 whitespace-pre-wrap text-sm font-sans">{review}</pre>
      )}
      {!review && !err && !busy && (
        <p className="mt-3 text-sm text-ink-soft">
          Log decisions in the journal to enable a monthly review.
        </p>
      )}
    </section>
  );
}
