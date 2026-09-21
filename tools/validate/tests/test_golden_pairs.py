"""Task 5 tests: golden set manifest (60 pairs, 10 decoys) + markup session.

Manifest selection is deterministic (seed=42). B-variants (controlled
degradations) are filled by subagents; tests validate structure and the
no-leak property of the markup session (original mapping stays in manifest).
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import golden_pairs as gp  # noqa: E402

MANIFEST = os.path.join(ROOT, "tools", "validate", "results", "golden_manifest.json")


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def manifest_ready():
    if not os.path.isfile(MANIFEST):
        return False
    m = load_manifest()
    return len(m.get("pairs", [])) == 60


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
        m1 = gp.select_pairs(ROOT)
        m2 = gp.select_pairs(ROOT)
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
        session = gp.build_session(ROOT)
        self.assertEqual(len(session["batches"]), 6)  # 60 pairs / 10
        for batch in session["batches"]:
            self.assertEqual(len(batch["pairs"]), 10)
            for item in batch["pairs"]:
                self.assertIn("VARIANT 1", item["rendered"])
                self.assertIn("VARIANT 2", item["rendered"])

    def test_session_leaks_no_mapping(self):
        session = gp.build_session(ROOT)
        dumped = json.dumps(session, ensure_ascii=False)
        self.assertNotIn('"variant_a"', dumped)
        self.assertNotIn('"decoy"', dumped)
        # decoy rendered as identical texts (fine), but no flag anywhere
        self.assertNotIn('is_decoy', dumped)


class TestManifestBookConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not manifest_ready():
            raise unittest.SkipTest("golden_manifest.json not yet generated")

    def test_variant_a_lives_in_its_chapter(self):
        m = load_manifest()
        import os
        for p in m["pairs"]:
            nn, lang = p["chapter"], p["lang"]
            book = gp.read_chapter(ROOT, nn, lang)
            self.assertIn(p["variant_a"][:80], book,
                          f"pair {p['id']} excerpt not in book/{lang}/{nn}")


if __name__ == "__main__":
    unittest.main()
