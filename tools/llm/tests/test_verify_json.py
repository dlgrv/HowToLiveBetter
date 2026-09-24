#!/usr/bin/env python3
"""Tests for tools/verify.py --json (machine report for repair wave)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class VerifyJson(unittest.TestCase):
    def test_json_flag_emits_object_with_fails(self):
        # Use existing ch01 candidate if present; else skip
        cand = ROOT / "tools" / "runs" / "active" / "ru" / "01" / "assembled.md"
        if not cand.is_file():
            self.skipTest("no assembled candidate")
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "verify.py"),
                "01",
                "--lang",
                "ru",
                "--file",
                str(cand),
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        # May be exit 0 or 1; JSON is the LAST stdout line (also on FAIL) —
        # rfind("{") alone would land inside the object, so parse by line.
        text = r.stdout
        js_line = next(
            (l for l in reversed(text.splitlines()) if l.startswith("{")),
            None,
        )
        self.assertIsNotNone(js_line, text[:500])
        data = json.loads(js_line)
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

    def test_es_banned_calques_empty_prints_stderr_note(self):
        # H1/H3: ES pack has banned_calques: [] → calque check is a silent
        # no-op; verify must print a maintainer note to STDERR (never stdout —
        # parse_verify_json scans stdout only).
        tmpmd = ROOT / "tools" / "llm" / "tests" / "_tmp_es_note_fixture.md"
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
            r = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "verify.py"), "01",
                 "--lang", "es", "--file", str(tmpmd), "--json"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertIn("no banned_calques configured", r.stderr)
            js_line = next(
                (l for l in reversed(r.stdout.splitlines()) if l.startswith("{")),
                None,
            )
            self.assertIsNotNone(js_line, r.stdout[:500])
            data = json.loads(js_line)
            self.assertIn("ok", data)
        finally:
            tmpmd.unlink(missing_ok=True)

    def test_ru_pack_calques_no_note(self):
        # RU falls back to built-in BANNED_RU (non-empty) → no note expected
        cand = ROOT / "book" / "ru" / "01-Не-умирайте-рано.md"
        if not cand.is_file():
            self.skipTest("no ru ch01")
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "verify.py"), "01",
             "--lang", "ru", "--file", str(cand), "--json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertNotIn("no banned_calques configured", r.stderr)

    def test_help_lists_json(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "verify.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("--json", r.stdout)


if __name__ == "__main__":
    unittest.main()
