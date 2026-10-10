"""Interactive useful/account wiring must stay connected.

Regression: cards lived in ``let CARDS`` (not a window property), while
``interactive.js`` read ``window.CARDS`` and short-circuited — Useful /
Bookmark bars never appeared on book.dlgrv.com even though the API and
script were deployed.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from translate.lib.config import default_root

ROOT = Path(default_root())
INDEX = ROOT / "site" / "index.html"
INTERACTIVE = ROOT / "site" / "assets" / "interactive.js"
EN_INDEX = ROOT / "site" / "en" / "index.html"


class TestIndexInteractiveWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = INDEX.read_text(encoding="utf-8")

    def test_exposes_cards_on_window_before_ready(self):
        """let/const CARDS are invisible to other scripts — must assign window.CARDS."""
        m = re.search(
            r"window\.CARDS\s*=\s*CARDS\s*;\s*"
            r"try\s*\{\s*dispatchEvent\(\s*new Event\('htlb:ready'\)\s*\)",
            self.text,
        )
        self.assertIsNotNone(
            m,
            "boot must set window.CARDS = CARDS immediately before dispatching htlb:ready",
        )

    def test_declares_cards_with_let(self):
        # Document the hazard: let is fine only if window.CARDS is assigned later.
        self.assertRegex(self.text, r"\blet CARDS\s*=")

    def test_loads_interactive_after_api_globals(self):
        api = self.text.find("__HTLB_API__")
        script = self.text.find('src="assets/interactive.js"')
        self.assertGreater(api, 0)
        self.assertGreater(script, api, "interactive.js must load after __HTLB_API__ globals")

    def test_account_slot_present(self):
        self.assertIn('id="account"', self.text)
        self.assertIn('id="account-menu"', self.text)


class TestInteractiveJsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = INTERACTIVE.read_text(encoding="utf-8")

    def test_enhance_cards_reads_window_cards(self):
        self.assertRegex(
            self.text,
            r"function enhanceCards\(\)\s*\{\s*var cards = window\.CARDS;",
            "enhanceCards must read window.CARDS into a local (bare CARDS is undefined across scripts)",
        )

    def test_no_bare_cards_short_circuit(self):
        # Old bug: if (!window.CARDS || !CARDS.length) — second operand never ran, but
        # the intent relied on a global CARDS that let never created.
        bad = re.search(r"!window\.CARDS\s*\|\|\s*!CARDS\.length", self.text)
        self.assertIsNone(bad, "do not short-circuit with bare CARDS.length")

    def test_host_gate_allows_book_and_local(self):
        for host in ("book.dlgrv.com", "127.0.0.1", "localhost"):
            self.assertIn(host, self.text)

    def test_listens_for_htlb_ready(self):
        self.assertIn("addEventListener('htlb:ready'", self.text)
        self.assertIn("enhanceCards();", self.text)

    def test_useful_and_bookmark_endpoints(self):
        self.assertIn("api('/useful'", self.text)

    def test_useful_inserted_after_sources(self):
        self.assertIn("details.src", self.text)
        self.assertIn("htlb-useful", self.text)
        self.assertNotRegex(
            self.text,
            r"insertBefore\(bar,\s*title\.nextSibling\)",
            "Useful must sit after Sources, not under the title",
        )


class TestBuiltLocaleKeepsWiring(unittest.TestCase):
    def test_en_page_exposes_cards_before_ready(self):
        self.assertTrue(EN_INDEX.is_file(), "site/en/index.html missing — run build_pages")
        text = EN_INDEX.read_text(encoding="utf-8")
        m = re.search(
            r"window\.CARDS\s*=\s*CARDS\s*;\s*"
            r"try\s*\{\s*dispatchEvent\(\s*new Event\('htlb:ready'\)\s*\)",
            text,
        )
        self.assertIsNotNone(m, "built en page must keep window.CARDS + htlb:ready wiring")
        self.assertIn('src="../assets/interactive.js"', text)


if __name__ == "__main__":
    unittest.main()
