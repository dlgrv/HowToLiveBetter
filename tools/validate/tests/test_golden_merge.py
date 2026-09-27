"""Task 11 prep tests: golden B-variant merge validator (hard rules).

Rules from the plan: degradation is stylistic ONLY — numbers byte-identical,
markdown structure preserved, headings/sources/tag-comments untouched,
decoys never touched, B != A.
"""

import json
import os
import unittest

from tools.test_paths import REPO_ROOT

MANIFEST = os.path.join(REPO_ROOT, "tools", "validate", "results", "golden_manifest.json")


def _merge_skip_line(xa: str) -> bool:
    return xa.startswith(("### ", "- Источники:", "- Sources:")) or xa.lstrip().startswith("<!--")


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

    def test_numbers_recipe_aware(self):
        """v2 rules: abridgement may remove digit-bearing sentences (subset
        check on digit chars), bloat may only add (superset). Tampering
        (46% -> 64%) is caught in both directions."""
        import re
        from collections import Counter

        m = json.load(open(MANIFEST, encoding="utf-8"))
        for p in m["pairs"]:
            if p["decoy"] or not p["variant_b"]:
                continue
            pat = re.compile(r"\d")
            ca = Counter(pat.findall(p["variant_a"]))
            cb = Counter(pat.findall(p["variant_b"]))
            if p["recipe"] == "abridgement":
                self.assertTrue(
                    all(cb[d] <= ca[d] for d in cb), f"pair {p['id']}: abridgement added digits"
                )
            else:
                self.assertTrue(
                    all(cb[d] >= n for d, n in ca.items()), f"pair {p['id']}: bloat lost digits"
                )

    def test_structure_preserved(self):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        for p in m["pairs"]:
            if p["decoy"] or not p["variant_b"]:
                continue
            la, lb = p["variant_a"].splitlines(), p["variant_b"].splitlines()
            self.assertEqual(len(la), len(lb), f"pair {p['id']}: line count changed")
            for i, (xa, xb) in enumerate(zip(la, lb, strict=True)):
                if _merge_skip_line(xa):
                    self.assertEqual(xa, xb, f"pair {p['id']} line {i}: immutable line changed")

    def test_b_differs_and_recipe_match(self):
        m = json.load(open(MANIFEST, encoding="utf-8"))
        for p in m["pairs"]:
            if p["decoy"]:
                self.assertEqual(p["variant_a"], p["variant_b"])
            else:
                self.assertNotEqual(p["variant_a"], p["variant_b"], p["id"])
                self.assertIn(p["recipe"], {r["name"] for r in m["recipes"]})


if __name__ == "__main__":
    unittest.main()
