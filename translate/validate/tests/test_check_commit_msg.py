"""Tests for forge/ops/check_commit_msg.py."""

import os
import subprocess
import sys
import unittest

from forge.ops.check_commit_msg import validate

from translate.test_paths import REPO_ROOT

SCRIPT = os.path.join(REPO_ROOT, "forge", "ops", "check_commit_msg.py")


class ValidateUnit(unittest.TestCase):
    def test_good_simple(self):
        self.assertEqual(validate("fix: restore V2 editorial templates"), [])

    def test_good_scoped(self):
        self.assertEqual(
            validate("translation(ru): chapter 02"),
            [],
        )

    def test_good_with_body(self):
        msg = "feat(pipeline): add make og target\n\nRegenerate locale previews."
        self.assertEqual(validate(msg), [])

    def test_good_breaking_bang(self):
        self.assertEqual(validate("feat(pipeline)!: rename wave output dir"), [])

    def test_good_sync_quality(self):
        self.assertEqual(validate("sync: pull upstream chapters 03, 08"), [])
        self.assertEqual(validate("quality(ru): strip bureaucratese markers"), [])

    def test_merge_allowed(self):
        self.assertEqual(
            validate("Merge pull request #51 from dlgrv/quality/pipeline-v2"),
            [],
        )

    def test_revert_allowed(self):
        self.assertEqual(validate('Revert "fix: broken redirect"'), [])

    def test_reject_cyrillic(self):
        errs = validate("feat: единый V2-дизайн OG")
        self.assertTrue(any("English" in e for e in errs))

    def test_reject_cjk(self):
        errs = validate("fix: 第 5 节加两条")
        self.assertTrue(any("English" in e for e in errs))

    def test_reject_bad_type(self):
        errs = validate("wip: temporary stash")
        self.assertTrue(any("must match" in e for e in errs))

    def test_reject_uppercase_desc(self):
        errs = validate("fix: Restore templates")
        self.assertTrue(any("lowercase" in e for e in errs))

    def test_reject_trailing_period(self):
        errs = validate("fix: restore templates.")
        self.assertTrue(any("period" in e for e in errs))

    def test_reject_missing_blank_line(self):
        errs = validate("fix: restore templates\nMore detail without blank line")
        self.assertTrue(any("blank line" in e for e in errs))

    def test_reject_cursor_trailer(self):
        msg = "fix: restore templates\n\nCo-authored-by: Cursor <cursoragent@cursor.com>"
        errs = validate(msg)
        self.assertTrue(any("Cursor" in e for e in errs))

    def test_reject_empty(self):
        errs = validate("   \n# comment only\n")
        self.assertTrue(any("empty" in e for e in errs))

    def test_strip_git_comments(self):
        msg = "fix: restore templates\n\n# Please enter the commit message\n"
        self.assertEqual(validate(msg), [])


class CliIntegration(unittest.TestCase):
    def _run(self, message: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, SCRIPT, "--stdin"],
            input=message,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

    def test_cli_pass(self):
        r = self._run("chore: ignore pipeline run state")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_cli_fail(self):
        r = self._run("bad message without type")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR", r.stderr)


if __name__ == "__main__":
    unittest.main()
