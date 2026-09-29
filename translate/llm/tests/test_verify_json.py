#!/usr/bin/env python3
"""Tests for translate/steps/verify/verify.py --json (machine report for repair wave)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from translate.llm.tests.helpers import run_cli
from translate.steps.repair.verify_issues import parse_verify_json
from translate.test_paths import REPO_ROOT

ROOT = Path(REPO_ROOT)


class VerifyJson(unittest.TestCase):
    def test_json_flag_emits_object_with_fails(self):
        # Hermetic: temp file (do not depend on gitignored runs/active).
        tmpmd = ROOT / "translate" / "llm" / "tests" / "_tmp_verify_json_fixture.md"
        try:
            tmpmd.write_text(
                "### 1. заголовок\n"
                "- Стоимость: 100\n"
                "- Простыми словами: что-то\n"
                "- Эффект: 610 000 человек\n"
                "- Уровень доказательности: A\n"
                "- Примечания: ещё\n",
                encoding="utf-8",
            )
            r = run_cli(
                [
                    sys.executable,
                    str(ROOT / "translate" / "steps" / "verify" / "verify.py"),
                    "01",
                    "--lang",
                    "ru",
                    "--file",
                    str(tmpmd),
                    "--json",
                ],
            )
            # May be exit 0 or 1; JSON is the LAST stdout line (also on FAIL) —
            # rfind("{") alone would land inside the object, so parse by line.
            data = parse_verify_json(r.stdout)
            self.assertIn("ok", data)
            self.assertIn("fails", data)
            self.assertIn("warns", data)
            self.assertEqual(data["chapter"], "01")
            self.assertEqual(data["lang"], "ru")
            self.assertIsInstance(data["fails"], list)
            if data["fails"]:
                self.assertIn("kind", data["fails"][0])
            if r.returncode == 1:
                self.assertFalse(data["ok"])
                self.assertGreater(len(data["fails"]), 0)
                for f in data["fails"]:
                    if f.get("kind") == "number_absent":
                        self.assertIn("value", f)
                        self.assertIn("count", f)
                    if f.get("kind") == "banned_calque":
                        self.assertIn("stem", f)
                        self.assertIn("count", f)
        finally:
            tmpmd.unlink(missing_ok=True)

    def test_es_banned_calques_empty_prints_stderr_note(self):
        # H1/H3: ES pack has banned_calques: [] → calque check is a silent
        # no-op; verify must print a maintainer note to STDERR (never stdout —
        # parse_verify_json scans stdout only).
        tmpmd = ROOT / "translate" / "llm" / "tests" / "_tmp_es_note_fixture.md"
        try:
            tmpmd.write_text(
                "### 1. titulo\n"
                "- Costo: 100\n"
                "- En términos sencillos: algo\n"
                "- Beneficio: 610 000 personas\n"
                "- Nivel de evidencia: A\n"
                "- Notas: algo mas\n",
                encoding="utf-8",
            )
            r = run_cli(
                [
                    sys.executable,
                    str(ROOT / "translate" / "steps" / "verify" / "verify.py"),
                    "01",
                    "--lang",
                    "es",
                    "--file",
                    str(tmpmd),
                    "--json",
                ],
            )
            self.assertIn("no banned_calques configured", r.stderr)
            data = parse_verify_json(r.stdout)
            self.assertIn("ok", data)
        finally:
            tmpmd.unlink(missing_ok=True)

    def test_ru_pack_calques_no_note(self):
        # RU falls back to built-in BANNED_RU (non-empty) → no note expected
        cand = ROOT / "book" / "ru" / "01-Не-умирайте-рано.md"
        if not cand.is_file():
            self.skipTest("no ru ch01")
        r = run_cli(
            [
                sys.executable,
                str(ROOT / "translate" / "steps" / "verify" / "verify.py"),
                "01",
                "--lang",
                "ru",
                "--file",
                str(cand),
                "--json",
            ],
        )
        self.assertNotIn("no banned_calques configured", r.stderr)

    def test_help_lists_json(self):
        r = run_cli(
            [sys.executable, str(ROOT / "translate" / "steps" / "verify" / "verify.py"), "--help"]
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("--json", r.stdout)


if __name__ == "__main__":
    unittest.main()
