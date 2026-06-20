"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Risk, type Timeline } from "@/lib/api";

const RISKS: { value: Risk; label: string; blurb: string }[] = [
  { value: "low",    label: "Low",    blurb: "Sleep well. Slow, steady, boring." },
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
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await api.createProfile({
        name: "Default",
        risk,
        timeline,
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
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-4xl font-semibold tracking-tight text-brg-900">
        Three sliders. Then you&rsquo;re done.
      </h1>
      <p className="mt-3 text-ink-muted">
        Power-user settings live in the dashboard — but you don&rsquo;t need them to start.
      </p>

      <section className="mt-12 space-y-10">
        <Field label="How much are you investing?" hint={`$${capital.toLocaleString()}`}>
          <input
            type="range"
            min={100}
            max={50000}
            step={100}
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            className="w-full accent-[var(--brg-700)]"
          />
          <div className="mt-1 flex justify-between text-xs text-ink-soft">
            <span>$100</span><span>$50,000</span>
          </div>
        </Field>

        <Field label="Risk appetite">
          <Choices
            options={RISKS}
            value={risk}
            onChange={setRisk}
          />
        </Field>

        <Field label="Timeline">
          <Choices
            options={TIMELINES}
            value={timeline}
            onChange={setTimeline}
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
        className="mt-10 inline-flex items-center justify-center rounded-full bg-brg px-7 py-3 text-cream-50 font-medium shadow-sm transition-colors hover:bg-brg-800 disabled:opacity-50"
      >
        {submitting ? "Creating profile…" : "Build my recommendations"}
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
        <label className="text-sm font-medium text-brg-900">{label}</label>
        {hint && <span className="text-sm text-ink-soft tabular-nums">{hint}</span>}
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
            <div className="text-sm font-semibold">{o.label}</div>
            <div className={`mt-1 text-xs ${active ? "text-cream-200" : "text-ink-soft"}`}>
              {o.blurb}
            </div>
          </button>
        );
      })}
    </div>
  );
}
