"""Task 7 tests: Cohen's kappa, screening metrics, gate logic.

Pure-math module (no I/O beyond verdict JSON loading).
"""
import json
import math
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import judge_metrics as jm  # noqa: E402


class TestKappa(unittest.TestCase):
    def test_perfect_agreement(self):
        a = [1, 0, 1, 1, 0]
        self.assertAlmostEqual(jm.cohens_kappa(a, a), 1.0)

    def test_chance_agreement_zero(self):
        # exactly chance-level agreement -> kappa ~ 0
        a = [1, 0, 1, 0, 1, 0, 1, 0]
        b = [1, 0, 1, 0, 1, 0, 1, 0]  # perfect would be 1; construct chance:
        b2 = [1, 1, 0, 0, 1, 1, 0, 0]  # agree 4/8 = p_e for balanced marginals
        k = jm.cohens_kappa(a, b2)
        self.assertAlmostEqual(k, 0.0, places=6)

    def test_known_value(self):
        # po = 3/5 = 0.6; marginals a: {1:3, 0:2}, b: {1:3, 0:2}
        # pe = .6*.6 + .4*.4 = 0.52 -> kappa = (0.6-0.52)/0.48 = 1/6
        a = [1, 1, 0, 0, 1]
        b = [1, 0, 0, 1, 1]
        self.assertAlmostEqual(jm.cohens_kappa(a, b), 1 / 6, places=6)

    def test_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            jm.cohens_kappa([1, 0], [1])

    def test_degenerate_all_same(self):
        # pe==1 -> kappa undefined; the function must say so, not fake 1.0
        # (review S5: the old fudge laundered 0/0 into a pass)
        self.assertIsNone(jm.cohens_kappa([1, 1], [1, 1]))
        # po is still meaningful and must be reported alongside
        self.assertEqual(jm.cohens_kappa([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)


class TestScreening(unittest.TestCase):
    def test_confusion_and_metrics(self):
        # gold: 0=calque,1=native ; pred from judge
        gold = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]
        pred = [0, 0, 1, 1, 1, 1, 1, 1, 0, 0]  # FP 2 (of 4 calques), FN 2 (of 6 natives)
        m = jm.screening_metrics(gold, pred)
        self.assertEqual(m["tp"], 4)
        self.assertEqual(m["fp"], 2)
        self.assertEqual(m["fn"], 2)
        self.assertEqual(m["tn"], 2)
        self.assertAlmostEqual(m["precision"], 4 / 6)
        self.assertAlmostEqual(m["recall"], 4 / 6)
        self.assertAlmostEqual(m["fpr"], 2 / 4)

    def test_fnr_gate(self):
        gold = [1] * 10 + [0] * 5
        pred = [1] * 7 + [0] * 3 + [1] * 2 + [0] * 3  # misses 3 of 10 natives
        m = jm.screening_metrics(gold, pred)
        self.assertAlmostEqual(m["fnr"], 0.3)
        self.assertFalse(jm.gate_fnr(m, threshold=0.2))   # 0.3 > 0.2
        self.assertTrue(jm.gate_fnr(m, threshold=0.5))


class TestLoadPairVerdicts(unittest.TestCase):
    def test_loads_and_pads(self):
        path = os.path.join(os.path.dirname(__file__), "_tmp_verdicts.json")
        data = {"native": [1, 0], "degraded": [0, 0]}
        with open(path, "w") as f:
            json.dump(data, f)
        try:
            native, degraded = jm.load_pair_verdicts(path)
            self.assertEqual(native, [1, 0])
            self.assertEqual(degraded, [0, 0])
        finally:
            os.unlink(path)

    def test_weighted_nativeness(self):
        # 60 pairs: A-group 30, B-group 30; decoys excluded by caller
        verdicts = {"native": [1] * 24 + [0] * 6, "degraded": [1] * 9 + [0] * 21}
        nr = jm.nativeness_rate(verdicts)
        self.assertAlmostEqual(nr["native"], 24 / 30)
        self.assertAlmostEqual(nr["degraded"], 9 / 30)
        self.assertAlmostEqual(nr["gap"], (24 - 9) / 30)


if __name__ == "__main__":
    unittest.main()
