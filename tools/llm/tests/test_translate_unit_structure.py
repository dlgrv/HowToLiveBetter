#!/usr/bin/env python3
"""Unit tests for marker strip/inject + structural validate (no LLM)."""

from __future__ import annotations

import unittest

from tools.llm import translate_unit as tu
from tools.pipeline.labels import field_labels


class RequiredFieldsSSOT(unittest.TestCase):
    """REQUIRED_FIELDS is derived from tools/rules/<lang>.json, not hand-copied."""

    def test_ru_plain_terms_label(self):
        self.assertEqual(tu.REQUIRED_FIELDS["ru"][1], "- Простыми словами:")

    def test_parity_with_field_labels(self):
        for lang in tu.LANGS:
            self.assertEqual(
                tu.REQUIRED_FIELDS[lang],
                tuple(f"- {name}:" for name in field_labels(lang)),
            )


class StripInject(unittest.TestCase):
    def test_strip_markers_from_digest(self):
        raw = "### 1. 标题\n§TAG§\n- 成本：x\n\n§SRC§\n"
        got = tu.strip_mechanical_markers(raw)
        self.assertNotIn("§TAG§", got)
        self.assertNotIn("§SRC§", got)
        self.assertIn("### 1.", got)
        self.assertIn("- 成本：", got)

    def test_inject_item(self):
        body = "### 1. Title\n- Стоимость: 0\n- Простыми словами: a\n"
        got = tu.inject_mechanical_markers(body, "01")
        lines = got.splitlines()
        self.assertEqual(lines[0], "### 1. Title")
        self.assertEqual(lines[1], "§TAG§")
        self.assertEqual(lines[-1], "§SRC§")

    def test_inject_00_strips_invented_markers(self):
        bad = "§TAG§ foo\n# 1. Title\n§SRC§\nprose\n"
        got = tu.inject_mechanical_markers(bad, "00")
        self.assertNotIn("§TAG§", got)
        self.assertNotIn("§SRC§", got)
        self.assertIn("# 1. Title", got)


class ValidateRu(unittest.TestCase):
    def test_item_ok(self):
        text = tu.inject_mechanical_markers(
            "### 1. Ремень\n- Стоимость: 0\n- Простыми словами: x\n- Эффект: y\n- Уровень доказательности: A\n- Примечания: z"
            "\n",
            "01",
        )
        self.assertEqual(tu.validate_unit(text, "01", "ru"), [])

    def test_item_bold_fields_fail(self):
        text = tu.inject_mechanical_markers(
            "### 11. Windows\n**Стоимость:** 10\n**Простыми словами:** a\n"
            "**Эффект:** b\n**Уровень доказательности:** B\n**Примечания:** c\n",
            "11",
        )
        errs = tu.validate_unit(text, "11", "ru")
        self.assertTrue(any("bold" in e for e in errs))
        self.assertTrue(any("missing - Стоимость:" in e for e in errs))

    def test_intro_rejects_hash3_and_fields(self):
        bad = "### Что важно знать\n\nТекст.\n- Стоимость: нет\n"
        errs = tu.validate_unit(bad, "00", "ru")
        self.assertTrue(any("###" in e for e in errs))
        self.assertTrue(any("Стоимость" in e for e in errs))

    def test_intro_ok(self):
        ok = "[← back](../../README.ru.md)\n\n# 1. Не умирай раньше времени\n\nПроза.\n"
        self.assertEqual(tu.validate_unit(ok, "00", "ru"), [])


if __name__ == "__main__":
    unittest.main()
