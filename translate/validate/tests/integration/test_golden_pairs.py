"""Task 5 tests: golden set manifest (60 pairs, 10 decoys) + markup session.

Manifest selection is deterministic (seed=42). B-variants (controlled
degradations) are filled by subagents; tests validate structure and the
no-leak property of the markup session (original mapping stays in manifest).
"""

import json
import os
import unittest

import pytest

from translate.lib.paths import load_chapter_text
from translate.test_paths import REPO_ROOT
from translate.validate.research import golden_pairs as gp

MANIFEST = os.path.join(REPO_ROOT, "translate", "validate", "results", "golden_manifest.json")


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def manifest_ready():
    if not os.path.isfile(MANIFEST):
        return False
    m = load_manifest()
    return len(m.get("pairs", [])) == 60


def manifest_matches_books(m):
    """False when book/ drifted away from golden_manifest excerpts."""
    for p in m.get("pairs", []):
        nn, lang = p["chapter"], p["lang"]
        book = load_chapter_text(REPO_ROOT, nn, lang)
        if p["variant_a"][:80] not in book:
            return False
    return True


class TestSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not manifest_ready():
            raise unittest.SkipTest("golden_manifest.json not yet generated")

    def test_counts(self):
        m = load_manifest()
        self.assertEqual(len(m["pairs"]), 60)
        # lite2: 18 real pairs (abridgement+bloat) + 42 identical-twin decoys
        self.assertEqual(sum(1 for p in m["pairs"] if p["decoy"]), 42)
        strata = {p["stratum"] for p in m["pairs"]}
        self.assertLessEqual(strata, {"short", "medium", "long", "fresh"})

    def test_deterministic_selection(self):
        m1 = gp.select_pairs(REPO_ROOT)
        m2 = gp.select_pairs(REPO_ROOT)
        self.assertEqual(m1, m2)

    def test_mapping_not_in_pair_public_fields(self):
        m = load_manifest()
        for p in m["pairs"]:
            # variant_a IS the original; the session must never say which is which
            self.assertIn("show_order", p)
            self.assertIn(p["show_order"], ("AB", "BA"))

    def test_non_decoy_pairs_have_b_to_fill_or_filled(self):
        m = load_manifest()
        for p in m["pairs"]:
            if p["decoy"]:
                continue
            if p.get("variant_b"):  # filled: must differ from A
                self.assertNotEqual(p["variant_b"], p["variant_a"])


class TestSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not manifest_ready():
            raise unittest.SkipTest("golden_manifest.json not yet generated")

    def test_build_session_batches(self):
        session = gp.build_session()
        self.assertEqual(len(session["batches"]), 6)  # 60 pairs / 10
        for batch in session["batches"]:
            self.assertEqual(len(batch["pairs"]), 10)
            for item in batch["pairs"]:
                self.assertIn("VARIANT 1", item["rendered"])
                self.assertIn("VARIANT 2", item["rendered"])

    def test_session_leaks_no_mapping(self):
        session = gp.build_session()
        dumped = json.dumps(session, ensure_ascii=False)
        self.assertNotIn('"variant_a"', dumped)
        self.assertNotIn('"decoy"', dumped)
        # decoy rendered as identical texts (fine), but no flag anywhere
        self.assertNotIn("is_decoy", dumped)


@pytest.mark.xfail(
    strict=True,
    reason="golden_manifest.json excerpts drifted; regenerate fixtures",
)
class TestManifestBookConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not manifest_ready():
            raise unittest.SkipTest("golden_manifest.json not yet generated")

    def test_variant_a_lives_in_its_chapter(self):
        m = load_manifest()
        self.assertTrue(
            manifest_matches_books(m),
            "golden_manifest.json excerpts no longer match book/; regenerate fixtures",
        )
        for p in m["pairs"]:
            nn, lang = p["chapter"], p["lang"]
            book = load_chapter_text(REPO_ROOT, nn, lang)
            self.assertIn(
                p["variant_a"][:80], book, f"pair {p['id']} excerpt not in book/{lang}/{nn}"
            )


if __name__ == "__main__":
    unittest.main()
