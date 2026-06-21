"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, type Profile } from "@/lib/api";

export default function ChatPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listProfiles().then((ps) => {
      const p = ps.find((x) => x.is_default) ?? ps[0] ?? null;
      setProfile(p);
      if (p) api.chatHistory(p.id).then(setMessages);
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send() {
    if (!profile) return;
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
    if (!profile) return;
    await api.clearChat(profile.id);
    setMessages([]);
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 space-y-4 flex flex-col h-[calc(100vh-100px)]">
      <div className="flex items-baseline justify-between">
        <div>
          <Link href="/dashboard" className="text-sm text-brg hover:underline">&larr; Dashboard</Link>
          <h1 className="mt-1 text-2xl font-semibold text-brg-900">Chat with the bot</h1>
          {profile && (
            <p className="text-sm text-ink-muted">
              Scoped to <strong>{profile.name}</strong> · {profile.risk} risk · {profile.timeline} timeline
            </p>
          )}
        </div>
        {messages.length > 0 && (
          <button onClick={clear} className="text-sm text-ink-soft hover:text-danger">
            Clear conversation
          </button>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded-2xl border border-cream-300 bg-cream-50 p-4 space-y-3"
      >
        {messages.length === 0 && (
          <div className="text-sm text-ink-soft">
            Try: <em>&ldquo;Should I buy NVDA?&rdquo;</em> · <em>&ldquo;What&apos;s Buffett&apos;s biggest position?&rdquo;</em>{" "}
            · <em>&ldquo;Any high-impact news on tech today?&rdquo;</em> · <em>&ldquo;Backtest MSFT over 10 years&rdquo;</em>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap text-left ${
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

      {err && <p className="text-xs text-danger">{err}</p>}

      <form
        className="flex gap-2"
        onSubmit={(e) => { e.preventDefault(); send(); }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          disabled={busy}
          className="flex-1 rounded-md border border-cream-300 bg-white px-4 py-2.5 text-sm focus:border-brg focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim() || !profile}
          className="rounded-md bg-brg px-6 py-2.5 text-sm text-cream-50 hover:bg-brg-800 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
