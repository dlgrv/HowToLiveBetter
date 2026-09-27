"""Book-wide bureaucratese CLI uses rules JSON markers, not a second list."""

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

    def test_json_is_dict_of_lists(self):
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
            self.assertIsInstance(data, dict)
            self.assertTrue(data)
            rows = next(iter(data.values()))
            self.assertIsInstance(rows, list)
            self.assertIn("desc", rows[0])
            self.assertIn("match", rows[0])
            self.assertIn("order to", rows[0]["match"].lower())


if __name__ == "__main__":
    unittest.main()
