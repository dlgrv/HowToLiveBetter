"""Task 4 tests: mutation spec validation, SEED_REF immutability, verify.py wrapper.

Generation of the 30 mutations is subagent work (seed-fixed list committed as
results/mutations_seed42.json); these tests validate spec + plumbing offline.
"""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import mutation_test as mt  # noqa: E402

RESULTS = os.path.join(ROOT, "tools", "validate", "results")
SPEC_PATH = os.path.join(RESULTS, "mutations_seed42.json")
SEED_REF = "f0c2674f729c6af1ef33c4575c30cbb3e2be5f13e7626090a5e16144790d1ef9"

CHAPTERS = ["02", "04", "05", "06", "07", "09", "12", "14", "16", "17",
            "20", "22", "23", "25", "27", "32"]

TAXONOMY = {"dropped_condition", "reversed_logic", "softened_claim",
            "added_advice", "subject_swapped", "cross_unit_contradiction"}


def load_spec():
    with open(SPEC_PATH, encoding="utf-8") as f:
        return json.load(f)


def _spec_ready():
    """Spec exists AND generation filled (30 mutations + 30 controls)."""
    if not os.path.isfile(SPEC_PATH):
        return False
    spec = load_spec()
    return (len(spec.get("mutations", [])) >= 30
            and len(spec.get("controls", [])) >= 30)


class TestSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _spec_ready():
            raise unittest.SkipTest("mutations_seed42.json not yet generated")

    def test_counts(self):
        spec = load_spec()
        self.assertEqual(len(spec["mutations"]), 30)
        self.assertEqual(len(spec["controls"]), 30)

    def test_seed_ref_pins_generation(self):
        self.assertEqual(load_spec()["seed_ref"], SEED_REF)

    def test_taxonomy_and_targets(self):
        spec = load_spec()
        for m in spec["mutations"]:
            self.assertIn(m["issue_type"], TAXONOMY)
            nn, lang = m["target"]
            self.assertIn(nn, CHAPTERS)
            self.assertIn(lang, ("ru", "en"))
            self.assertTrue(os.path.isfile(mt.book_path(nn, lang)))
            self.assertNotEqual(m["mutant_text"], m["original_excerpt"])
            self.assertIn(m["original_excerpt"], mt.read_book(nn, lang))

    def test_controls_untouched(self):
        spec = load_spec()
        for c in spec["controls"]:
            nn, lang = c["target"]
            self.assertIn(c["original_excerpt"], mt.read_book(nn, lang))


class TestVerifyWrapper(unittest.TestCase):
    def test_slug_resolution(self):
        p = mt.book_path("02", "ru")
        self.assertTrue(os.path.isfile(p))

    def test_clean_chapter_passes_wrapper(self):
        code, out = mt.run_verify("02", "ru")
        self.assertEqual((code, out["status"]), (0, "pass"))

    def test_broken_file_fails_wrapper(self):
        code, out = mt.run_verify("02", "ru", file_text="кактус без структуры\n")
        self.assertEqual(out["status"], "fail")


class TestControlsVerifiedClean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _spec_ready():
            raise unittest.SkipTest("mutations_seed42.json not yet generated")

    def test_every_control_target_is_green_today(self):
        for nn in CHAPTERS:
            for lang in ("ru", "en"):
                code, out = mt.run_verify(nn, lang)
                self.assertEqual(out["status"], "pass", f"{lang}{nn} must be green")


if __name__ == "__main__":
    unittest.main()
