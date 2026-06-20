"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Profile } from "@/lib/api";

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProfiles().then(setProfiles).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-brg-900">Dashboard</h1>
        <Link
          href="/"
          className="text-sm text-brg hover:underline"
        >
          + New profile
        </Link>
      </div>

      {error && (
        <p className="mt-6 text-sm text-danger">
          Backend unreachable — start it with{" "}
          <code className="rounded bg-cream-200 px-1.5 py-0.5">uvicorn app.main:app --reload</code>.
          ({error})
        </p>
      )}

      {profiles && profiles.length === 0 && (
        <div className="mt-10 rounded-xl border border-cream-300 bg-cream-50 p-8 text-center">
          <p className="text-ink-muted">No profile yet.</p>
          <Link
            href="/"
            className="mt-4 inline-block rounded-full bg-brg px-5 py-2 text-cream-50"
          >
            Start onboarding
          </Link>
        </div>
      )}

      {profiles && profiles.length > 0 && (
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {profiles.map((p) => (
            <ProfileCard key={p.id} profile={p} />
          ))}
        </div>
      )}

      <section className="mt-12 rounded-xl border border-cream-300 bg-cream-50 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-brg">
          Coming online over the next 6 days
        </h2>
        <ul className="mt-3 list-disc pl-5 text-sm text-ink-muted space-y-1">
          <li>Day 2 — 30+ quant ratios across every US ticker</li>
          <li>Day 3 — Risk- and timeline-weighted scoring</li>
          <li>Day 4 — Famous-investor + Congress tracking</li>
          <li>Day 5 — News pipeline, Claude chat, backtest</li>
          <li>Day 6 — Daily email digest, portfolio, monthly journal</li>
          <li>Day 7 — Polish + Apple/Power mode toggle</li>
        </ul>
      </section>
    </div>
  );
}

function ProfileCard({ profile: p }: { profile: Profile }) {
  return (
    <div className="rounded-xl border border-cream-300 bg-cream-50 p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold text-brg-900">{p.name}</h3>
        {p.is_default && (
          <span className="rounded-full bg-brg px-2 py-0.5 text-xs text-cream-50">
            default
          </span>
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
