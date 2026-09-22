"""Tests for render_markup diff highlighting (neutral, symmetric-ish)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from tools.validate.render_markup import diff_texts, diff_words  # noqa: E402


class TestDiffWords(unittest.TestCase):
    def test_identical_no_marks(self):
        h1, h2 = diff_words("раз два три", "раз два три")
        self.assertNotIn("<mark>", h1)
        self.assertNotIn("<mark>", h2)

    def test_difference_marked_both_sides(self):
        h1, h2 = diff_words("он пришёл домой", "он вернулся домой")
        self.assertIn("<mark>пришёл</mark>", h1)
        self.assertIn("<mark>вернулся</mark>", h2)
        self.assertIn("домой", h1)

    def test_total_replacement_marks_whole_line(self):
        h1, h2 = diff_words("совершенно другой текст здесь", "яйца")
        self.assertTrue(h1.startswith("<mark>"))
        self.assertTrue(h2.startswith("<mark>"))


class TestDiffTexts(unittest.TestCase):
    def test_identical_texts_untouched(self):
        t = "строка один\nстрока два\nстрока три"
        h1, h2 = diff_texts(t, t)
        self.assertNotIn("<mark>", h1 + h2)

    def test_inserted_line_marked_only_in_second(self):
        h1, h2 = diff_texts("а\nб", "а\nX\nб")
        self.assertNotIn("<mark>", h1)
        self.assertIn("<mark>X</mark>", h2)

    def test_html_escaped(self):
        h1, _ = diff_texts("a <b> c", "a <b> d")
        self.assertNotIn("<b>", h1.replace("<mark>", ""))
        self.assertIn("&lt;b&gt;", h1)


if __name__ == "__main__":
    unittest.main()
