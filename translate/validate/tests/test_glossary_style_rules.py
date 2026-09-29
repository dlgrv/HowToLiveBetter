import json
import os
import sys
import tempfile
import unittest

from translate.lib import labels
from translate.llm.tests.helpers import run_cli
from translate.test_paths import REPO_ROOT

GLOSS = os.path.join(REPO_ROOT, "translate", "glossary.json")
RULES_RU = os.path.join(REPO_ROOT, "translate", "rules", "ru.json")
RULES_EN = os.path.join(REPO_ROOT, "translate", "rules", "en.json")


class TestGlossaryStyleRules(unittest.TestCase):
    def test_langs_have_distinctive_contract(self):
        rules = json.load(open(GLOSS, encoding="utf-8"))["style_rules"]
        for lang, needles in {
            "ru": ("падеж", "сорняков", "кальк"),
            "en": ("weedkiller", "neighbor", "bare"),
            "es": ("malas hierbas", "veneno"),
        }.items():
            self.assertIn(lang, rules)
            blob = "\n".join(rules[lang]).lower()
            self.assertTrue(any(n in blob for n in needles), lang)

    def test_glossary_has_no_banned_calques(self):
        data = json.load(open(GLOSS, encoding="utf-8"))
        self.assertNotIn("banned_calques", data)

    def test_soft_calques_in_rules(self):
        ru = json.load(open(RULES_RU, encoding="utf-8"))
        en = json.load(open(RULES_EN, encoding="utf-8"))
        self.assertIn("soft_calques", ru)
        self.assertIn("soft_calques", en)
        self.assertTrue(ru["soft_calques"] or en["soft_calques"])

    def test_hard_banned_unchanged_shape(self):
        # EN/ES HARD stay empty; RU HARD non-empty (byte contract for verify)
        self.assertEqual(labels.banned_calques("en", root=REPO_ROOT), [])
        self.assertEqual(labels.banned_calques("es", root=REPO_ROOT), [])
        self.assertTrue(labels.banned_calques("ru", root=REPO_ROOT))

    def test_book_flags_soft_calque(self):
        # EN soft_calques include "cohort" (former glossary-only WARN)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "unit.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("In this cohort the risk was higher.\n")
            proc = run_cli(
                [
                    sys.executable,
                    os.path.join(REPO_ROOT, "translate", "shelf", "style_check.py"),
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
            self.assertTrue(data, proc.stdout)
            blob = json.dumps(data, ensure_ascii=False).lower()
            self.assertIn("cohort", blob)


if __name__ == "__main__":
    unittest.main()
