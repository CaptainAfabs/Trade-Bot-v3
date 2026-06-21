"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Risk, type Timeline } from "@/lib/api";

const RISKS: { value: Risk; label: string; blurb: string }[] = [
  { value: "low",    label: "Low",    blurb: "Sleep well. Slow, steady." },
  { value: "medium", label: "Medium", blurb: "Some swings. Reasonable upside." },
  { value: "high",   label: "High",   blurb: "Volatile. Big upside, real downside." },
];

const TIMELINES: { value: Timeline; label: string; blurb: string }[] = [
  { value: "short",        label: "Short",        blurb: "< 1 year" },
  { value: "medium",       label: "Medium",       blurb: "1 – 5 years" },
  { value: "long",         label: "Long",         blurb: "5 – 20 years" },
  { value: "generational", label: "Generational", blurb: "20+ years" },
];

export default function OnboardPage() {
  const router = useRouter();
  const [capital, setCapital]   = useState(500);
  const [risk, setRisk]         = useState<Risk>("medium");
  const [timeline, setTimeline] = useState<Timeline>("long");
  const [name, setName]         = useState("Default");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existing, setExisting] = useState<{ id: number; name: string }[]>([]);

  useEffect(() => {
    api.listProfiles().then((ps) => setExisting(ps.map((p) => ({ id: p.id, name: p.name }))))
      .catch(() => void 0);
  }, []);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await api.createProfile({
        name: name || "Default",
        risk, timeline,
        capital_usd: capital,
        is_default: true,
      });
      router.push("/dashboard");
    } catch (e) {
      setError((e as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <header className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-brg-900">
          Three answers. Then your dashboard.
        </h1>
        <p className="mt-3 text-ink-muted">
          Tell the bot how much, how brave, and how long. It tunes everything else.
        </p>
        {existing.length > 0 && (
          <p className="mt-2 text-xs text-ink-soft">
            You already have {existing.length} profile{existing.length > 1 ? "s" : ""} ·{" "}
            <a className="text-brg underline" href="/dashboard">jump to dashboard</a>
          </p>
        )}
      </header>

      <section className="mt-12 space-y-10">
        {/* Capital — the hero */}
        <div className="rounded-2xl bg-cream-50 border border-cream-300 p-6">
          <div className="flex items-baseline justify-between">
            <label className="text-sm font-semibold uppercase tracking-wide text-brg">How much are you investing?</label>
            <span className="text-xs text-ink-soft">USD</span>
          </div>

          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-5xl font-bold text-brg-900 tabular-nums">$</span>
            <input
              type="text"
              inputMode="numeric"
              value={capital.toLocaleString()}
              onChange={(e) => {
                const n = Number(e.target.value.replace(/[^0-9]/g, ""));
                if (!isNaN(n)) setCapital(Math.min(Math.max(n, 0), 5_000_000));
              }}
              className="w-full bg-transparent text-5xl font-bold text-brg-900 tabular-nums outline-none focus:text-brg-700"
              aria-label="Investment amount in dollars"
            />
          </div>

          <input
            type="range"
            min={100}
            max={50000}
            step={100}
            value={Math.min(capital, 50000)}
            onChange={(e) => setCapital(Number(e.target.value))}
            className="mt-4 w-full accent-[var(--brg-700)]"
          />
          <div className="mt-1 flex justify-between text-xs text-ink-soft">
            <span>$100</span>
            <span>$10k</span>
            <span>$25k</span>
            <span>$50k+</span>
          </div>
          <p className="mt-2 text-xs text-ink-soft">
            Slider stops at $50k for fast picking — type any number above for larger accounts.
          </p>
        </div>

        <Field label="Risk appetite">
          <Choices options={RISKS} value={risk} onChange={setRisk} />
        </Field>

        <Field label="Timeline">
          <Choices options={TIMELINES} value={timeline} onChange={setTimeline} />
        </Field>

        <Field label="Profile name (optional)" hint="So you can have multiple strategies later">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={40}
            className="w-full rounded-md border border-cream-300 bg-white px-4 py-2.5 text-base focus:border-brg focus:outline-none"
            placeholder="e.g. Aggressive TFSA"
          />
        </Field>
      </section>

      {error && (
        <div className="mt-6 rounded-md border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          {error}
        </div>
      )}

      <button
        onClick={submit}
        disabled={submitting}
        className="mt-10 w-full sm:w-auto inline-flex items-center justify-center rounded-full bg-brg px-8 py-3.5 text-cream-50 font-medium shadow-sm transition-colors hover:bg-brg-800 disabled:opacity-50"
      >
        {submitting ? "Saving profile…" : "Save profile & see recommendations →"}
      </button>
    </div>
  );
}

function Field({
  label, hint, children,
}: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-semibold uppercase tracking-wide text-brg">{label}</label>
        {hint && <span className="text-xs text-ink-soft">{hint}</span>}
      </div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function Choices<T extends string>({
  options, value, onChange,
}: {
  options: { value: T; label: string; blurb: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={`text-left rounded-xl border p-4 transition-colors ${
              active
                ? "border-brg bg-brg text-cream-50"
                : "border-cream-300 bg-cream-50 hover:border-brg-400"
            }`}
          >
            <div className="text-base font-semibold">{o.label}</div>
            <div className={`mt-1 text-xs ${active ? "text-cream-200" : "text-ink-soft"}`}>
              {o.blurb}
            </div>
          </button>
        );
      })}
    </div>
  );
}
