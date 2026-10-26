"""Chip-checkbox contract: filter chips render a check square in both skins.

Pure CSS on .chip + [aria-pressed] (synced by syncControls), so the test
only asserts both shipped stylesheets carry the ::before box, the checked
rule, and the checkmark svg — enough to catch a dropped restyle.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _has_chip_checkbox(css: str) -> bool:
    return (
        ".chip::before" in css
        and bool(re.search(r'\.chip\[aria-pressed="true"\]::before', css))
        and "M20 6 9 17l-5-5" in css  # checkmark path
        and "border-radius" in css
    )


def test_v2_skin_chips_have_checkbox():
    css = (ROOT / "forge/v2.css").read_text(encoding="utf-8")
    assert _has_chip_checkbox(css), "v2.css lost the chip checkbox styling"
    # dark-mode check uses the inverted stroke, same as .toggle input:checked
    assert 'html.dark .chip[aria-pressed="true"]::before' in css


def test_v1_skin_chips_have_checkbox():
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    assert _has_chip_checkbox(html), "site/index.html lost the chip checkbox styling"


def _has_disclosure_markers(css: str) -> bool:
    return (
        ".src summary::before" in css
        and ".src[open] summary::before" in css
        and ".card-expand::before" in css
        and ".card.expanded .card-expand::before{transform:rotate(45deg)}" in css
    )


def _has_useful_bookmark(css: str) -> bool:
    return (
        ".htlb-useful::before" in css
        and "mask-image" in css
        and "m19 21-7-4-7 4V5" in css  # bookmark path
        and bool(re.search(r'\.htlb-useful\[aria-pressed="true"\]::before', css))
        and "fill='black' stroke='black'" in css  # pressed = filled bookmark
    )


def test_v2_skin_disclosure_and_useful():
    css = (ROOT / "forge/v2.css").read_text(encoding="utf-8")
    assert _has_disclosure_markers(css), "v2.css lost the summary/expand carets"
    assert _has_useful_bookmark(css), "v2.css lost the useful bookmark icon"


def test_v1_skin_disclosure_and_useful():
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    assert _has_disclosure_markers(html), "site/index.html lost the summary/expand carets"
    assert _has_useful_bookmark(html), "site/index.html lost the useful bookmark icon"
