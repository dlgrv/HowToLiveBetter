#!/usr/bin/env python3
"""Python twin of the site's sitMatch()/SITUATIONS — keep both in sync.

The JS original lives inline in site/index.html; age chapter lists are a
first draft (marked TUNE there) — change both files together.
"""

from __future__ import annotations

SITUATIONS = {
    "age": {
        "35": ["05", "15", "16", "18", "19", "24", "26", "32"],
        "60": ["16", "17", "24", "25", "33"],
    },
}


def sit_match(e: dict, tags: set[str]) -> bool:
    for t in tags:
        if t == "free" and e.get("money") == "0":
            return True
        if t == "d30" and e.get("time") == "少" and e.get("will") == "否":
            return True
        if t in ("35", "60") and e.get("sec") in SITUATIONS["age"][t]:
            return True
    return False
