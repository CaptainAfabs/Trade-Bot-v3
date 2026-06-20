"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Investor } from "@/lib/api";

const KIND_LABELS: Record<Investor["kind"], string> = {
  fund: "Hedge fund / institution",
  politician: "Politician",
  individual: "Individual",
};

export default function InvestorsPage() {
  const [all, setAll] = useState<Investor[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<"all" | Investor["kind"]>("all");
  const [addQuery, setAddQuery] = useState("");
  const [adding, setAdding] = useState(false);

  async function refresh() {
    try { setAll(await api.listInvestors()); }
    catch (e) { setErr((e as Error).message); }
  }
  useEffect(() => { refresh(); }, []);

  const filtered = useMemo(() => {
    if (!all) return [];
    let xs = all;
    if (kind !== "all") xs = xs.filter((i) => i.kind === kind);
    if (query.trim()) {
      const q = query.toLowerCase();
      xs = xs.filter((i) =>
        i.display_name.toLowerCase().includes(q) ||
        (i.description ?? "").toLowerCase().includes(q)
      );
    }
    return xs;
  }, [all, kind, query]);

  async function addByAI() {
    if (!addQuery.trim()) return;
    setAdding(true);
    try { await api.addInvestor(addQuery); setAddQuery(""); await refresh(); }
    catch (e) { setErr((e as Error).message); }
    finally { setAdding(false); }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-brg-900">Investors</h1>
          <p className="text-sm text-ink-muted">
            Click any name to see their latest 13F holdings (politicians: PTR feed coming v1.1).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name"
            className="rounded-md border border-cream-300 bg-white px-3 py-2 text-sm focus:border-brg focus:outline-none"
          />
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as "all" | Investor["kind"])}
            className="rounded-md border border-cream-300 bg-white px-3 py-2 text-sm"
          >
            <option value="all">All ({all?.length ?? 0})</option>
            <option value="fund">Funds</option>
            <option value="politician">Politicians</option>
            <option value="individual">Individuals</option>
          </select>
        </div>
      </div>

      <div className="rounded-xl border border-cream-300 bg-cream-50 p-4">
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => { e.preventDefault(); addByAI(); }}
        >
          <label className="text-sm font-medium text-brg-900">Ask AI to add someone:</label>
          <input
            value={addQuery}
            onChange={(e) => setAddQuery(e.target.value)}
            placeholder="e.g. Stan Druckenmiller, Bill Gross, Mohnish Pabrai"
            className="flex-1 min-w-60 rounded-md border border-cream-300 bg-white px-3 py-2 text-sm focus:border-brg focus:outline-none"
          />
          <button
            type="submit"
            disabled={adding || !addQuery.trim()}
            className="rounded-md bg-brg px-4 py-2 text-sm text-cream-50 hover:bg-brg-800 disabled:opacity-50"
          >
            {adding ? "Researching…" : "+ Add"}
          </button>
        </form>
        <p className="mt-2 text-xs text-ink-soft">Claude looks up bio, CIK, photo, then adds to your roster.</p>
      </div>

      {err && <p className="text-sm text-danger">{err}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map((inv) => (
          <Link
            key={inv.slug}
            href={`/investors/${inv.slug}`}
            className="group rounded-xl border border-cream-300 bg-cream-50 p-4 transition-colors hover:border-brg"
          >
            <div className="flex items-start gap-3">
              {inv.photo_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={inv.photo_url}
                  alt={inv.display_name}
                  className="h-16 w-16 rounded-md object-cover bg-cream-200"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              ) : (
                <div className="h-16 w-16 rounded-md bg-cream-200 flex items-center justify-center text-brg text-xl font-semibold">
                  {inv.display_name.slice(0, 1)}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-brg-900 leading-tight group-hover:text-brg-700">{inv.display_name}</h3>
                <div className="mt-0.5 text-[11px] uppercase tracking-wide text-ink-soft">{KIND_LABELS[inv.kind]}</div>
              </div>
            </div>
            <p className="mt-3 text-sm text-ink-muted line-clamp-3">{inv.description}</p>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && all && (
        <p className="text-sm text-ink-soft">No matches.</p>
      )}
    </div>
  );
}
