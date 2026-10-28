"""Open retrieval adapter.

The v0.1 core binary deliberately focuses on reasoning (plan/reason/verify);
retrieval stays in the open framework so it can be swapped (Bing RSS, an
internal index, a robot's local knowledge base). No API key, no telemetry.
"""
from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request
from typing import Any
from xml.etree import ElementTree as ET

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def search(query: str, limit: int = 5, timeout: float = 6.0) -> dict[str, Any]:
    """Bing RSS (no key). Returns ``{"items": [...], "errors": [...]}``."""
    q = (query or "").strip()
    if not q:
        return {"items": [], "errors": ["empty_query"]}
    url = (f"https://cn.bing.com/search?q={urllib.parse.quote(q)}"
           f"&format=rss&count={max(5, limit)}&setlang=zh-hans")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        raw = urllib.request.urlopen(req, timeout=timeout, context=_ctx()).read()
    except Exception as exc:  # noqa: BLE001
        return {"items": [], "errors": [f"{type(exc).__name__}: {exc}"]}
    try:
        root = ET.fromstring(raw)
    except Exception as exc:  # noqa: BLE001
        return {"items": [], "errors": [f"xml: {exc}"]}
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = re.sub(r"<[^>]+>", "", item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title:
            items.append({"title": title, "snippet": desc[:400], "source": link})
        if len(items) >= limit:
            break
    return {"items": items, "errors": []}
