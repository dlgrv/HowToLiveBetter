"""Blind-judge collection tests: answers -> native preference / decoy FP / per-recipe.

The collector maps judge answers (1/2/=) through the manifest's show_order
mapping: it must say whether the judge picked the ORIGINAL (variant_a) —
without ever leaking that mapping into output files consumed by humans.
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import golden_collect as gc  # noqa: E402

RESULTS = os.path.join(ROOT, "tools", "validate", "results")


def blind_done():
    files = [os.path.join(RESULTS, f"golden_verdicts_batch{b}.json") for b in range(1, 7)]
    return all(os.path.isfile(p) for p in files)


class TestCollect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not blind_done():
            raise unittest.SkipTest("blind judge verdicts not yet complete")

    def test_all_60_pairs_answered(self):
        answers = gc.load_answers(RESULTS)
        self.assertEqual(len(answers), 60)

    def test_summary_structure(self):
        s = gc.summarize(RESULTS)
        self.assertIn("native_preference", s)
        self.assertIn("decoy_fp_rate", s)
        self.assertIn("per_recipe", s)
        self.assertTrue(0.0 <= s["native_preference"] <= 1.0)
        self.assertTrue(0.0 <= s["decoy_fp_rate"] <= 1.0)
        # 50 non-decoy pairs distributed over 4 recipes
        self.assertEqual(sum(v["answered"] for v in s["per_recipe"].values()), 50)


if __name__ == "__main__":
    unittest.main()
