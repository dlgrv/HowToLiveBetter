#!/usr/bin/env python3
"""Unit tests for verify.norm_numbers scale folding and word folding.

Covers: ES «mil millones» compound scale; ZH 千万/百万 scales; RU «мая»
month-stem false match («маяк», prose «в начале мая»); regression guard
for the already-working 万亿 and digit-date month folding («1 мая» == «5 月 1 日»).
"""
import os
import sys
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.verify import norm_numbers  # noqa: E402


class TestNormNumbersScale(unittest.TestCase):
    def test_es_mil_millones(self):
        self.assertEqual(norm_numbers("20 mil millones", es=True), ["20000000000"])

    def test_es_mil_millon_singular(self):
        self.assertEqual(norm_numbers("1 mil millón", es=True), ["1000000000"])

    def test_zh_qianwan(self):
        self.assertEqual(norm_numbers("3 千万"), ["30000000"])

    def test_zh_baiwan(self):
        self.assertEqual(norm_numbers("5 百万"), ["5000000"])

    def test_zh_wanyi_still_works(self):
        # regression guard — don't break the existing working case
        self.assertEqual(norm_numbers("2万亿"), ["2000000000000"])

    def test_ru_maya_not_matched_as_number(self):
        # «маяк» must not parse as «5», and prose «в начале мая» (no digit
        # date context) must not fold either — the plan's acceptance case.
        self.assertNotIn("5", norm_numbers("маяк виден в начале мая", ru=True))

    def test_ru_digit_date_maya_still_folds(self):
        # «1 мая» == «5 月 1 日» is the reason month stems exist; the anchor
        # must keep the digit-date case working.
        self.assertIn("5", norm_numbers("1 мая", ru=True))


if __name__ == "__main__":
    unittest.main()
