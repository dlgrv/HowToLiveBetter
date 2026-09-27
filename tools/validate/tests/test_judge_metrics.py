"""Task 7 tests: Cohen's kappa and nativeness rates.

Pure-math module.
"""

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


class TestNativenessRate(unittest.TestCase):
    def test_weighted_nativeness(self):
        verdicts = {"native": [1] * 24 + [0] * 6, "degraded": [1] * 9 + [0] * 21}
        nr = jm.nativeness_rate(verdicts)
        assert nr["native"] == pytest.approx(24 / 30)
        assert nr["degraded"] == pytest.approx(9 / 30)
        assert nr["gap"] == pytest.approx((24 - 9) / 30)


if __name__ == "__main__":
    unittest.main()
