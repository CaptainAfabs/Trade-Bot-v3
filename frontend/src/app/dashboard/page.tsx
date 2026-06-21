"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, type Profile } from "@/lib/api";
import { scoreColor } from "@/components/score";

type Recs = Awaited<ReturnType<typeof api.getRecommendations>>;
type Portfolio = Awaited<ReturnType<typeof api.getPortfolio>>;
type News = Awaited<ReturnType<typeof api.listNews>>;
type Investors = Awaited<ReturnType<typeof api.listInvestors>>;

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshProfiles() {
    try {
      const ps = await api.listProfiles();
      setProfiles(ps);
      if (activeId == null || !ps.find((p) => p.id === activeId)) {
        const def = ps.find((p) => p.is_default) ?? ps[0] ?? null;
        setActiveId(def?.id ?? null);
      }
    } catch (e) { setError((e as Error).message); }
  }
  useEffect(() => { refreshProfiles(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <p className="text-sm text-danger">
        Backend unreachable.{" "}
        <code className="rounded bg-cream-200 px-1.5 py-0.5">uvicorn app.main:app --reload</code>
      </p>
    </div>
  );
  if (!profiles) return <p className="mx-auto max-w-3xl px-6 py-10 text-sm text-ink-soft">Loading…</p>;
  if (profiles.length === 0 || activeId == null) return (
    <div className="mx-auto max-w-3xl px-6 py-10 text-center">
      <p className="text-ink-muted">No profile yet — let&apos;s set one up.</p>
      <Link href="/" className="mt-4 inline-block rounded-full bg-brg px-6 py-2.5 text-cream-50">
        Start onboarding
      </Link>
    </div>
  );

  const active = profiles.find((p) => p.id === activeId)!;

  async function deleteActive() {
    if (profiles!.length <= 1) {
      alert("Can't delete your only profile.");
      return;
    }
    if (!confirm(`Delete profile "${active.name}"? This removes its holdings and chat history.`)) return;
    await api.deleteProfile(active.id);
    setActiveId(null);
    await refreshProfiles();
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-5 space-y-4">
      <TopBar
        profiles={profiles}
        active={active}
        onSwitch={setActiveId}
        onDelete={deleteActive}
      />

      <RecommendationsRow profile={active} />

      <ScoreTickerCard />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5 flex flex-col gap-4">
          <PortfolioCard profile={active} />
          <NewsCard profile={active} />
        </div>
        <div className="lg:col-span-7">
          <ChatCard profile={active} />
        </div>
      </div>

      <InvestorsStrip profile={active} />
    </div>
  );
}

/* ───────── Top bar (compact) ───────── */

function TopBar({
  profiles, active, onSwitch, onDelete,
}: {
  profiles: Profile[];
  active: Profile;
  onSwitch: (id: number) => void;
  onDelete: () => void;
}) {
  return (
    <header className="rounded-xl border border-cream-300 bg-cream-50 px-5 py-3 flex flex-wrap items-center gap-4">
      <div className="flex-1 min-w-0">
        <div className="text-[10px] uppercase tracking-wider text-ink-soft leading-none">Active profile</div>
        <div className="flex items-baseline gap-3 mt-0.5">
          <select
            value={active.id}
            onChange={(e) => onSwitch(Number(e.target.value))}
            className="bg-transparent border-0 text-xl font-semibold text-brg-900 focus:outline-none focus:ring-0 cursor-pointer pr-6"
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}{p.is_default ? " · default" : ""}
              </option>
            ))}
          </select>
          <span className="text-sm text-ink-muted truncate">
            <span className="capitalize">{active.risk}</span> risk · <span className="capitalize">{active.timeline}</span> · ${active.capital_usd.toLocaleString()}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Link href="/" className="rounded-md border border-cream-300 bg-white px-3 py-1.5 text-sm text-brg hover:border-brg">
          + New profile
        </Link>
        {profiles.length > 1 && (
          <button
            onClick={onDelete}
            className="rounded-md border border-cream-300 bg-white px-3 py-1.5 text-sm text-ink-soft hover:border-danger hover:text-danger"
            title={`Delete ${active.name}`}
          >
            Delete profile
          </button>
        )}
      </div>
    </header>
  );
}

function ScoreTickerCard() {
  const [ticker, setTicker] = useState("");
  return (
    <SectionCard
      title="Look up any ticker"
      subtitle="Score any US stock against your active profile. Press Enter or click Score — full breakdown opens on the next page."
    >
      <form
        onSubmit={(e) => { e.preventDefault(); if (ticker.trim()) location.href = `/score?ticker=${ticker.toUpperCase()}`; }}
        className="flex flex-wrap gap-2 items-center"
      >
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="e.g. AAPL, NVDA, BRK-B"
          maxLength={10}
          className="flex-1 min-w-48 rounded-md border border-cream-300 bg-white px-3 py-2 text-base focus:border-brg focus:outline-none"
        />
        <button
          type="submit"
          disabled={!ticker.trim()}
          className="rounded-md bg-brg px-5 py-2 text-sm text-cream-50 hover:bg-brg-800 disabled:opacity-50"
        >
          Score
        </button>
        <span className="text-xs text-ink-soft ml-1">
          Try popular ones: {["AAPL","NVDA","MSFT","TSLA","JPM"].map((t, i) => (
            <span key={t}>
              {i > 0 && " · "}
              <button
                type="button"
                onClick={() => { location.href = `/score?ticker=${t}`; }}
                className="text-brg hover:underline"
              >
                {t}
              </button>
            </span>
          ))}
        </span>
      </form>
    </SectionCard>
  );
}

/* ───────── Card scaffolding ───────── */

function SectionCard({
  title, href, subtitle, action, children, className = "",
}: {
  title: string;
  href?: string;
  subtitle: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  const heading = href ? (
    <Link href={href} className="text-base font-semibold text-brg-900 hover:text-brg group">
      {title} <span className="text-xs text-brg group-hover:translate-x-0.5 inline-block transition-transform">→</span>
    </Link>
  ) : (
    <h2 className="text-base font-semibold text-brg-900">{title}</h2>
  );
  return (
    <section className={`rounded-xl border border-cream-300 bg-cream-50 p-4 ${className}`}>
      <div className="flex items-start justify-between gap-3 pb-2 border-b border-cream-300">
        <div className="min-w-0">
          {heading}
          <p className="mt-0.5 text-xs text-ink-soft leading-snug">{subtitle}</p>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

/* ───────── Recommendations ───────── */

function RecommendationsRow({ profile }: { profile: Profile }) {
  const [recs, setRecs] = useState<Recs | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true); setErr(null); setRecs(null);
    api.getRecommendations(profile.id, 15)
      .then(setRecs)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [profile.id]);

  return (
    <SectionCard
      title="Recommended for you"
      subtitle="Claude generates ~40 candidates tailored to your profile, then every one is scored. The list below shows the ones that clear your threshold first, then near-misses."
      action={recs && (
        <div className="flex items-center gap-3 text-[11px] text-ink-soft whitespace-nowrap">
          <span>
            <span className="text-success font-semibold">{recs.n_cleared}</span> cleared · {recs.n_near_misses} near · {recs.universe_size} screened
          </span>
          <span className="text-ink-soft/60">|</span>
          <span>threshold {recs.support_required.toFixed(0)}</span>
          <span className="text-ink-soft/60">|</span>
          <span>{recs.cached ? "cached 6h" : "fresh"}</span>
        </div>
      )}
    >
      {err && <p className="text-sm text-danger">{err}</p>}
      {loading && <p className="text-sm text-ink-soft">Asking Claude for candidates and scoring them… (first load ~30s)</p>}
      {recs && recs.picks.length === 0 && (
        <p className="text-sm text-ink-soft">
          No picks generated — data provider may be rate-limited, or Claude returned no candidates.
        </p>
      )}
      {recs && recs.picks.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          {recs.picks.map((p) => {
            const c = scoreColor(p.score);
            return (
              <Link
                key={p.ticker}
                href={`/score?ticker=${p.ticker}`}
                className={`rounded-lg border p-2.5 transition-colors ${c.bg} ${c.border} hover:border-brg group`}
              >
                <div className="flex items-baseline justify-between gap-1">
                  <div className="font-bold text-brg-900 text-sm">{p.ticker}</div>
                  <div className={`text-base font-bold tabular-nums ${c.text}`}>
                    {p.score?.toFixed(0)}<span className="text-[9px] opacity-70 ml-0.5">{p.grade}</span>
                  </div>
                </div>
                <div className="mt-0.5 text-[11px] text-ink-muted truncate" title={p.name ?? ""}>{p.name}</div>
                <div className="mt-0.5 text-[10px] text-ink-soft">{p.sector}</div>
                {p.followed_by && p.followed_by.length > 0 && (
                  <div className="mt-1 text-[10px] text-brg font-medium" title={`Held by: ${p.followed_by.join(", ")}`}>
                    ★ followed (+{p.investor_boost?.toFixed(0)})
                  </div>
                )}
                {!p.clears_threshold && (
                  <div className="mt-1 text-[10px] text-danger">below threshold</div>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

/* ───────── Portfolio ───────── */

function PortfolioCard({ profile }: { profile: Profile }) {
  const [p, setP] = useState<Portfolio | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { setP(null); api.getPortfolio(profile.id).then(setP).catch((e) => setErr(e.message)); }, [profile.id]);

  return (
    <SectionCard
      title="Portfolio"
      href="/portfolio"
      subtitle="Track what you actually own. Live prices, P/L, sector weights. Add holdings on the full page."
    >
      {err && <p className="text-sm text-danger">{err}</p>}
      {!p && !err && <p className="text-sm text-ink-soft">Loading…</p>}
      {p && p.n_positions === 0 && (
        <p className="text-sm text-ink-soft">
          No positions yet.{" "}
          <Link href="/portfolio" className="text-brg underline">Add one →</Link>
        </p>
      )}
      {p && p.n_positions > 0 && (
        <>
          {p.n_unvalued === p.n_positions ? (
            <p className="text-sm text-ink-soft">
              Valuation pending — the data provider didn&apos;t return prices this fetch. Try again in a minute.
            </p>
          ) : (
            <div className="flex items-baseline justify-between">
              <div>
                <div className="text-2xl font-bold text-brg-900 tabular-nums">
                  ${p.total_value_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
                <div className="text-[11px] text-ink-soft mt-0.5">
                  {p.n_positions} positions
                  {p.n_unvalued > 0 && <span className="text-danger"> · {p.n_unvalued} unvalued</span>}
                </div>
              </div>
              <div className={`text-right ${p.total_pnl_usd >= 0 ? "text-success" : "text-danger"}`}>
                <div className="text-lg font-semibold tabular-nums">
                  {p.total_pnl_usd >= 0 ? "+" : ""}${p.total_pnl_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
                <div className="text-[11px] tabular-nums">{p.total_pnl_pct >= 0 ? "+" : ""}{p.total_pnl_pct.toFixed(1)}%</div>
              </div>
            </div>
          )}
          <ul className="mt-3 divide-y divide-cream-200 max-h-40 overflow-y-auto">
            {p.holdings.slice(0, 6).map((h) => (
              <li key={h.id} className="py-1.5 flex items-center justify-between text-sm">
                <span className="font-medium w-14">{h.ticker}</span>
                <span className="tabular-nums text-ink-muted flex-1 text-right pr-3">
                  {h.market_value_usd == null ? "—" : `$${h.market_value_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                </span>
                <span className={`tabular-nums w-16 text-right ${(h.pnl_pct ?? 0) >= 0 ? "text-success" : "text-danger"}`}>
                  {h.pnl_pct == null ? "—" : `${h.pnl_pct >= 0 ? "+" : ""}${h.pnl_pct.toFixed(1)}%`}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionCard>
  );
}

/* ───────── News ───────── */

function NewsCard({ profile }: { profile: Profile }) {
  const [items, setItems] = useState<News | null>(null);
  useEffect(() => { setItems(null); api.listNews({ limit: 7, min_impact: 2 }).then(setItems).catch(() => void 0); }, [profile.id]);
  return (
    <SectionCard
      title="Market news"
      href="/news"
      subtitle="High-impact headlines from 12 RSS sources. Claude scores each for sentiment and impact (0–5)."
    >
      {!items && <p className="text-sm text-ink-soft">Loading…</p>}
      {items && items.length === 0 && (
        <p className="text-sm text-ink-soft">Quiet — no flagged headlines yet.</p>
      )}
      <ul className="divide-y divide-cream-200">
        {items?.map((it) => (
          <li key={it.id} className="py-1.5 flex items-start gap-2 text-sm">
            <Dot s={it.sentiment} />
            <a href={it.url} target="_blank" rel="noopener noreferrer" className="flex-1 hover:text-brg line-clamp-2">
              {it.title}
            </a>
            <span className="text-[10px] text-ink-soft whitespace-nowrap mt-0.5">{it.source}</span>
          </li>
        ))}
      </ul>
    </SectionCard>
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

/* ───────── Chat (live, taller) ───────── */

function ChatCard({ profile }: { profile: Profile }) {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([]);
    api.chatHistory(profile.id).then(setMessages).catch(() => void 0);
  }, [profile.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setBusy(true); setErr(null);
    try {
      const r = await api.chat(profile.id, text);
      setMessages((m) => [...m, { role: "assistant", content: r.reply }]);
    } catch (e) {
      setErr((e as Error).message);
      setMessages((m) => m.slice(0, -1));
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    await api.clearChat(profile.id);
    setMessages([]);
  }

  return (
    <SectionCard
      title="Ask the bot"
      href="/chat"
      subtitle="Personal advisor scoped to your profile. It uses real tools — scoring, news, 13F filings, backtests — before answering."
      action={messages.length > 0 && (
        <button onClick={clear} className="text-[11px] text-ink-soft hover:text-danger">clear</button>
      )}
    >
      <div
        ref={scrollRef}
        className="h-[420px] overflow-y-auto rounded-md border border-cream-200 bg-white/50 p-3 space-y-2"
      >
        {messages.length === 0 && !busy && (
          <div className="text-sm text-ink-soft space-y-2">
            <p>Try one of these:</p>
            {[
              "Should I buy NVDA?",
              "What's Buffett's biggest position right now?",
              "Any high-impact news on tech today?",
              "Backtest MSFT over 10 years",
            ].map((q) => (
              <button
                key={q}
                onClick={() => { setInput(q); }}
                className="block w-full text-left rounded-md border border-cream-200 bg-cream-50 px-2.5 py-1.5 text-sm text-ink hover:border-brg hover:text-brg"
              >
                {q}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block max-w-[88%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap text-left ${
              m.role === "user" ? "bg-brg text-cream-50" : "bg-cream-200 text-ink"
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {busy && (
          <div>
            <div className="inline-block rounded-lg bg-cream-200 px-3 py-2 text-sm text-ink-soft animate-pulse">
              thinking…
            </div>
          </div>
        )}
      </div>

      {err && <p className="mt-2 text-xs text-danger">{err}</p>}

      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => { e.preventDefault(); send(); }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          disabled={busy}
          className="flex-1 rounded-md border border-cream-300 bg-white px-3 py-2 text-sm focus:border-brg focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-md bg-brg px-5 py-2 text-sm text-cream-50 hover:bg-brg-800 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </SectionCard>
  );
}

/* ───────── Investors strip (horizontal) ───────── */

function InvestorsStrip({ profile }: { profile: Profile }) {
  const [list, setList] = useState<Investors | null>(null);
  useEffect(() => { api.listInvestors().then(setList).catch(() => void 0); }, []);

  const followed = list?.filter((i) => profile.follow_investors?.includes(i.slug)) ?? [];
  const shown = followed.length > 0 ? followed : (list ?? []).slice(0, 12);

  return (
    <SectionCard
      title="Famous investors"
      href="/investors"
      subtitle="29 hedge fund managers and politicians. Click any to see their latest 13F holdings — live from SEC EDGAR."
    >
      {!list && <p className="text-sm text-ink-soft">Loading…</p>}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {shown.map((i) => (
          <Link
            key={i.slug}
            href={`/investors/${i.slug}`}
            className="shrink-0 w-32 rounded-md border border-cream-300 bg-cream-50 p-2 text-center hover:border-brg"
          >
            {i.photo_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={i.photo_url}
                alt={i.display_name}
                referrerPolicy="no-referrer"
                className="h-16 w-16 mx-auto rounded-full object-cover bg-cream-200"
                onError={(e) => {
                  const img = e.target as HTMLImageElement;
                  img.style.display = "none";
                  img.nextElementSibling?.classList.remove("hidden");
                }}
              />
            ) : null}
            <div className={`h-16 w-16 mx-auto rounded-full bg-cream-200 flex items-center justify-center text-brg text-xl font-semibold ${i.photo_url ? "hidden" : ""}`}>
              {i.display_name.slice(0, 1)}
            </div>
            <div className="mt-1.5 text-xs font-medium text-brg-900 truncate" title={i.display_name}>{i.display_name}</div>
            <div className="text-[10px] text-ink-soft uppercase tracking-wide">{i.kind}</div>
          </Link>
        ))}
      </div>
    </SectionCard>
  );
}
