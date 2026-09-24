#!/usr/bin/env python3
"""Structural tests for repair_unit.py (no LLM, no server).

Covers: repaired-body shape passes translate_unit's gate; issue-assert logic
(number present / calque stem count); --issues-json validation.
"""
from __future__ import annotations

import os
import sys
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.llm import repair_unit as ru  # noqa: E402
from tools.llm.translate_unit import (  # noqa: E402
    inject_mechanical_markers,
    validate_unit,
)


class RepairedShape(unittest.TestCase):
    def test_repaired_item_shape_passes_gate(self):
        body = (
            "### 7. Title\n"
            "- Стоимость: 0\n"
            "- Простыми словами: a\n"
            "- Эффект: 610 000 человек\n"
            "- Уровень доказательности: A\n"
            "- Примечания: z\n"
        )
        got = inject_mechanical_markers(body, "07")
        self.assertEqual(validate_unit(got, "07", "ru"), [])

    def test_bold_fields_fail_gate(self):
        body = (
            "### 7. Title\n"
            "**Стоимость:** 0\n"
            "- Простыми словами: a\n"
            "- Эффект: b\n"
            "- Уровень доказательности: A\n"
            "- Примечания: z\n"
        )
        got = inject_mechanical_markers(body, "07")
        self.assertTrue(validate_unit(got, "07", "ru"))


class IssueAssert(unittest.TestCase):
    def test_number_present_ok(self):
        leftovers = ru.issues_still_present(
            "61万 = 610000 человек", [{"kind": "number_absent", "value": "610000"}],
            "ru")
        self.assertEqual(leftovers, [])

    def test_number_still_absent(self):
        leftovers = ru.issues_still_present(
            "61 тысяча человек", [{"kind": "number_absent", "value": "610000"}],
            "ru")
        self.assertEqual(leftovers, ["number 610000 still absent"])

    def test_calque_stem_cleared(self):
        leftovers = ru.issues_still_present(
            "в популяции (population) растёт",
            [{"kind": "banned_calque", "stem": "популяц"}], "ru")
        self.assertEqual(leftovers, [])

    def test_calque_stem_still_many(self):
        leftovers = ru.issues_still_present(
            "популяция растёт, популяция стареет",
            [{"kind": "banned_calque", "stem": "популяц"}], "ru")
        self.assertEqual(leftovers, ["stem «популяц» still 2x"])


class IssuesJsonValidation(unittest.TestCase):
    def _run(self, argv):
        try:
            return ru.main(argv)
        except SystemExit as e:
            return f"SystemExit: {e}"

    def test_rejects_unrepairable_kind(self):
        out = self._run(["--nn", "01", "--unit", "07", "--lang", "ru",
                         "--out-dir", "/tmp/x",
                         "--issues-json", '[{"kind": "headings_mismatch"}]'])
        self.assertIn("unrepairable", str(out))

    def test_rejects_empty_list(self):
        out = self._run(["--nn", "01", "--unit", "07", "--lang", "ru",
                         "--out-dir", "/tmp/x", "--issues-json", "[]"])
        self.assertIn("non-empty", str(out))


if __name__ == "__main__":
    unittest.main()
