"""Unit tests for translate.lib.paths helpers."""

import os
import unittest

from translate.lib.paths import _nn, cn_chapter_path, tr_chapter_path
from translate.test_paths import REPO_ROOT


class TestNn(unittest.TestCase):
    def test_pads(self):
        self.assertEqual(_nn(2), "02")
        self.assertEqual(_nn("01"), "01")
        self.assertEqual(_nn("3"), "03")


class TestChapterResolution(unittest.TestCase):
    def test_cn_and_tr_resolve_one_match(self):
        cases = [
            (1, "ru"),
            ("02", "en"),
            (3, "es"),
        ]
        for chapter, lang in cases:
            with self.subTest(chapter=chapter, lang=lang):
                cn = cn_chapter_path(REPO_ROOT, chapter)
                tr = tr_chapter_path(REPO_ROOT, chapter, lang)
                self.assertTrue(os.path.isfile(cn))
                self.assertTrue(os.path.isfile(tr))
                self.assertTrue(os.path.basename(cn).startswith(_nn(chapter) + "-"))
                self.assertTrue(os.path.basename(tr).startswith(_nn(chapter) + "-"))


if __name__ == "__main__":
    unittest.main()
