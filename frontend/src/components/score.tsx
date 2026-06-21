"use client";

import type { PillarScore } from "@/lib/api";

/** Traffic-light helpers. Green >= 65, yellow 45-65, red < 45, gray null. */
export function scoreColor(score: number | null): {
  bg: string; text: string; border: string; chip: string;
} {
  if (score === null)
    return { bg: "bg-cream-200/60", text: "text-ink-soft", border: "border-cream-300", chip: "bg-cream-300 text-ink-soft" };
  if (score >= 65)
    return { bg: "bg-success/15", text: "text-success", border: "border-success/40", chip: "bg-success text-cream-50" };
  if (score >= 45)
    return { bg: "bg-gold/20", text: "text-brg-900", border: "border-gold/50", chip: "bg-gold text-brg-900" };
  return { bg: "bg-danger/10", text: "text-danger", border: "border-danger/40", chip: "bg-danger text-cream-50" };
}

export function ScoreBadge({
  score, grade, size = "md",
}: { score: number | null; grade: string; size?: "sm" | "md" | "lg" }) {
  const c = scoreColor(score);
  const cls = size === "lg" ? "px-4 py-2 text-2xl" : size === "sm" ? "px-2 py-1 text-sm" : "px-3 py-1.5 text-xl";
  return (
    <div className={`rounded-lg text-right ${c.chip} ${cls}`}>
      <div className="font-bold tabular-nums leading-none">{score?.toFixed(1) ?? "N/A"}</div>
      {size !== "sm" && <div className="text-[10px] opacity-90">grade {grade}</div>}
    </div>
  );
}

export function PillarBlock({ pillar }: { pillar: PillarScore }) {
  const c = scoreColor(pillar.score);
  return (
    <div className={`rounded-md border p-2 text-center ${c.bg} ${c.border} ${c.text}`}>
      <div className="text-[9px] uppercase tracking-wide opacity-70">{pillar.name}</div>
      <div className="text-lg font-bold tabular-nums">
        {pillar.score === null ? "—" : pillar.score.toFixed(0)}
      </div>
      <div className="text-[9px] opacity-60">w {pillar.weight}</div>
    </div>
  );
}
