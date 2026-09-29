"""Book-wide style CLI (--book) and deprecated bureaucratese shim."""

import json
import os
import sys
import tempfile
import unittest

from tools.llm.tests.helpers import run_cli
from tools.style_check import check_text
from tools.test_paths import REPO_ROOT


class TestBureaucrateseRules(unittest.TestCase):
    def test_former_profile_phrase_flags_via_rules(self):
        hits = check_text(
            "Walk in order to live longer.\n",
            "en",
            root=REPO_ROOT,
            include_glossary=False,
        )
        self.assertTrue(any(h["label"] == "in-order-to" for h in hits))

    def test_style_book_json(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "unit.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Walk in order to live longer.\n")
            proc = run_cli(
                [
                    sys.executable,
                    os.path.join(REPO_ROOT, "tools", "style_check.py"),
                    "--book",
                    "--lang",
                    "en",
                    "--dir",
                    td,
                    "--json",
                ]
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertIsInstance(data, dict)
            self.assertTrue(data)
            rows = next(iter(data.values()))
            self.assertIsInstance(rows, list)
            self.assertIn("desc", rows[0])
            self.assertIn("match", rows[0])
            self.assertIn("order to", rows[0]["match"].lower())

    def test_style_book_strict_exits_1(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "unit.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Walk in order to live longer.\n")
            proc = run_cli(
                [
                    sys.executable,
                    os.path.join(REPO_ROOT, "tools", "style_check.py"),
                    "--book",
                    "--lang",
                    "en",
                    "--dir",
                    td,
                    "--strict",
                ]
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_bureaucratese_shim_json(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "unit.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Walk in order to live longer.\n")
            proc = run_cli(
                [
                    sys.executable,
                    os.path.join(REPO_ROOT, "tools", "bureaucratese.py"),
                    "en",
                    "--dir",
                    td,
                    "--json",
                ]
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertTrue(data)
            self.assertIn("deprecated", proc.stderr.lower())


if __name__ == "__main__":
    unittest.main()
