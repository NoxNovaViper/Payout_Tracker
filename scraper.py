#!/usr/bin/env python3
"""
The Ledger — auto-refresh scraper
----------------------------------
Scans public news coverage (via Google News RSS, no API key required) for
recent mentions of police-misconduct settlements, and appends candidates to
pending.json for human review.

Deliberately does NOT write to data.json directly. Dollar amounts attached
to a real person's name are a "verify before you publish" situation, not a
"trust the regex" situation — headlines round numbers, conflate proposed vs.
approved settlements, and sometimes are just wrong. This script's job is to
surface candidates fast, not to be the final word.

Run it however you like. The bundled GitHub Actions workflow
(.github/workflows/update-data.yml) runs it automatically every 12 hours
with zero paid services and zero dependency on this script's author.
Only Python's standard library is used, so no `pip install` step is needed.
"""

import datetime
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DATA_FILE = "data.json"
PENDING_FILE = "pending.json"
USER_AGENT = "Mozilla/5.0 (compatible; TheLedgerBot/1.0; +https://github.com/)"

# Search queries cast a wide net across the common phrasings newsrooms use
# for this story. Add/remove queries here to tune what the crawler looks for.
QUERIES = [
    "police settlement million lawsuit",
    "city council approves police misconduct settlement",
    "wrongful conviction settlement police million",
    "police shooting settlement family million",
    "police department pays settlement civil rights",
    "wrongful arrest settlement police million",
    "police custody death settlement million",
]

AMOUNT_RE = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s?(million|billion|M|B)?",
    re.IGNORECASE,
)

RELEVANT_KEYWORDS = ["police", "officer", "sheriff", "deputy", "department"]
SETTLEMENT_KEYWORDS = [
    "settlement", "settle", "settled", "payout", "agreed to pay",
    "lawsuit", "wrongful", "council approved", "approves",
]


def fetch_rss(query: str) -> bytes:
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def parse_items(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall(".//item"):
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "pubDate": (item.findtext("pubDate") or "").strip(),
            "description": (item.findtext("description") or "").strip(),
        })
    return items


def extract_amount(text: str):
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit.startswith("b"):
        num *= 1_000_000_000
    elif unit.startswith("m"):
        num *= 1_000_000
    elif num < 1000:
        # A bare "$X" with no unit and a small number is almost never a
        # settlement headline figure — skip it rather than guess.
        return None
    return int(num)


def looks_relevant(text: str) -> bool:
    t = text.lower()
    return (
        any(k in t for k in RELEVANT_KEYWORDS)
        and any(k in t for k in SETTLEMENT_KEYWORDS)
    )


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    data = load_json(DATA_FILE, {"generated_at": "", "cases": []})
    pending = load_json(PENDING_FILE, [])

    known_links = set()
    for c in data.get("cases", []):
        if c.get("source_url"):
            known_links.add(c["source_url"])
    for p in pending:
        if p.get("source_url"):
            known_links.add(p["source_url"])

    added = 0
    for query in QUERIES:
        try:
            items = parse_items(fetch_rss(query))
        except Exception as exc:  # network hiccups shouldn't kill the run
            print(f"[warn] query failed: {query!r} ({exc})")
            continue

        for item in items:
            link = item["link"]
            if not link or link in known_links:
                continue

            blob = f'{item["title"]} {item["description"]}'
            if not looks_relevant(blob):
                continue

            amount = extract_amount(blob)
            if amount is None or amount < 50_000:
                continue

            known_links.add(link)
            pending.append({
                "id": hashlib.sha1(link.encode()).hexdigest()[:10],
                "headline": item["title"],
                "detected_amount": amount,
                "source_url": link,
                "published": item["pubDate"],
                "matched_query": query,
                "status": "needs_review",
                "detected_at": datetime.datetime.utcnow().isoformat() + "Z",
            })
            added += 1

        time.sleep(1)  # be polite to the feed

    save_json(PENDING_FILE, pending)
    print(f"Scan complete. {added} new candidate(s) added to {PENDING_FILE}.")
    print(f"{len(pending)} total candidate(s) awaiting review.")


if __name__ == "__main__":
    main()
