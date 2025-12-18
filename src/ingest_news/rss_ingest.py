import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

import feedparser
import yaml


def load_sources(config_path: str) -> Dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _hash_entry(title: str, url: str) -> str:
    h = hashlib.sha256()
    h.update((title or "").encode("utf-8"))
    h.update((url or "").encode("utf-8"))
    return h.hexdigest()


def fetch_and_normalize(
    sources: List[Dict],
    include_keywords: Optional[List[str]] = None,
    exclude_keywords: Optional[List[str]] = None,
    log_path: Optional[str] = None,
) -> List[Dict]:
    include_keywords = include_keywords or []
    exclude_keywords = exclude_keywords or []
    seen = set()
    results = []

    for src in sources:
        url = src.get("url")
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = _clean_text(entry.get("title", ""))
            summary = _clean_text(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")
            ts = entry.get("published", entry.get("updated", ""))

            if not title:
                continue

            text_blob = f"{title} {summary}".lower()
            if include_keywords and not any(k.lower() in text_blob for k in include_keywords):
                continue
            if any(k.lower() in text_blob for k in exclude_keywords):
                continue

            dedup_key = _hash_entry(title, link)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            results.append(
                {
                    "title": title,
                    "body": summary,
                    "ts": _to_iso(ts),
                    "source": src.get("name", "rss"),
                    "url": link,
                }
            )

    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def _to_iso(ts: str) -> str:
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(ts)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(tz=timezone.utc).isoformat()
