"""Task 2 tests: judge prompt templates exist and carry mandatory schema sections.

Prompts are DATA (tools/prompts/judge-<mode>.md); the test enforces the
contract that validate scripts and the verdict parser rely on.
"""
import json
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROMPTS = os.path.join(REPO, "tools", "prompts")

ISSUE_TYPES = [
    "dropped_condition", "reversed_logic", "softened_claim", "added_advice",
    "subject_swapped", "cross_unit_contradiction", "invented", "other",
]


def read(mode):
    path = os.path.join(PROMPTS, f"judge-{mode}.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestScreenPrompt(unittest.TestCase):
    def test_exists_and_nonempty(self):
        self.assertGreater(len(read("screen")), 200)

    def test_mandatory_sections(self):
        p = read("screen")
        self.assertIn("verdict", p)
        for v in ("native", "translationese", "broken"):
            self.assertIn(f"`{v}`", p)
        self.assertIn("issues", p)
        self.assertIn("JSON", p.upper())

    def test_scope_limits(self):
        p = read("screen")
        # source-blind: only fluency; explicit bans on accuracy/terminology/numbers
        self.assertIn("accuracy", p.lower())
        self.assertIn("fluency", p.lower())
        # language-agnostic statement (ru or en)
        self.assertIn("Russian", p)
        self.assertIn("English", p)


class TestAbPrompt(unittest.TestCase):
    def test_mandatory_sections(self):
        p = read("ab")
        self.assertIn("winner", p)
        self.assertIn("tie", p)
        self.assertIn("VARIANT 1", p)
        self.assertIn("VARIANT 2", p)
        self.assertIn("JSON", p.upper())


class TestFactcheckPrompt(unittest.TestCase):
    def test_mandatory_sections(self):
        p = read("factcheck")
        self.assertIn("cn_span", p)
        self.assertIn("verbatim", p.lower())
        self.assertIn("issue_type", p)
        self.assertIn("JSON", p.upper())

    def test_taxonomy_complete(self):
        p = read("factcheck")
        for t in ISSUE_TYPES:
            self.assertIn(t, p)

    def test_service_lines_excluded(self):
        # CN input is pre-filtered by the orchestrator; prompt must not
        # instruct the judge to ground spans on §TAG§/§SRC§ lines.
        p = read("factcheck")
        self.assertIn("§", p)  # mentioned as excluded/banned
        self.assertLess(re.search(r"§SRC§", p).start(),
                        re.search(r"(?i)never|do not|must not", p).start() + 400)


class TestReplyParsing(unittest.TestCase):
    """Fixed sample replies (mock calls) must parse into objects w/o errors."""

    SAMPLES = {
        "screen": '{"verdict": "translationese", "issues": [{"span": "осуществляет ходьбу", "quote": "осуществляет ходьбу", "severity": "minor", "type": "calque"}], "note": ""}',  # noqa: E501
        "ab": '{"winner": 1, "reason": "variant 1 reads natural"}',
        "factcheck": json.dumps({
            "assertions": [
                {"cn_span": "每天至少30分钟", "claim": "30 min daily",
                 "ru_ok": True, "en_ok": True, "issue_type": None},
                {"cn_span": "不要空腹服药", "claim": "do not take on empty stomach",
                 "ru_ok": False, "en_ok": True, "issue_type": "dropped_condition"},
            ]}, ensure_ascii=False),
    }

    def test_samples_parse(self):
        for mode, raw in self.SAMPLES.items():
            obj = json.loads(raw)  # parser contract: strict JSON
            self.assertIsInstance(obj, dict)
        # screen verdict enum respected by sample
        self.assertIn(json.loads(self.SAMPLES["screen"])["verdict"],
                      ("native", "translationese", "broken"))
        fc = json.loads(self.SAMPLES["factcheck"])
        for a in fc["assertions"]:
            self.assertIn(a["issue_type"], ISSUE_TYPES + [None])


if __name__ == "__main__":
    unittest.main()
