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
