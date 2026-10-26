#!/usr/bin/env python3
"""Python twin of the site's scScore()/scTop() — keep both in sync.

The JS originals live inline in site/index.html (самопроверка section) and are
contract-tested by site/assets/selfcheck_flag.test.mjs.
"""

from __future__ import annotations

RATIO_W = {"极高": 0, "高": 1, "一般": 2}


def sc_score(entries: list[dict], ans: dict[str, int]) -> list[dict]:
    """Per-section coverage over ANSWERED entries only, ordered by section."""
    m: dict[str, dict] = {}
    for e in entries:
        v = ans.get(e["id"])
        if v is None:
            continue
        r = m.setdefault(e["sec"], {"sec": e["sec"], "total": 0, "yes": 0})
        r["total"] += 1
        if v == 1:
            r["yes"] += 1
    return [m[k] for k in sorted(m, key=lambda s: int(s) if s.isdigit() else 0)]


def sc_top(entries: list[dict], ans: dict[str, int], k: int = 8) -> list[dict]:
    """Unmet (answered "no") entries: best ratio first, then cheapest."""
    unmet = [e for e in entries if ans.get(e["id"]) == 0]
    unmet.sort(
        key=lambda e: (
            RATIO_W.get(e.get("ratio", "一般"), 2),
            e.get("cs", 0),
            int(e["n"]) if str(e.get("n", "")).isdigit() else 0,
        )
    )
    return unmet[:k]
