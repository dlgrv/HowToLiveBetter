#!/usr/bin/env python3
"""Python twin of the site's updMatch() — keep both in sync.

The JS original lives inline in site/index.html (near the filter state block)
and is contract-tested by site/assets/updates_flag.test.mjs.
"""

from __future__ import annotations

import datetime as dt

UPD_DAY_MS = 86_400_000


def upd_match(e: dict, kinds: set[str], days: int, now: int | None = None) -> bool:
    """True if any of `kinds` ('added'/'changed') on entry `e.upd` falls inside the window."""
    upd = e.get("upd")
    if not upd or not kinds:
        return False
    if now is None:
        now = int(dt.datetime.now(tz=dt.UTC).timestamp() * 1000)
    for k in kinds:
        d = upd.get(k)
        if d and now - _parse_ms(d) <= days * UPD_DAY_MS:
            return True
    return False


def _parse_ms(iso_date: str) -> int:
    return int(dt.datetime.fromisoformat(iso_date).replace(tzinfo=dt.UTC).timestamp() * 1000)
