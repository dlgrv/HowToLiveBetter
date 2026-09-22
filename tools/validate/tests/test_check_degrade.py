"""Tests for check_degrade validation gates."""
import importlib.util
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from tools.validate import check_degrade as cd  # noqa: E402

ORIG_RU = """### 2. Заголовок
<!-- 成本标签: 钱=0 时间=少 -->
- Стоимость: 0 юаней
- Простыми словами: госпитализация стоит дешевле в 10 случаях из 100.
- Эффект: разрыв около 10 пунктов
- Уровень доказательности: A
- Источники: gov.cn (2026)
- Примечания: уточнение про 2026 год и детали. Хвост-примечание, которое можно удалить без потери смысла, плюс развёрнутое объяснение зачем это нужно читателю."""


class TestDigits(unittest.TestCase):
    def test_multiset_same(self):
        self.assertEqual(cd.digits_multiset("10 и 2026, п.2"),
                         cd.digits_multiset("2 и 2026, п.10"))

    def test_multiset_differs(self):
        self.assertNotEqual(cd.digits_multiset("10"),
                            cd.digits_multiset("100"))


class TestLang(unittest.TestCase):
    def test_ru_ok(self):
        self.assertTrue(cd.lang_ok("привет мир abc", "ru"))

    def test_en_ok(self):
        self.assertTrue(cd.lang_ok("hello world", "en"))

    def test_mismatch(self):
        self.assertFalse(cd.lang_ok("hello world", "ru"))


class TestCheck(unittest.TestCase):
    def base_pair(self, b):
        return {"pair_id": "g01", "lang": "ru", "variant_b": b}

    def test_good_bloat_passes(self):
        b = ORIG_RU.replace(
            "- Простыми словами: госпитализация стоит дешевле в 10 случаях из 100.",
            "- Простыми словами: следует отметить, что госпитализация, в рамках "
            "данного пункта, стоит дешевле в 10 случаях из 100. Иными словами, "
            "речь идёт о том, что госпитализация обходится дешевле.")
        problems = cd.check(self.base_pair(b), ORIG_RU, "bloat")
        self.assertEqual(problems, [])

    def test_digit_change_rejected(self):
        b = ORIG_RU.replace("10 случаях", "15 случаях")
        problems = cd.check(self.base_pair(b), ORIG_RU, "bloat")
        self.assertTrue(any("digits" in p for p in problems))

    def test_protected_line_rejected(self):
        b = ORIG_RU.replace("### 2. Заголовок", "### 2. Другой заголовок")
        problems = cd.check(self.base_pair(b), ORIG_RU, "bloat")
        self.assertTrue(any("protected" in p for p in problems))

    def test_identical_rejected(self):
        problems = cd.check(self.base_pair(ORIG_RU), ORIG_RU, "bloat")
        self.assertIn("variant_b identical to variant_a", problems)

    def test_abridgement_too_long_rejected(self):
        problems = cd.check(self.base_pair(ORIG_RU + " ещё хвост" * 3),
                            ORIG_RU, "abridgement")
        self.assertTrue(any("ratio" in p for p in problems))

    def test_leak_rejected(self):
        b = ORIG_RU.replace("госпитализация", "variant_a стоит дешево, а 10 так и 2026")
        problems = cd.check(self.base_pair(b), ORIG_RU, "bloat")
        self.assertTrue(any("leak" in p or "digits" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
