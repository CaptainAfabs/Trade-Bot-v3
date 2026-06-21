"""SEC EDGAR adapter. Free, official, no API key — but requires a real User-Agent
header (sec.gov rule). Fetches the latest 13F-HR for a given CIK and parses the
holdings information table (XML).

13F filings disclose long equity positions for institutional managers > $100M AUM,
filed within 45 days of quarter end. Schedule for 2026: Feb 17, May 15, Aug 14, Nov 16.
"""
from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from .cache import DiskCache

_cache = DiskCache("edgar")
TIMEOUT = 20.0

# SEC requires a descriptive User-Agent with contact info.
_HEADERS = {
    "User-Agent": "stock-advisor (personal-use; adamfabiano18@gmail.com)",
    "Accept-Encoding": "gzip, deflate",
}


def _pad_cik(cik: str) -> str:
    """Pad to 10 digits, strip CIK prefix if present."""
    s = re.sub(r"^CIK", "", str(cik), flags=re.IGNORECASE).lstrip("0")
    return s.zfill(10)


def get_recent_filings(cik: str) -> dict | None:
    """Pulls the submissions index for a CIK. Returns the JSON blob."""
    cik10 = _pad_cik(cik)
    key = f"sub_{cik10}"
    cached = _cache.get(key, ttl_seconds=3600)
    if cached is not None:
        return cached
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    try:
        r = httpx.get(url, headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    _cache.set(key, data)
    return data


def latest_13f_accession(cik: str) -> tuple[str, str, str] | None:
    """Return (accession_number, filing_date, report_date) for most recent 13F-HR."""
    subs = get_recent_filings(cik)
    if not subs:
        return None
    recent = subs.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    for i, form in enumerate(forms):
        if form == "13F-HR":
            return accessions[i], filing_dates[i], report_dates[i]
    return None


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _parse_info_table(xml_text: str, value_is_thousands: bool) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for info in root.iter():
        if _strip_ns(info.tag) != "infoTable":
            continue
        h: dict[str, Any] = {}
        for child in info:
            tag = _strip_ns(child.tag)
            if tag == "nameOfIssuer":
                h["name"] = (child.text or "").strip()
            elif tag == "cusip":
                h["cusip"] = (child.text or "").strip().upper()
            elif tag == "value":
                try:
                    v = int(child.text or 0)
                    h["value_usd"] = v * 1000 if value_is_thousands else v
                except (TypeError, ValueError):
                    h["value_usd"] = None
            elif tag == "shrsOrPrnAmt":
                for c in child:
                    if _strip_ns(c.tag) == "sshPrnamt":
                        try:
                            h["shares"] = int(c.text or 0)
                        except (TypeError, ValueError):
                            h["shares"] = None
            elif tag == "titleOfClass":
                h["class"] = (child.text or "").strip()
        if h.get("name"):
            rows.append(h)
    return rows


def _aggregate_by_cusip(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Multiple sub-advisors in one 13F report each holding separately. Sum by cusip."""
    by_key: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = r.get("cusip") or r.get("name") or ""
        if not key:
            continue
        if key not in by_key:
            by_key[key] = {
                "name": r.get("name"),
                "cusip": r.get("cusip"),
                "class": r.get("class"),
                "value_usd": 0,
                "shares": 0,
            }
        agg = by_key[key]
        agg["value_usd"] = (agg["value_usd"] or 0) + (r.get("value_usd") or 0)
        agg["shares"]    = (agg["shares"] or 0)    + (r.get("shares") or 0)
    return list(by_key.values())


def fetch_13f_holdings(cik: str) -> dict | None:
    """Fetch + parse the latest 13F-HR for a CIK.
    Aggregates across all info tables and sub-advisors, dedupes by CUSIP.
    Returns {period, filed, accession, total_value_usd, holdings: [...]}
    """
    latest = latest_13f_accession(cik)
    if not latest:
        return None
    accession, filed, report = latest
    cik10 = _pad_cik(cik)
    acc_nodash = accession.replace("-", "")

    cache_key = f"13f_{cik10}_{accession}"
    cached = _cache.get(cache_key, ttl_seconds=86400)
    if cached is not None:
        return cached

    # SEC filings switched 13F value reporting from thousands to dollars in 2022Q3.
    # Use the report date as the cutoff signal.
    year = int(report.split("-")[0]) if report else 2026
    value_is_thousands = year < 2023

    dir_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{acc_nodash}/"
    try:
        r = httpx.get(dir_url, headers=_HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception:
        return None
    xml_hrefs = re.findall(r'href="([^"]+\.xml)"', r.text, flags=re.IGNORECASE)

    all_rows: list[dict[str, Any]] = []
    for href in xml_hrefs:
        lower = href.lower()
        # Skip the cover-page and form metadata — only parse info tables
        if "primary_doc" in lower or "form13fhr" in lower or "form_13f" in lower or "metalinks" in lower:
            continue
        url = href if href.startswith("http") else "https://www.sec.gov" + href
        try:
            x = httpx.get(url, headers=_HEADERS, timeout=TIMEOUT)
            x.raise_for_status()
        except Exception:
            continue
        rows = _parse_info_table(x.text, value_is_thousands=value_is_thousands)
        all_rows.extend(rows)

    if not all_rows:
        return None

    aggregated = _aggregate_by_cusip(all_rows)
    total_value = sum(h.get("value_usd") or 0 for h in aggregated)
    aggregated.sort(key=lambda h: h.get("value_usd") or 0, reverse=True)
    for h in aggregated:
        v = h.get("value_usd") or 0
        h["pct_portfolio"] = round(v / total_value * 100, 3) if total_value else None

    out = {
        "period": report,
        "filed": filed,
        "accession": accession,
        "total_value_usd": total_value,
        "holdings": aggregated,
    }
    _cache.set(cache_key, out)
    return out
