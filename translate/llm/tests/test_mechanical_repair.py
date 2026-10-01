#!/usr/bin/env python3
"""Tests for mechanical number inject + multiline field collapse (no LLM)."""

from __future__ import annotations

import unittest
from collections import Counter

from translate.steps.repair.mechanical import (
    clean_pollution,
    collapse_multiline_fields,
    ensure_notes_inject,
    fix_heading_number,
    format_abs_for_lang,
    inject_token,
    mechanical_fix_unit,
    normalize_bold_fields,
    strip_trailing_item_period,
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
        counts = Counter(norm_numbers(fixed, lang="ru"))
        self.assertGreaterEqual(counts["2022"], 2)
        self.assertGreaterEqual(counts["523"], 1)


class TitleAndFieldCleanup(unittest.TestCase):
    def test_strip_trailing_item_period_en_and_cn(self):
        self.assertEqual(
            strip_trailing_item_period("### 3. Wear a seatbelt.\n"),
            "### 3. Wear a seatbelt\n",
        )
        self.assertEqual(
            strip_trailing_item_period("### 3. 系安全带。\n"),
            "### 3. 系安全带\n",
        )

    def test_strip_preserves_abbrev_ellipsis_version_chapter(self):
        self.assertEqual(
            strip_trailing_item_period("### 1. Made in U.S.\n"),
            "### 1. Made in U.S.\n",
        )
        self.assertEqual(
            strip_trailing_item_period("### 2. Wait...\n"),
            "### 2. Wait...\n",
        )
        self.assertEqual(
            strip_trailing_item_period("### 3. Version 2.0\n"),
            "### 3. Version 2.0\n",
        )
        self.assertEqual(
            strip_trailing_item_period("# chapter.\n"),
            "# chapter.\n",
        )
        self.assertEqual(strip_trailing_item_period(""), "")
        self.assertEqual(
            strip_trailing_item_period("### 4. Title?\n"),
            "### 4. Title?\n",
        )

    def test_strip_and_bold_skip_fenced_blocks(self):
        text = "### 1. Title.\n```\n### 99. Fenced.\n**Cost:** x\n```\n"
        stripped = strip_trailing_item_period(text)
        self.assertIn("### 99. Fenced.", stripped)
        self.assertIn("### 1. Title\n", stripped)
        bolded = normalize_bold_fields(stripped, "en")
        self.assertIn("**Cost:** x", bolded)

    def test_normalize_bold_fields(self):
        text = "**Cost:** 0\n**In plain terms:** ok\n**UnknownLabel:** x\n"
        got = normalize_bold_fields(text, "en")
        self.assertIn("- Cost: 0", got)
        self.assertIn("- In plain terms: ok", got)
        self.assertIn("**UnknownLabel:** x", got)

    def test_normalize_bold_ru_fullwidth_colon(self):
        text = "**Стоимость：** 0\n"
        got = normalize_bold_fields(text, "ru")
        self.assertIn("- Стоимость: 0", got)

    def test_collapse_applies_period_and_bold(self):
        text = (
            "### 10. Title.\n"
            "**Cost:**\n"
            "  Prices range from 200 to 300.\n"
            "- In plain terms: ok\n"
            "- Benefit: ok\n"
            "- Evidence grade: C\n"
            "- Notes: ok\n"
        )
        got = collapse_multiline_fields(text, "en")
        self.assertIn("### 10. Title\n", got)
        self.assertIn("- Cost: Prices range from 200 to 300.", got)

    def test_fix_heading_number(self):
        self.assertEqual(fix_heading_number("### 5. Title\n", "07"), "### 7. Title\n")
        self.assertEqual(fix_heading_number("### 5. Title\n", "02"), "### 2. Title\n")
        self.assertEqual(fix_heading_number("### 5. Title\n", "00"), "### 5. Title\n")

    def test_fix_heading_skips_fenced_heading(self):
        text = "### 5. Title\n```\n### 99. Inside fence\n```\n"
        got = fix_heading_number(text, "07")
        self.assertIn("### 7. Title", got)
        self.assertIn("### 99. Inside fence", got)


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

    def test_collapse_skips_fenced_empty_fields(self):
        text = (
            "### 10. Title\n"
            "- Cost: ok\n"
            "```\n"
            "- Cost:\n"
            "  should stay split\n"
            "```\n"
            "- In plain terms: ok\n"
            "- Benefit: ok\n"
            "- Evidence grade: C\n"
            "- Notes: ok\n"
        )
        got = collapse_multiline_fields(text, "en")
        self.assertIn("- Cost:\n  should stay split", got.replace("\r\n", "\n"))

    def test_collapse_ru_fullwidth_colon_empty_field(self):
        text = (
            "### 7. Title\n"
            "- Стоимость：\n"
            "Ноль.\n"
            "- Простыми словами: a\n"
            "- Эффект: b\n"
            "- Уровень доказательности: A\n"
            "- Примечания: z\n"
        )
        got = collapse_multiline_fields(text, "ru")
        self.assertIn("- Стоимость: Ноль.", got)

    def test_orphan_grade_moves_onto_evidence(self):
        text = (
            "### 7. Title\n"
            "- Стоимость: 0\n"
            "- Простыми словами: a\n"
            "- Эффект: b\n"
            "- Уровень доказательности:\n"
            "- Источники: doi x\n"
            " A\n"
        )
        got = collapse_multiline_fields(text, "ru")
        self.assertIn("- Уровень доказательности: A", got)
        self.assertIn("- Источники: doi x", got)

    def test_ensure_notes_replaces_stale_inject_tokens(self):
        stale = "- Notes: old " + inject_token("2022", "en") + "\n"
        got = ensure_notes_inject(stale, [("523", 1)], "en")
        self.assertNotIn("〔2022〕", got)
        self.assertIn(inject_token("523", "en"), got)

    def test_pipeline_order_collapse_then_heading(self):
        text = (
            "### 99. Wrong.\n"
            "**Cost:**\n"
            "  x\n"
            "- In plain terms: y\n"
            "- Benefit: z\n"
            "- Evidence grade: C\n"
            "- Notes: n\n"
        )
        collapsed = collapse_multiline_fields(text, "en")
        fixed = fix_heading_number(collapsed, "07")
        self.assertTrue(fixed.startswith("### 7. Wrong\n"))


class PollutionAndInjectEdges(unittest.TestCase):
    def test_clean_pollution_strips_digit_dumps_only(self):
        line = "text 0.499 0.123 0.456"
        got = clean_pollution(line)
        self.assertEqual(got, "text")
        keep = "only one 0.499 tail"
        self.assertEqual(clean_pollution(keep), keep)

    def test_mechanical_fix_no_issues_still_collapses(self):
        text = (
            "### 10. Title\n"
            "- Cost:\n"
            "  joined.\n"
            "- In plain terms: ok\n"
            "- Benefit: ok\n"
            "- Evidence grade: C\n"
            "- Notes: ok\n"
        )
        fixed = mechanical_fix_unit(text, [], "en")
        self.assertIn("- Cost: joined.", fixed)

    def test_ensure_notes_inject_appends_when_missing_notes(self):
        text = "### 1. T\n- Cost: 0\n"
        got = ensure_notes_inject(text, [("99", 1)], "en")
        self.assertIn("- Notes:", got)
        self.assertIn(inject_token("99", "en"), got)


if __name__ == "__main__":
    unittest.main()
