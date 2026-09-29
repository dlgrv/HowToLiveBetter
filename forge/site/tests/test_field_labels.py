"""I18N field labels in translate/rules must appear in site/index.html entry parser.

Catches the PT bug: cards showed empty Custo/Benefício and Fontes(0) because
the markdown parser only listed CN/RU/ES/EN label alternates.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from translate.lib.config import default_root, translation_langs
from translate.lib.labels import field_labels, source_label

ROOT = Path(default_root())
INDEX = ROOT / "site" / "index.html"


def _parser_block() -> str:
    text = INDEX.read_text(encoding="utf-8")
    m = re.search(
        r"if \(entry\)\{([\s\S]*?)continue;\s*\n\s*\}",
        text,
    )
    assert m, "entry field parser block not found in site/index.html"
    return m.group(1)


class TestSiteFieldLabelCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block = _parser_block()

    def test_every_translation_lang_labels_appear_in_parser(self):
        missing: list[str] = []
        for lang in translation_langs(ROOT):
            labels = (*field_labels(lang, root=ROOT), source_label(lang, root=ROOT))
            missing.extend(f"{lang}:{label}" for label in labels if label not in self.block)
        self.assertEqual(
            missing,
            [],
            "site/index.html entry parser missing language field labels "
            "(cards will render empty cost/gain/sources)",
        )

    def test_pt_labels_parse_sample_lines(self):
        """Smoke: Portuguese lines must populate cost/gain/grade/src/note."""
        # Mirrors the alternates in site/index.html (keep in sync).
        cost = re.compile(r"^- (?:成本|Стоимость|Costo|Custo|Cost)[：:](.*)$")
        human = re.compile(
            r"^- (?:说人话|Простыми словами|En términos sencillos|Em linguagem simples|In plain terms)[：:](.*)$"
        )
        gain = re.compile(r"^- (?:收益|Эффект|Beneficio|Benefício|Benefit)[：:](.*)$")
        grade = re.compile(
            r"^- (?:证据等级|Уровень доказательности|Nivel de evidencia|Nível de evidência|Evidence grade)[：:]\s*([ABC])"
        )
        src = re.compile(r"^- (?:来源|Источники|Fuentes|Fontes|Sources)[：:]?(.*)$")
        note = re.compile(r"^- (?:备注|Примечания|Notas|Notes)[：:](.*)$")

        lines = {
            "cost": "- Custo: Nenhum custo.",
            "human": "- Em linguagem simples: Usar o cinto ajuda.",
            "gain": "- Benefício: Reduz cerca de 45%.",
            "grade": "- Nível de evidência: A",
            "src": "- Fontes:NHTSA (2024). <https://example.com>",
            "note": "- Notas: Também no banco de trás.",
        }
        self.assertTrue(cost.match(lines["cost"]))
        self.assertTrue(human.match(lines["human"]))
        self.assertTrue(gain.match(lines["gain"]))
        self.assertEqual(grade.match(lines["grade"]).group(1), "A")
        self.assertIn("https://example.com", src.match(lines["src"]).group(1))
        self.assertTrue(note.match(lines["note"]))


if __name__ == "__main__":
    unittest.main()
