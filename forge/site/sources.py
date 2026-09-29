"""Twin of splitSources / srcCount in site/index.html.

Keep this algorithm in sync with the JS helpers — badge count must equal
the expanded source list length.
"""

from __future__ import annotations

import re

_URL_RE = re.compile(r"<https?://[^>\s]+>|https?://[^\s；;>]+")


def split_sources(s: str | None) -> list[str]:
    """Split a Sources field into display rows (one per URL when URLs exist)."""
    s = s or ""
    matches = list(_URL_RE.finditer(s))
    if matches:
        parts: list[str] = []
        start = 0
        for m in matches:
            chunk = s[start : m.end()].strip().lstrip("；;").strip()
            if chunk:
                parts.append(chunk)
            start = m.end()
        trail = s[start:].strip().lstrip("；;").strip()
        if trail:
            parts.append(trail)
        return parts
    # No URLs: fullwidth ； only (ASCII ; is common inside citations).
    return [p.strip() for p in re.split(r"\s*；\s*", s) if p.strip()]


def src_count(s: str | None) -> int:
    return len(split_sources(s))
