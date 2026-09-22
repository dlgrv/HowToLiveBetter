"""Plainness pass tests (plan addendum: "understandable to a child" standard).

Scope: ONLY the plain-terms field (Простыми словами / In plain terms) — the
field whose contract IS simplicity. Эффект/Notes are allowed to be technical.

Checks (WARN-only, deterministic):
  - long sentence: > max_sentence_words (default 25) words
  - relative-clause chain: >= 3 «который/which» in one sentence
  - unexplained ALL-CAPS abbreviation (not in plain_ok_abbrev whitelist)
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import plainness as pl  # noqa: E402

PACK = json.load(open(os.path.join(ROOT, "tools", "rules", "ru.json"),
                      encoding="utf-8"))


def ru_field(text):
    return f"### 1. Заголовок\n- Простыми словами: {text}\n- Эффект: технический текст без ограничений\n"


class TestSentenceLength(unittest.TestCase):
    def test_long_sentence_flagged(self):
        warns = pl.check_field("Съешьте " + "очень " * 30 + "ещё одну сливу.", PACK)
        self.assertTrue(any(w["type"] == "long_sentence" for w in warns))

    def test_short_sentence_clean(self):
        warns = pl.check_field("Съешьте сливу. Она полезна. Это просто.", PACK)
        self.assertEqual(warns, [])

    def test_effect_field_not_scanned(self):
        body = "### 1. Заголовок\n- Эффект: " + "слово " * 40 + "\n"
        fields = pl.plain_fields(body, PACK)
        self.assertEqual(fields, [])


class TestWhichChain(unittest.TestCase):
    def test_three_which_flagged(self):
        text = ("Есть врач, который лечит, который знает, который поможет "
                "и который всегда на связи.")
        warns = pl.check_field(text, PACK)
        self.assertTrue(any(w["type"] == "which_chain" for w in warns))

    def test_one_which_clean(self):
        warns = pl.check_field("Есть врач, который лечит дома.", PACK)
        self.assertEqual(warns, [])


class TestAbbrev(unittest.TestCase):
    def test_unknown_abbrev_flagged(self):
        warns = pl.check_field("Сделайте КТГ и снова КТГ.", PACK)
        self.assertTrue(any(w["type"] == "unexplained_abbrev" for w in warns))

    def test_whitelisted_abbrev_clean(self):
        warns = pl.check_field("Проверьте давление при ОМС-осмотре.", PACK)
        self.assertEqual([w for w in warns if w["type"] == "unexplained_abbrev"], [])

    def test_explained_abbrev_clean(self):
        warns = pl.check_field("Сделайте КТГ (кардиотокографию) плода.", PACK)
        self.assertEqual([w for w in warns if w["type"] == "unexplained_abbrev"], [])


class TestChapter(unittest.TestCase):
    def test_check_chapter_reports_units(self):
        body = (ru_field("Съешьте " + "очень " * 30 + "сливу.")
                + "\n### 2. Второй\n- Простыми словами: Коротко и ясно.\n")
        report = pl.check_chapter(body, PACK)
        self.assertEqual(len(report), 2)
        self.assertTrue(report[0]["warns"])
        self.assertEqual(report[1]["warns"], [])


if __name__ == "__main__":
    unittest.main()
