import json
import os
import unittest

from tools.test_paths import REPO_ROOT

GLOSS = os.path.join(REPO_ROOT, "tools", "glossary.json")


class TestNameForms(unittest.TestCase):
    def test_bangladesh_prep(self):
        forms = json.load(open(GLOSS, encoding="utf-8"))["name_forms"]
        hit = [f for f in forms if f.get("form") == "в Бангладеше"]
        self.assertTrue(hit)
