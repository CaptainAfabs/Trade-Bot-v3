"use client";

import { useEffect, useState } from "react";
import { api, type Profile } from "@/lib/api";

/** Reusable button: shows "Follow" or "Following ✓", toggles via API.
 * Loads the active profile on mount and reads its follow_investors list.
 */
export function FollowToggle({
  slug, size = "md",
}: { slug: string; size?: "sm" | "md" }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listProfiles().then((ps) => {
      setProfile(ps.find((p) => p.is_default) ?? ps[0] ?? null);
    });
  }, []);

  const following = profile?.follow_investors?.includes(slug) ?? false;

  async function toggle() {
    if (!profile || busy) return;
    setBusy(true);
    try {
      const updated = following
        ? await api.unfollowInvestor(profile.id, slug)
        : await api.followInvestor(profile.id, slug);
      setProfile(updated);
    } finally {
      setBusy(false);
    }
  }

  const cls = size === "sm"
    ? "px-2 py-0.5 text-xs"
    : "px-3 py-1.5 text-sm";

  if (!profile) {
    return <button disabled className={`rounded-md border border-cream-300 bg-cream-50 text-ink-soft ${cls}`}>…</button>;
  }

  return (
    <button
      onClick={toggle}
      disabled={busy}
      className={`rounded-md font-medium transition-colors ${cls} ${
        following
          ? "bg-brg text-cream-50 hover:bg-brg-800"
          : "border border-brg bg-cream-50 text-brg hover:bg-brg/10"
      }`}
    >
      {busy ? "…" : following ? "Following ✓" : "+ Follow"}
    </button>
  );
}
