import json, os, unittest
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLOSS = os.path.join(REPO, "tools", "glossary.json")

class TestNameForms(unittest.TestCase):
    def test_bangladesh_prep(self):
        forms = json.load(open(GLOSS, encoding="utf-8"))["name_forms"]
        hit = [f for f in forms if f.get("form") == "в Бангладеше"]
        self.assertTrue(hit)
