import json
import os
import unittest

from tools.test_paths import REPO_ROOT

GLOSS = os.path.join(REPO_ROOT, "tools", "glossary.json")


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

    def test_banned_calques_ru_nonempty(self):
        data = json.load(open(GLOSS, encoding="utf-8"))
        self.assertTrue(data.get("banned_calques", {}).get("ru"))
