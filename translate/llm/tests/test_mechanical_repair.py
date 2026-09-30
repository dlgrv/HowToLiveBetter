#!/usr/bin/env python3
"""Tests for mechanical number inject + multiline field collapse (no LLM)."""

from __future__ import annotations

import unittest

from translate.steps.repair.mechanical import (
    collapse_multiline_fields,
    format_abs_for_lang,
    inject_token,
    mechanical_fix_unit,
)
from translate.steps.repair.verify_issues import issues_still_present
from translate.steps.verify.verify import norm_numbers


class LocaleFormat(unittest.TestCase):
    def test_es_decimal_comma(self):
        self.assertEqual(format_abs_for_lang("0.499", "es"), "0,499")
        self.assertEqual(norm_numbers(inject_token("0.499", "es"), lang="es"), ["0.499"])

    def test_en_keeps_dot(self):
        self.assertEqual(format_abs_for_lang("0.499", "en"), "0.499")
        self.assertEqual(norm_numbers(inject_token("0.499", "en"), lang="en"), ["0.499"])

    def test_bracket_inject_does_not_glue(self):
        text = "note " + inject_token("2022", "ru") + " " + inject_token("523", "ru")
        got = set(norm_numbers(text, lang="ru"))
        self.assertIn("2022", got)
        self.assertIn("523", got)
        self.assertNotIn("2022523", got)


class MangledAndInject(unittest.TestCase):
    def test_fixes_0499_and_clears_absent(self):
        body = (
            "### 14. Title\n"
            "- Costo: 0\n"
            "- En términos sencillos: a\n"
            "- Beneficio: efecto medio (g = 0499).\n"
            "- Nivel de evidencia: A\n"
            "- Notas: combinarlos.\n"
        )
        issues = [{"kind": "number_absent", "value": "0.499", "count": 1}]
        fixed = mechanical_fix_unit(body, issues, "es")
        self.assertIn("0,499", fixed)
        self.assertEqual(issues_still_present(fixed, issues, "es"), [])

    def test_space_dump_would_glue_but_brackets_safe(self):
        body = (
            "### 4. Title\n"
            "- Стоимость: 0\n"
            "- Простыми словами: a\n"
            "- Эффект: b\n"
            "- Уровень доказательности: A\n"
            "- Примечания: путь с 2024 года.\n"
        )
        issues = [
            {"kind": "number_absent", "value": "2022", "count": 2},
            {"kind": "number_absent", "value": "523", "count": 1},
        ]
        fixed = mechanical_fix_unit(body, issues, "ru")
        self.assertEqual(issues_still_present(fixed, issues, "ru"), [])
        self.assertNotIn("2022523", " ".join(norm_numbers(fixed, lang="ru")))


class CollapseFields(unittest.TestCase):
    def test_indented_value_joins(self):
        text = (
            "### 10. Title\n"
            "- Cost:\n"
            "  Prices range from 200 to 300.\n"
            "- In plain terms: ok\n"
            "- Benefit: ok\n"
            "- Evidence grade: C\n"
            "- Notes: ok\n"
        )
        got = collapse_multiline_fields(text, "en")
        self.assertIn("- Cost: Prices range from 200 to 300.", got)
        self.assertFalse(any(ln.strip() == "- Cost:" for ln in got.splitlines()))

    def test_unindented_value_joins(self):
        text = (
            "### 19. Title\n"
            "- Costo:\n"
            "No supone ningún gasto.\n"
            "- En términos sencillos: x\n"
            "- Beneficio: y\n"
            "- Nivel de evidencia: A\n"
            "- Notas: z\n"
        )
        got = collapse_multiline_fields(text, "es")
        self.assertIn("- Costo: No supone ningún gasto.", got)


if __name__ == "__main__":
    unittest.main()
