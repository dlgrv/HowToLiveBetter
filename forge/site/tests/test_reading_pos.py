"""Tests for forge.site.reading_pos (twin of site/index.html resume helpers)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from translate.lib.config import default_root

from forge.site.reading_pos import (
    CardGeom,
    TargetState,
    parse_hash_id,
    parse_nav_h_css,
    pick_current_pos_id,
    pos_key,
    pos_nav_offset,
    resolve_restore_id,
)

ROOT = Path(default_root())
INDEX = ROOT / "site" / "index.html"


class TestPosKey(unittest.TestCase):
    def test_lang_scoped(self):
        self.assertEqual(pos_key("ru"), "htlb-pos:ru")
        self.assertEqual(pos_key("en"), "htlb-pos:en")
        self.assertNotEqual(pos_key("ru"), pos_key("en"))


class TestNavOffset(unittest.TestCase):
    def test_default_when_none(self):
        self.assertEqual(pos_nav_offset(None), 80.0)

    def test_nan_and_inf_use_default(self):
        self.assertEqual(pos_nav_offset(float("nan")), 80.0)
        self.assertEqual(pos_nav_offset(float("inf")), 80.0)

    def test_css_px_value(self):
        self.assertEqual(pos_nav_offset(56.0), 80.0)
        self.assertEqual(pos_nav_offset(parse_nav_h_css("56px")), 80.0)

    def test_parse_nav_h_empty(self):
        self.assertIsNone(parse_nav_h_css(""))
        self.assertIsNone(parse_nav_h_css("   "))


class TestPickCurrentPosId(unittest.TestCase):
    def setUp(self):
        self.limit = 80.0
        self.cards = [
            CardGeom("e-1-1", top=200, hidden=False),
            CardGeom("e-1-2", top=40, hidden=False),
            CardGeom("e-1-3", top=-10, hidden=False),
            CardGeom("e-1-4", top=90, hidden=False),
        ]

    def test_clears_near_page_top(self):
        self.assertIsNone(pick_current_pos_id(self.cards, limit=self.limit, scroll_y=0))
        self.assertIsNone(pick_current_pos_id(self.cards, limit=self.limit, scroll_y=11.9))

    def test_picks_closest_below_limit(self):
        # e-1-2 (40) and e-1-3 (-10) qualify; prefer larger top → e-1-2
        self.assertEqual(
            pick_current_pos_id(self.cards, limit=self.limit, scroll_y=100),
            "e-1-2",
        )

    def test_long_card_still_above_viewport(self):
        cards = [
            CardGeom("e-2-1", top=-400, hidden=False),
            CardGeom("e-2-2", top=120, hidden=False),
        ]
        self.assertEqual(
            pick_current_pos_id(cards, limit=self.limit, scroll_y=500),
            "e-2-1",
        )

    def test_skips_hidden(self):
        cards = [
            CardGeom("e-1-2", top=40, hidden=True),
            CardGeom("e-1-3", top=-10, hidden=False),
        ]
        self.assertEqual(
            pick_current_pos_id(cards, limit=self.limit, scroll_y=100),
            "e-1-3",
        )

    def test_nothing_qualifies_clears(self):
        cards = [CardGeom("e-1-1", top=200, hidden=False)]
        self.assertIsNone(pick_current_pos_id(cards, limit=self.limit, scroll_y=50))

    def test_skips_empty_id(self):
        cards = [CardGeom("", top=10, hidden=False)]
        self.assertIsNone(pick_current_pos_id(cards, limit=self.limit, scroll_y=50))


class TestResolveRestore(unittest.TestCase):
    def setUp(self):
        self.lookup = {
            "e-1-1": TargetState(exists=True, hidden=False),
            "e-1-2": TargetState(exists=True, hidden=True),
            "e-1-3": TargetState(exists=True, hidden=False, block_hidden=True),
            "e-9-9": TargetState(exists=True, hidden=False),
        }

    def test_hash_wins_when_visible(self):
        self.assertEqual(
            resolve_restore_id("#e-1-1", "e-9-9", self.lookup),
            "e-1-1",
        )

    def test_no_hash_uses_storage(self):
        self.assertEqual(
            resolve_restore_id("", "e-9-9", self.lookup),
            "e-9-9",
        )
        self.assertEqual(
            resolve_restore_id("#", "e-9-9", self.lookup),
            "e-9-9",
        )

    def test_hidden_hash_falls_through_to_storage(self):
        self.assertEqual(
            resolve_restore_id("#e-1-2", "e-9-9", self.lookup),
            "e-9-9",
        )

    def test_block_hidden_hash_falls_through(self):
        self.assertEqual(
            resolve_restore_id("#e-1-3", "e-9-9", self.lookup),
            "e-9-9",
        )

    def test_missing_hash_falls_through(self):
        self.assertEqual(
            resolve_restore_id("#e-missing", "e-9-9", self.lookup),
            "e-9-9",
        )

    def test_hidden_storage_skipped(self):
        self.assertIsNone(resolve_restore_id("", "e-1-2", self.lookup))

    def test_missing_storage_skipped(self):
        self.assertIsNone(resolve_restore_id("", "e-nope", self.lookup))

    def test_parse_hash_id(self):
        self.assertEqual(parse_hash_id("#e-1-1"), "e-1-1")
        self.assertIsNone(parse_hash_id(""))
        self.assertIsNone(parse_hash_id("#"))


class TestIndexWiring(unittest.TestCase):
    """Guardrails so site/index.html stays wired to the twin."""

    @classmethod
    def setUpClass(cls):
        cls.text = INDEX.read_text(encoding="utf-8")

    def test_scroll_restoration_manual(self):
        self.assertIn("history.scrollRestoration = 'manual'", self.text)

    def test_pos_key_prefix(self):
        self.assertRegex(self.text, r"htlb-pos:'\s*\+\s*LANG|htlb-pos:' \+ LANG")

    def test_clear_pos_in_to_top(self):
        self.assertRegex(
            self.text,
            r"const toTop = \(\) => \{\s*clearPos\(\);",
            "toTop must clear saved position (filter/reset)",
        )

    def test_restore_called_after_apply(self):
        # restorePos after apply in boot; not only behind location.hash
        self.assertIn("restorePos();", self.text)
        self.assertNotRegex(
            self.text,
            r"if\s*\(\s*location\.hash\s*\)\s*\{[^}]*scrollIntoView",
            "boot must use restorePos(), not a bare hash-only scrollIntoView",
        )

    def test_save_on_scroll(self):
        self.assertRegex(
            self.text,
            r"requestAnimationFrame\(\(\)\s*=>\s*\{\s*ticking\s*=\s*false;\s*savePos\(\);",
        )

    def test_twin_comment(self):
        self.assertIn("forge/site/reading_pos.py", self.text)

    def test_hash_fallthrough_logic_present(self):
        """Hidden/missing hash must not block sessionStorage restore."""
        # After update: restorePos should consult resolve-equivalent paths
        self.assertIn("function restorePos()", self.text)
        m = re.search(
            r"function restorePos\(\)\{(?P<body>.*?)\n\}",
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(m)
        body = m.group("body")
        self.assertIn("sessionStorage.getItem(posKey())", body)
        # Must not return immediately on any truthy location.hash without
        # checking visibility / falling through.
        self.assertNotRegex(
            body,
            r"if\s*\(\s*location\.hash\s*\)\s*\{\s*scrollToEl\(document\.getElementById",
            "hash path must check visibility or fall through to storage",
        )


if __name__ == "__main__":
    unittest.main()
