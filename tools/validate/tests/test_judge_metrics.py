"""Task 7 tests: Cohen's kappa, screening metrics, gate logic.

Pure-math module (no I/O beyond verdict JSON loading).
"""

import json
import os
import unittest

import pytest
from tools.validate import judge_metrics as jm


class TestKappa(unittest.TestCase):
    def test_perfect_agreement(self):
        a = [1, 0, 1, 1, 0]
        assert jm.cohens_kappa(a, a) == pytest.approx(1.0)

    def test_chance_agreement_zero(self):
        a = [1, 0, 1, 0, 1, 0, 1, 0]
        b2 = [1, 1, 0, 0, 1, 1, 0, 0]
        k = jm.cohens_kappa(a, b2)
        assert k == pytest.approx(0.0, abs=1e-6)

    def test_known_value(self):
        a = [1, 1, 0, 0, 1]
        b = [1, 0, 0, 1, 1]
        assert jm.cohens_kappa(a, b) == pytest.approx(1 / 6, abs=1e-6)

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError, match="equal length"):
            jm.cohens_kappa([1, 0], [1])

    def test_degenerate_all_same(self):
        assert jm.cohens_kappa([1, 1], [1, 1]) is None
        assert jm.cohens_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0


class TestScreening(unittest.TestCase):
    def test_confusion_and_metrics(self):
        gold = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]
        pred = [0, 0, 1, 1, 1, 1, 1, 1, 0, 0]
        m = jm.screening_metrics(gold, pred)
        assert m["tp"] == 4
        assert m["fp"] == 2
        assert m["fn"] == 2
        assert m["tn"] == 2
        assert m["precision"] == pytest.approx(4 / 6)
        assert m["recall"] == pytest.approx(4 / 6)
        assert m["fpr"] == pytest.approx(2 / 4)

    def test_fnr_gate(self):
        gold = [1] * 10 + [0] * 5
        pred = [1] * 7 + [0] * 3 + [1] * 2 + [0] * 3
        m = jm.screening_metrics(gold, pred)
        assert m["fnr"] == pytest.approx(0.3)
        assert not jm.gate_fnr(m, threshold=0.2)
        assert jm.gate_fnr(m, threshold=0.5)


class TestLoadPairVerdicts(unittest.TestCase):
    def test_loads_and_pads(self):
        path = os.path.join(os.path.dirname(__file__), "_tmp_verdicts.json")
        data = {"native": [1, 0], "degraded": [0, 0]}
        with open(path, "w") as f:
            json.dump(data, f)
        try:
            native, degraded = jm.load_pair_verdicts(path)
            assert native == [1, 0]
            assert degraded == [0, 0]
        finally:
            os.unlink(path)

    def test_weighted_nativeness(self):
        verdicts = {"native": [1] * 24 + [0] * 6, "degraded": [1] * 9 + [0] * 21}
        nr = jm.nativeness_rate(verdicts)
        assert nr["native"] == pytest.approx(24 / 30)
        assert nr["degraded"] == pytest.approx(9 / 30)
        assert nr["gap"] == pytest.approx((24 - 9) / 30)


if __name__ == "__main__":
    unittest.main()
