"""Tests for tools/make_digest.py — chapter splitting into translation units.

Runs the REAL make_digest.py in a temp repo mirror.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# -------- shared fixtures --------

CN_SIMPLE = """# 1. Не умирайте рано

Как жить долго и счастливо.

### 1. Бросьте курить

<!-- 成本标签: 钱=0 时间=少 毅力=是 收益=大 口径=死亡率 -->

- 成本：意志力
- 说人话：курение убивает
- 收益：+10 лет жизни
- 证据等级：A
- 来源：Jha P 等 (2013). NEJM.
- 备注：пассивное курение тоже

### 2. Ходите пешком

<!-- 成本标签: 钱=0 时间=средне 毅力=да 收益=средняя 口径=смертность -->

- 成本：30 минут в день
- 说人话：ходьба снижает риск смерти
- 收益：HR 0.80
- 证据等级：A
- 来源：Smith et al. (2022)
- 来源：Jones et al. (2023)
- 备注：начните с 10 минут
"""

CN_NO_ITEMS = """# 99. Пустая глава

Это глава без рекомендаций.
"""

CN_SINGLE_ITEM = """# 50. Одна рекомендация

Какой-то вводный текст.

### 1. Единственный совет

<!-- 成本标签: 钱=0 时间=мало 毅力=да 收益=средняя 口径=всё -->

- 成本：5 минут
- 说人话：делайте зарядку
- 收益：лучше спите
- 证据等级：B
- 来源：WHO Guidelines 2020
"""

CN_NO_TAG = """# 77. Без тэга

### 1. Совет без тэга

- 成本：бесплатно
- 说人话：гуляйте больше
- 收益：лучше настроение
- 来源：Obvious Studies (2025)
"""

GLOSSARY = {
    "terms": [
        {"cn": "死亡率", "ru": "смертность", "en": "mortality"},
        {"cn": "证据等级", "ru": "уровень доказательности", "en": "evidence level"},
        {"cn": "成本", "ru": "стоимость", "en": "cost"},
    ],
    "style_rules": {
        "ru": ["Избегай канцелярита."],
        "en": ["Prefer active voice."]
    }
}


def _setup_tmp_repo(tmp, chapter_n, cn_content, glossary=None):
    """Mirror repo structure so the REAL make_digest.py runs."""
    tools_dir = os.path.join(tmp, "tools")
    os.makedirs(tools_dir)
    shutil.copy2(
        os.path.join(REPO_ROOT, "tools", "make_digest.py"),
        os.path.join(tools_dir, "make_digest.py"))

    book_dir = os.path.join(tmp, "book")
    os.makedirs(book_dir)
    with open(os.path.join(book_dir, f"{chapter_n}-test.md"), "w", encoding="utf-8") as f:
        f.write(cn_content)

    if glossary is not None:
        with open(os.path.join(tools_dir, "glossary.json"), "w", encoding="utf-8") as f:
            json.dump(glossary, f, ensure_ascii=False)


def _run_digest(tmp, n):
    digest_py = os.path.join(tmp, "tools", "make_digest.py")
    return subprocess.run(
        [sys.executable, digest_py, str(n)],
        capture_output=True, text=True, timeout=10
    )


def _digest_dir(tmp, n):
    return os.path.join(tmp, "tools", "digest", str(n))


class TestMakeDigest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    # ---- basics ----

    def test_split_two_items(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE, GLOSSARY)
        r = _run_digest(self.tmp, "01")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2 units", r.stdout)

        d = _digest_dir(self.tmp, "01")
        self.assertTrue(os.path.exists(os.path.join(d, "units", "00.md")))
        self.assertTrue(os.path.exists(os.path.join(d, "units", "01.md")))
        self.assertTrue(os.path.exists(os.path.join(d, "units", "02.md")))
        self.assertTrue(os.path.exists(os.path.join(d, "blocks.json")))

        with open(os.path.join(d, "blocks.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["items"], 2)
        self.assertEqual(len(meta["blocks"]), 2)
        self.assertIn("<!-- 成本标签", meta["blocks"]["1"]["tag"])

    def test_units_have_markers(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE, GLOSSARY)
        _run_digest(self.tmp, "01")
        d = _digest_dir(self.tmp, "01")

        with open(os.path.join(d, "units", "01.md"), encoding="utf-8") as f:
            unit1 = f.read()
        self.assertIn("§TAG§", unit1)
        self.assertIn("§SRC§", unit1)
        self.assertNotIn("<!-- 成本标签", unit1)

    def test_unit_00_is_head(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE, GLOSSARY)
        _run_digest(self.tmp, "01")
        d = _digest_dir(self.tmp, "01")

        with open(os.path.join(d, "units", "00.md"), encoding="utf-8") as f:
            head = f.read()
        self.assertIn("Не умирайте рано", head)
        self.assertNotIn("###", head)

    def test_no_items_chapter(self):
        _setup_tmp_repo(self.tmp, "99", CN_NO_ITEMS, GLOSSARY)
        r = _run_digest(self.tmp, "99")
        self.assertEqual(r.returncode, 0)
        self.assertIn("0 units", r.stdout)

        d = _digest_dir(self.tmp, "99")
        with open(os.path.join(d, "blocks.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["items"], 0)

    def test_single_item(self):
        _setup_tmp_repo(self.tmp, "50", CN_SINGLE_ITEM, GLOSSARY)
        r = _run_digest(self.tmp, "50")
        self.assertEqual(r.returncode, 0)
        self.assertIn("1 units", r.stdout)

    def test_missing_chapter_exits(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE, GLOSSARY)
        r = _run_digest(self.tmp, "99")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stdout + r.stderr)

    # ---- glossary ----

    def test_glossary_injection(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE, GLOSSARY)
        _run_digest(self.tmp, "01")
        d = _digest_dir(self.tmp, "01")

        self.assertTrue(os.path.exists(os.path.join(d, "units", "00.gloss.md")))
        with open(os.path.join(d, "units", "00.gloss.md"), encoding="utf-8") as f:
            gloss00 = f.read()
        self.assertIn("死亡率 → RU", gloss00)
        self.assertIn("证据等级 → RU", gloss00)
        self.assertIn("[STYLE RU]", gloss00)
        self.assertIn("[STYLE EN]", gloss00)

        self.assertTrue(os.path.exists(os.path.join(d, "units", "01.gloss.md")))
        with open(os.path.join(d, "units", "01.gloss.md"), encoding="utf-8") as f:
            gloss01 = f.read()
        self.assertIn("证据等级", gloss01)
        self.assertIn("成本", gloss01)
        self.assertNotIn("死亡率", gloss01)  # only in tag, excluded from body
        self.assertNotIn("[STYLE", gloss01)

    def test_no_glossary_file(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE)  # no glossary arg
        r = _run_digest(self.tmp, "01")
        self.assertEqual(r.returncode, 0)
        d = _digest_dir(self.tmp, "01")
        self.assertFalse(os.path.exists(os.path.join(d, "units", "00.gloss.md")))

    # ---- edge cases ----

    def test_multiple_sources(self):
        _setup_tmp_repo(self.tmp, "01", CN_SIMPLE, GLOSSARY)
        _run_digest(self.tmp, "01")
        d = _digest_dir(self.tmp, "01")

        with open(os.path.join(d, "blocks.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(len(meta["blocks"]["2"]["src"]), 2)
        self.assertIn("Smith et al. (2022)", meta["blocks"]["2"]["src"][0])
        self.assertIn("Jones et al. (2023)", meta["blocks"]["2"]["src"][1])

    def test_item_without_tag(self):
        _setup_tmp_repo(self.tmp, "77", CN_NO_TAG, GLOSSARY)
        r = _run_digest(self.tmp, "77")
        self.assertEqual(r.returncode, 0)

        d = _digest_dir(self.tmp, "77")
        with open(os.path.join(d, "blocks.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["blocks"]["1"]["tag"], "")

        with open(os.path.join(d, "units", "01.md"), encoding="utf-8") as f:
            unit = f.read()
        self.assertIn("§TAG§", unit)


if __name__ == "__main__":
    unittest.main()