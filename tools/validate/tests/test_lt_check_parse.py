"""Task 5: lt_check — parse LanguageTool JSON; server down → skip (never FAIL)."""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "lt_response_sample.json")

SAMPLE_MD = """# 1. Test

- **Walk fast.**
- Cost: $0.
- In plain terms: This is a sample plain-terms line for grammar checking.
- Benefit: HR 0.80.
- Evidence: A
- Sources: https://example.org/x
- Notes: advisory only.
"""


class TestLtParseResponse(unittest.TestCase):
    def test_parse_matches_nonempty(self):
        from tools.lt_check import parse_response

        with open(FIXTURE, encoding="utf-8") as f:
            data = json.load(f)
        hits = parse_response(data)
        self.assertIsInstance(hits, list)
        self.assertEqual(len(hits), 2)
        self.assertIn("message", hits[0])
        self.assertIn("rule_id", hits[0])
        self.assertEqual(hits[0]["rule_id"], "MORFOLOGIK_RULE_RU_RU")

    def test_parse_empty_matches(self):
        from tools.lt_check import parse_response

        hits = parse_response({"matches": []})
        self.assertEqual(hits, [])


class TestLtExtractPlain(unittest.TestCase):
    def test_extract_en_plain_only(self):
        from tools.lt_check import extract_plain_segments

        segs = extract_plain_segments(SAMPLE_MD, "en")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["line_no"], 5)
        self.assertIn("sample plain-terms", segs[0]["text"])

    def test_ru_label(self):
        from tools.lt_check import extract_plain_segments

        md = "- Простыми словами: быстрая ходьба снижает риск.\n"
        segs = extract_plain_segments(md, "ru")
        self.assertEqual(len(segs), 1)
        self.assertIn("быстрая ходьба", segs[0]["text"])


class TestLtCheckText(unittest.TestCase):
    def test_server_down_returns_skip(self):
        from tools.lt_check import check_text

        md = "- Простыми словами: тестовая строка.\n"
        result = check_text(md, "ru", base_url="http://127.0.0.1:1", timeout=0.5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "skip")
        self.assertEqual(result[0]["reason"], "server_down")

    def test_partial_failure_keeps_prior_hits(self):
        from tools import lt_check as lt

        md = (
            "- Простыми словами: первая строка.\n"
            "- Простыми словами: вторая строка.\n"
        )
        calls = {"n": 0}

        def fake_post(text, lang, base_url, timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"matches": [{
                    "message": "hit",
                    "offset": 0,
                    "length": 3,
                    "rule": {"id": "TEST"},
                }]}
            return None

        old = lt._post_check
        lt._post_check = fake_post
        try:
            result = lt.check_text(md, "ru", base_url="http://example.invalid")
        finally:
            lt._post_check = old
        self.assertTrue(any(r.get("rule_id") == "TEST" for r in result))
        self.assertTrue(any(r.get("reason") == "skip_partial" for r in result))

    def test_lt_lang_map(self):
        from tools.lt_check import lt_language_code

        self.assertEqual(lt_language_code("ru"), "ru-RU")
        self.assertEqual(lt_language_code("en"), "en-US")
        self.assertEqual(lt_language_code("es"), "es")


if __name__ == "__main__":
    unittest.main()
