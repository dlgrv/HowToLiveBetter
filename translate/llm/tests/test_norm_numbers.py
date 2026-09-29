#!/usr/bin/env python3
"""Unit tests for verify.norm_numbers scale folding and word folding.

Covers: ES «mil millones» compound scale; ES thousands dots («9.676»);
ZH 千万/百万 scales; RU «мая» month-stem false match («маяк», prose
«в начале мая»); regression guard for the already-working 万亿 and
digit-date month folding («1 мая» == «5 月 1 日»).
"""

import unittest

from translate.steps.verify.verify import norm_numbers


class TestNormNumbersScale(unittest.TestCase):
    def test_es_mil_millones(self):
        self.assertEqual(norm_numbers("20 mil millones", es=True), ["20000000000"])

    def test_es_mil_millon_singular(self):
        self.assertEqual(norm_numbers("1 mil millón", es=True), ["1000000000"])

    def test_es_thousands_dot(self):
        self.assertEqual(norm_numbers("9.676", es=True), ["9676"])
        self.assertEqual(norm_numbers("113.000", es=True), ["113000"])

    def test_es_thousands_dot_multi_group(self):
        self.assertEqual(norm_numbers("1.234.567", es=True), ["1234567"])

    def test_es_thousands_space_still_works(self):
        self.assertEqual(norm_numbers("9 676", es=True), ["9676"])

    def test_es_comma_decimal_not_thousands(self):
        # «1,21» is a decimal; must not become 121 after folding
        self.assertEqual(norm_numbers("1,21", es=True), ["1.21"])

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


class TestNormNumbersPortuguese(unittest.TestCase):
    """pt-BR: same decimal notation as ES; scale words are not Spanish."""

    def test_dot_thousands(self):
        assert norm_numbers("610.000", lang="pt") == ["610000"]

    def test_milhao(self):
        assert norm_numbers("1,5 milhão", lang="pt") == ["1500000"]
        assert norm_numbers("2 milhões", lang="pt") == ["2000000"]

    def test_bilhao_is_billion(self):
        assert norm_numbers("1 bilhão", lang="pt") == ["1000000000"]

    def test_es_billon_still_trillion(self):
        assert norm_numbers("1 billón", lang="es") == ["1000000000000"]

    def test_legacy_es_kwarg_still_works(self):
        assert norm_numbers("610.000", es=True) == ["610000"]


if __name__ == "__main__":
    unittest.main()
