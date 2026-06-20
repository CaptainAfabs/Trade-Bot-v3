"""Thin Anthropic client wrapper. Used by investor-add (Day 4) and chat (Day 5)."""
from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from app.config import settings

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def complete(system: str, user: str, model: str | None = None, max_tokens: int = 1024) -> str:
    msg = client().messages.create(
        model=model or settings.claude_bulk_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = []
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def complete_json(system: str, user: str, model: str | None = None, max_tokens: int = 1024) -> dict[str, Any]:
    """Parse the first JSON object out of Claude's response."""
    txt = complete(system, user, model=model, max_tokens=max_tokens)
    # Strip ```json fences if present
    if "```" in txt:
        chunks = txt.split("```")
        for c in chunks:
            c = c.strip()
            if c.startswith("json"):
                c = c[4:].strip()
            if c.startswith("{") or c.startswith("["):
                txt = c
                break
    start = txt.find("{")
    end = txt.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in response: {txt[:200]}")
    return json.loads(txt[start:end + 1])
