"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, type InvestorDetail } from "@/lib/api";
import { FollowToggle } from "@/components/followToggle";

export default function InvestorDetailPage() {
  const params = useParams();
  const slug = params?.slug as string;
  const [detail, setDetail] = useState<InvestorDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    api.getInvestor(slug).then(setDetail).catch((e) => setErr((e as Error).message));
  }, [slug]);

  if (err) return <p className="mx-auto max-w-3xl px-6 py-10 text-sm text-danger">{err}</p>;
  if (!detail) return <p className="mx-auto max-w-3xl px-6 py-10 text-sm text-ink-soft">Loading…</p>;

  return (
    <div className="mx-auto max-w-4xl px-6 py-10 space-y-8">
      <Link href="/investors" className="text-sm text-brg hover:underline">
        &larr; Back to investors
      </Link>

      <header className="flex flex-col sm:flex-row gap-6">
        {detail.photo_url ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={detail.photo_url}
            alt={detail.display_name}
            referrerPolicy="no-referrer"
            className="h-40 w-40 rounded-xl object-cover bg-cream-200"
            onError={(e) => {
              const img = e.target as HTMLImageElement;
              img.style.display = "none";
              img.nextElementSibling?.classList.remove("hidden");
            }}
          />
        ) : null}
        <div className={`h-40 w-40 rounded-xl bg-cream-200 flex items-center justify-center text-brg text-5xl font-semibold ${detail.photo_url ? "hidden" : ""}`}>
          {detail.display_name.slice(0, 1)}
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <h1 className="text-3xl font-semibold text-brg-900">{detail.display_name}</h1>
              <div className="mt-1 text-sm text-ink-soft uppercase tracking-wide">{detail.kind}</div>
            </div>
            <FollowToggle slug={detail.slug} />
          </div>
          {detail.description && <p className="mt-3 italic text-ink-muted">{detail.description}</p>}
          {detail.bio && <p className="mt-3 text-sm leading-relaxed">{detail.bio}</p>}
          <p className="mt-3 text-xs text-ink-soft">
            Following adds their top 25 holdings as candidates and gives any matching stock a +6 to +12 boost when scoring for your profile.
          </p>
        </div>
      </header>

      <section>
        <div className="flex items-baseline justify-between border-b border-cream-300 pb-2">
          <h2 className="text-lg font-semibold text-brg-900">
            Latest 13F holdings
          </h2>
          {detail.period && (
            <span className="text-sm text-ink-soft">
              Period {detail.period} · filed {detail.filed}
            </span>
          )}
        </div>

        {detail.holdings_note && (
          <p className="mt-3 text-sm text-ink-muted">{detail.holdings_note}</p>
        )}

        {detail.top_holdings.length > 0 && (
          <>
            <p className="mt-3 text-sm text-ink-soft">
              Total reported portfolio: ${(detail.total_value_usd! / 1e9).toFixed(1)}B
              · {detail.top_holdings.length} top positions
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-ink-soft border-b border-cream-300">
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-3">Security</th>
                    <th className="py-2 pr-3 text-right">Value</th>
                    <th className="py-2 pr-3 text-right">% Book</th>
                    <th className="py-2 pr-3 text-right">Shares</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.top_holdings.map((h, i) => (
                    <tr key={`${h.cusip}-${i}`} className="border-b border-cream-200">
                      <td className="py-2 pr-3 text-ink-soft tabular-nums">{i + 1}</td>
                      <td className="py-2 pr-3 font-medium">{h.name}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {h.value_usd ? `$${(h.value_usd / 1e9).toFixed(2)}B` : "—"}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {h.pct_portfolio?.toFixed(2)}%
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {h.shares ? h.shares.toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
