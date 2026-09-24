"""Task 6 tests: style_check is WARN-only with corpus-driven markers.

Marker data lives in tools/rules/<lang>.json (style_markers + whitelist_zones);
the engine (tools/style_check.py) is language-agnostic.
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.pipeline import config as pconfig  # noqa: E402

CLEAN = """# 2. Не умирайте медленно

- **Ходите быстро по 30 минут в день.**
- Стоимость: 0 ₽.
- Простыми словами: быстрая ходьба снижает риск ранней смерти примерно на пятую часть.
- Эффект: HR 0.80 (95% CI 0.72–0.89), метаанализ 2023 года.
- Уровень доказательности: A
- Источники: https://doi.org/10.1000/example
- Примечания: подходит почти всем; начните с 10 минут.
"""

BUREAUCRATESE = """- **Осуществление реализации данного мероприятия является целесообразным.**
- Стоимость: 0 ₽.
- Простыми словами: в рамках осуществления данного мероприятия осуществляется ходьба.
- Эффект: HR 0.80 (95% CI 0.72–0.89).
- Уровень доказательности: A
- Источники: https://doi.org/10.1000/example
- Примечания: осуществлённый в рамках данного подхода, данным методом осуществляемый процесс является рекомендованным осуществляющими лицами.
"""

MEDICAL_PASSIVE = """- **Не прекращайте приём статинов.**
- Стоимость: 300 ₽/мес.
- Простыми словами: статина́ми снижается риск инфаркта; в Эффекте — цифры.
- Эффект: HR 0.75 (95% CI 0.70–0.81); назначение осуществляется врачом.
- Уровень доказательности: A
- Источники: https://doi.org/10.1000/example
- Примечания: данные получены в рандомизированных исследованиях; отмена согласовывается с врачом.
"""

DATA_NOUN = """- Простыми словами: данные получены из национального реестра, риск ниже на четверть.
"""

BANGLADESH_PLAIN = """- **Госпитализируйтесь при отравлении.**
- Стоимость: 0 ₽.
- Простыми словами: лечение в больницах в Бангладеш обходится дешевле, чем в соседних странах.
- Эффект: технический текст.
- Уровень доказательности: B
- Источники: https://doi.org/10.1000/example
- Примечания: в рамках осуществления данного мероприятия осуществляется наблюдение.
"""

BANGLADESH_CORRECT_PREP = """- **Госпитализируйтесь при отравлении.**
- Стоимость: 0 ₽.
- Простыми словами: из 257 случаев в больницах Бангладеша умерли 43.2%.
- Эффект: технический текст.
- Уровень доказательности: B
- Источники: https://doi.org/10.1000/example
- Примечания: в рамках осуществления данного мероприятия осуществляется наблюдение.
"""

BANGLADESH_CORRECT_IN = """- **Госпитализируйтесь при отравлении.**
- Стоимость: 0 ₽.
- Простыми словами: лечение в Бангладеше обходится дешевле, чем в соседних странах.
- Эффект: технический текст.
- Уровень доказательности: B
- Источники: https://doi.org/10.1000/example
- Примечания: в рамках осуществления данного мероприятия осуществляется наблюдение.
"""


def _bangladesh_marker_warns(warns):
    """Warnings tied to Bangladesh place-name calque / name_form checks."""
    out = []
    for w in warns:
        label = w.get("label", "")
        if "Бангладеш" in label or label.startswith("name_form:Бангладеш"):
            out.append(w)
            continue
        if label.startswith("calque:") and "Бангладеш" in w.get("span", ""):
            out.append(w)
    return out


class TestRulesData(unittest.TestCase):
    def test_ru_markers_filled(self):
        rules = pconfig.load_lang_rules("ru", root=ROOT)
        self.assertGreaterEqual(len(rules["style_markers"]), 5)
        for m in rules["style_markers"]:
            self.assertIn("pattern", m)
            self.assertIn("label", m)

    def test_ru_whitelist_zones(self):
        rules = pconfig.load_lang_rules("ru", root=ROOT)
        zones = " ".join(rules["whitelist_zones"])
        self.assertIn("Эффект", zones)
        self.assertIn("Примечания", zones)


class TestStyleCheck(unittest.TestCase):
    def _warns(self, text, lang="ru"):
        from tools.style_check import check_text
        return check_text(text, lang, root=ROOT)

    def test_clean_text_zero_warnings(self):
        self.assertEqual(self._warns(CLEAN), [])

    def test_bureaucratese_warns(self):
        warns = self._warns(BUREAUCRATESE)
        self.assertGreaterEqual(len(warns), 3)
        labels = {w["label"] for w in warns}
        self.assertTrue(any("осуществля" in l for l in labels))
        self.assertTrue(any("данн" in l for l in labels))
        self.assertTrue(any("является" in l for l in labels))

    def test_cap_per_category(self):
        warns = self._warns(BUREAUCRATESE)
        by_label = {}
        for w in warns:
            by_label[w["label"]] = by_label.get(w["label"], 0) + 1
        for label, n in by_label.items():
            self.assertLessEqual(n, 5, f"cap exceeded for {label}")

    def test_medical_passive_in_evidence_zone_zero(self):
        self.assertEqual(self._warns(MEDICAL_PASSIVE), [])

    def test_data_noun_zero(self):
        self.assertEqual(self._warns(DATA_NOUN), [])

    def test_engine_reads_rules_not_hardcoded(self):
        import tools.style_check as sc
        self.assertTrue(sc.load_markers("ru", root=ROOT))
        # engine must fail loudly for unknown language (config-driven)
        with self.assertRaises(ValueError):
            sc.load_markers("es", root=ROOT)

    def test_glossary_plain_only_flags_bangladesh_calque(self):
        from tools.style_check import check_text
        warns = check_text(BANGLADESH_PLAIN, "ru", root=ROOT, plain_only=True)
        spans = " ".join(w["span"] for w in warns)
        self.assertIn("Бангладеш", spans)
        labels = {w["label"] for w in warns}
        self.assertIn("name_form:Бангладеш", labels)
        self.assertFalse(any(l.startswith("calque:в Бангладеш") for l in labels))

    def test_bangladesh_correct_prep_plain_only_no_false_positive(self):
        from tools.style_check import check_text
        warns = check_text(BANGLADESH_CORRECT_IN, "ru", root=ROOT, plain_only=True)
        self.assertEqual(_bangladesh_marker_warns(warns), [])

    def test_bangladesh_pilot_genitive_plain_only_clean(self):
        from tools.style_check import check_text
        warns = check_text(BANGLADESH_CORRECT_PREP, "ru", root=ROOT, plain_only=True)
        self.assertEqual(_bangladesh_marker_warns(warns), [])

    def test_plain_only_scans_plain_line_only(self):
        from tools.style_check import check_text
        plain = check_text(BANGLADESH_PLAIN, "ru", root=ROOT, plain_only=True)
        self.assertTrue(plain)
        plain_line_no = next(
            i for i, ln in enumerate(BANGLADESH_PLAIN.splitlines(), 1)
            if ln.lstrip().startswith("- Простыми словами:")
        )
        self.assertEqual({w["line_no"] for w in plain}, {plain_line_no})


class TestCliAlwaysZero(unittest.TestCase):
    def test_cli_plain_only_warns_bangladesh(self):
        import subprocess, tempfile
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w") as f:
            f.write(BANGLADESH_PLAIN)
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "tools", "style_check.py"),
                 path, "--lang", "ru", "--plain-only"],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("Бангладеш", proc.stdout)
            self.assertIn("WARN", proc.stdout)
        finally:
            os.unlink(path)

    def test_cli_exit_zero_even_with_warnings(self):
        import subprocess, tempfile
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w") as f:
            f.write(BUREAUCRATESE)
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "tools", "style_check.py"),
                 path, "--lang", "ru"],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("WARN", proc.stdout)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
