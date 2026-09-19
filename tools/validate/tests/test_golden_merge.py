"""Task 11 prep tests: golden B-variant merge validator (hard rules).

Rules from the plan: degradation is stylistic ONLY — numbers byte-identical,
markdown structure preserved, headings/sources/tag-comments untouched,
decoys never touched, B != A.
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import golden_merge as gm  # noqa: E402

MANIFEST = os.path.join(ROOT, "tools", "validate", "results", "golden_manifest.json")


def manifest_has_b():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    return any(p["variant_b"] for p in m["pairs"] if not p["decoy"])


class TestMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not manifest_has_b():
            raise unittest.SkipTest("B-variants not yet merged")

    def test_all_non_decoy_pairs_filled(self):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        empty = [p["id"] for p in m["pairs"] if not p["decoy"] and not p["variant_b"]]
        self.assertEqual(empty, [])

    def test_numbers_byte_identical(self):
        import re
        m = json.load(open(MANIFEST, encoding="utf-8"))
        for p in m["pairs"]:
            if p["decoy"] or not p["variant_b"]:
                continue
            nums_a = sorted(re.findall(r"\d+(?:[.,]\d+)?", p["variant_a"]))
            nums_b = sorted(re.findall(r"\d+(?:[.,]\d+)?", p["variant_b"]))
            self.assertEqual(nums_a, nums_b, f"pair {p['id']}: numbers changed")

    def test_structure_preserved(self):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        for p in m["pairs"]:
            if p["decoy"] or not p["variant_b"]:
                continue
            la, lb = p["variant_a"].splitlines(), p["variant_b"].splitlines()
            self.assertEqual(len(la), len(lb), f"pair {p['id']}: line count changed")
            for i, (xa, xb) in enumerate(zip(la, lb)):
                if xa.startswith("### ") or xa.lstrip().startswith("<!--") \
                        or xa.startswith("- Источники:") or xa.startswith("- Sources:"):
                    self.assertEqual(xa, xb, f"pair {p['id']} line {i}: immutable line changed")

    def test_b_differs_and_recipe_match(self):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        for p in m["pairs"]:
            if p["decoy"]:
                self.assertEqual(p["variant_a"], p["variant_b"])
            else:
                self.assertNotEqual(p["variant_a"], p["variant_b"], p["id"])
                self.assertIn(p["recipe"],
                              {r["name"] for r in m["recipes"]})


if __name__ == "__main__":
    unittest.main()
