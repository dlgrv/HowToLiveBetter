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
