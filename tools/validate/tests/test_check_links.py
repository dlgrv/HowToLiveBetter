"""Tests for tools/check_links.py — markdown link checker."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _setup_repo(tmp):
    """Copy real check_links.py and create a controlled file structure."""
    tools_dir = os.path.join(tmp, "tools")
    os.makedirs(tools_dir)
    shutil.copy2(
        os.path.join(REPO_ROOT, "tools", "check_links.py"),
        os.path.join(tools_dir, "check_links.py"))

    # Root-level README
    with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Test\n[link](book/ru/01.md)\n[broken](nonexistent.md)\n")

    # book/ tree
    book_ru = os.path.join(tmp, "book", "ru")
    os.makedirs(book_ru)
    with open(os.path.join(book_ru, "01.md"), "w", encoding="utf-8") as f:
        f.write("# 01\n[back](../../README.md)\n")

    # docs/ tree
    docs = os.path.join(tmp, "docs")
    os.makedirs(docs)
    with open(os.path.join(docs, "guide.md"), "w", encoding="utf-8") as f:
        f.write("# Guide\n[home](../README.md)\n")
    with open(os.path.join(docs, "broken.md"), "w", encoding="utf-8") as f:
        f.write("# Broken\n[dead](ghost.md)\n")

    # file with code-fenced link (should be skipped)
    with open(os.path.join(tmp, "book", "code.md"), "w", encoding="utf-8") as f:
        f.write("""# Code sample
Real link: [works](../README.md)

```md
[fake](ghost.md)
```

More real: [also works](../docs/guide.md)
""")

    # file with external links (should be skipped)
    with open(os.path.join(tmp, "book", "external.md"), "w", encoding="utf-8") as f:
        f.write("""# External
[github](https://github.com)
[mail](mailto:a@b.com)
[fragment](#section)
""")

    return tools_dir


def _run(tmp):
    check_py = os.path.join(tmp, "tools", "check_links.py")
    return subprocess.run(
        [sys.executable, check_py],
        capture_output=True, text=True, timeout=10
    )


class TestCheckLinks(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tools_dir = _setup_repo(self.tmp)

    # ---- valid links ----

    def test_all_good_link(self):
        # Remove broken.md with its dead link, remove the intentional broken from README
        os.remove(os.path.join(self.tmp, "docs", "broken.md"))
        # Fix README: remove the broken link
        with open(os.path.join(self.tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Test\n[link](book/ru/01.md)\n")
        r = _run(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    # ---- broken links ----

    def test_broken_link_detected(self):
        r = _run(self.tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("BROKEN LINKS", r.stdout)

    def test_broken_root_readme(self):
        r = _run(self.tmp)
        self.assertIn("nonexistent.md", r.stdout)

    def test_broken_docs_ghost(self):
        r = _run(self.tmp)
        self.assertIn("ghost.md", r.stdout)

    # ---- code fence skipping ----

    def test_code_fence_links_skipped(self):
        # code.md has a [fake](ghost.md) inside a code fence — should NOT be flagged
        # But code.md also has real links that resolve — remove broken.md to isolate
        os.remove(os.path.join(self.tmp, "docs", "broken.md"))
        with open(os.path.join(self.tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Test\n[link](book/ru/01.md)\n")
        r = _run(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)
        # No 'ghost' in output — code-fenced link was skipped
        self.assertNotIn("ghost", r.stdout)

    # ---- external links skipped ----

    def test_external_links_skipped(self):
        os.remove(os.path.join(self.tmp, "docs", "broken.md"))
        with open(os.path.join(self.tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Test\n[link](book/ru/01.md)\n")
        r = _run(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)
        # External links should not appear in broken list
        self.assertNotIn("https://", r.stdout)
        self.assertNotIn("mailto:", r.stdout)


if __name__ == "__main__":
    unittest.main()