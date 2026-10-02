"""Twin of resume-reading helpers in site/index.html.

Keep algorithms in sync with the JS block marked
「resume reading position (sessionStorage)」.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

POS_KEY_PREFIX = "htlb-pos:"
TOP_CLEAR_PX = 12.0
NAV_PAD_PX = 24.0
DEFAULT_NAV_H = 56.0


def pos_key(lang: str) -> str:
    return f"{POS_KEY_PREFIX}{lang}"


def pos_nav_offset(nav_h: float | None, *, pad: float = NAV_PAD_PX) -> float:
    """Mirror JS: parseFloat(--nav-h) or 56, then + 24."""
    if nav_h is None or not math.isfinite(nav_h):
        return DEFAULT_NAV_H + pad
    return float(nav_h) + pad


def parse_nav_h_css(raw: str) -> float | None:
    """Like JS parseFloat on getComputedStyle('--nav-h')."""
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.match(r"^[-+]?(?:\d+\.?\d*|\.\d+)", raw)
    if not m:
        return None
    return float(m.group(0))


@dataclass(frozen=True)
class CardGeom:
    """One card for pick_current_pos_id."""

    id: str
    top: float  # getBoundingClientRect().top
    hidden: bool


def pick_current_pos_id(
    cards: list[CardGeom],
    *,
    limit: float,
    scroll_y: float,
    top_clear: float = TOP_CLEAR_PX,
) -> str | None:
    """Id to persist, or None meaning clear storage (at top / nothing qualifies)."""
    if scroll_y < top_clear:
        return None
    best: str | None = None
    best_top = float("-inf")
    for c in cards:
        if c.hidden or not c.id:
            continue
        if c.top <= limit and c.top >= best_top:
            best_top = c.top
            best = c.id
    return best


@dataclass(frozen=True)
class TargetState:
    """Visibility of a restore candidate."""

    exists: bool
    hidden: bool = False
    block_hidden: bool = False

    @property
    def visible(self) -> bool:
        return self.exists and not self.hidden and not self.block_hidden


def parse_hash_id(location_hash: str) -> str | None:
    """location.hash including leading '#'; empty / '#' alone → None."""
    h = location_hash or ""
    if not h.startswith("#"):
        return None
    frag = h[1:]
    return frag or None


def resolve_restore_id(
    location_hash: str,
    stored_id: str | None,
    lookup: dict[str, TargetState],
) -> str | None:
    """Which card id to scroll to.

    Explicit hash wins when its target is visible. If the hash target is
    missing or hidden, fall through to sessionStorage (same visibility rules).
    """
    hid = parse_hash_id(location_hash)
    if hid is not None:
        st = lookup.get(hid)
        if st is not None and st.visible:
            return hid
        # missing / hidden hash → try storage below
    if stored_id:
        st = lookup.get(stored_id)
        if st is not None and st.visible:
            return stored_id
    return None
