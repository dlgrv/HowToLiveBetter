"""Tests for tools/assemble.py — unit assembly and integrity checks.

Runs the REAL assemble.py in a temp repo mirror.
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

CN_CHAPTER = """# 1. Не умирайте рано

Как жить долго и счастливо.

### 1. Бросьте курить

<!-- 成本标签: 钱=0 时间=少 毅力=是 收益=大 口径=死亡率 -->

- 成本：意志力
- 说人话：курение убивает
- 收益：+10 лет жизни
- 证据等级：A
- 来源：Jha P 等 (2013). NEJM. https://doi.org/10.1056/NEJMsa1211128
- 备注：пассивное курение тоже

### 2. Ходите пешком

<!-- 成本标签: 钱=0 时间=средне 毅力=да 收益=средняя 口径=смертность -->

- 成本：30 минут в день
- 说人话：ходьба снижает риск смерти
- 收益：HR 0.80
- 证据等级：A
- 来源：Smith et al. (2022)
- 备注：начните с 10 минут

### 3. Отказ от сладкого

<!-- 成本标签: 钱=0 时间=мало 毅力=да 收益=средняя 口径=здоровье -->

- 成本：сила воли
- 说人话：сахар = яд
- 收益：-5 кг за год
- 证据等级：B
- 来源：Lustig RH (2012). Nature. https://doi.org/10.1038/482027a
"""

RU_INTRO = """# 1. Не умирайте рано

[← Назад к оглавлению](../README.md)

Курение — главная предотвратимая причина смерти. В этой главе — конкретные шаги.
"""

RU_UNIT_01 = """### 1. Бросьте курить

- Стоимость: сила воли на несколько недель
- Простыми словами: курение убивает — курильщики живут в среднем на 10 лет меньше.
- Эффект: +10 лет жизни при отказе до 40 лет.
- Уровень доказательности: A
- Примечания: пассивное курение тоже опасно.
§TAG§
§SRC§
"""

RU_UNIT_02 = """### 2. Ходите пешком

- Стоимость: 30 минут в день
- Простыми словами: быстрая ходьба снижает риск ранней смерти на 20%.
- Эффект: HR 0.80 (95% CI 0.72–0.89)
- Уровень доказательности: A
- Примечания: начните с 10 минут, постепенно увеличивайте до 30.
§TAG§
§SRC§
"""

RU_UNIT_03 = """### 3. Отказ от сладкого

- Стоимость: сила воли на первые 2 недели
- Простыми словами: добавленный сахар — чистый яд, никакой пользы.
- Эффект: −5 кг за год при полном отказе от сладких напитков.
- Уровень доказательности: B
- Примечания: фрукты и ягоды — исключение, их можно.
§TAG§
§SRC§
"""

BLOCKS_JSON = {
    "items": 3,
    "blocks": {
        "1": {
            "tag": "<!-- 成本标签: 钱=0 时间=少 毅力=是 收益=大 口径=死亡率 -->",
            "src": [
                "- 来源：Jha P 等 (2013). NEJM. https://doi.org/10.1056/NEJMsa1211128"
            ]
        },
        "2": {
            "tag": "<!-- 成本标签: 钱=0 时间=средне 毅力=да 收益=средняя 口径=смертность -->",
            "src": [
                "- 来源：Smith et al. (2022)"
            ]
        },
        "3": {
            "tag": "<!-- 成本标签: 钱=0 时间=мало 毅力=да 收益=средняя 口径=здоровье -->",
            "src": [
                "- 来源：Lustig RH (2012). Nature. https://doi.org/10.1038/482027a"
            ]
        }
    }
}


def _setup_tmp_fixtures(tmp):
    """Mirror repo structure so the REAL assemble.py runs with root = tmp."""
    # Copy real assemble.py
    tools_dir = os.path.join(tmp, "tools")
    os.makedirs(tools_dir)
    shutil.copy2(
        os.path.join(REPO_ROOT, "tools", "assemble.py"),
        os.path.join(tools_dir, "assemble.py"))

    # CN original
    book_dir = os.path.join(tmp, "book")
    os.makedirs(book_dir)
    with open(os.path.join(book_dir, "01-不要早死.md"), "w", encoding="utf-8") as f:
        f.write(CN_CHAPTER)

    # digest blocks.json
    digest_dir = os.path.join(tmp, "tools", "digest", "01")
    os.makedirs(digest_dir)
    with open(os.path.join(digest_dir, "blocks.json"), "w", encoding="utf-8") as f:
        json.dump(BLOCKS_JSON, f)


def _setup_workdir(workdir):
    """Create run/ru/01/units/ with standard fixtures."""
    units_dir = os.path.join(workdir, "units")
    os.makedirs(units_dir)
    with open(os.path.join(units_dir, "00.md"), "w", encoding="utf-8") as f:
        f.write(RU_INTRO)
    with open(os.path.join(units_dir, "01.md"), "w", encoding="utf-8") as f:
        f.write(RU_UNIT_01)
    with open(os.path.join(units_dir, "02.md"), "w", encoding="utf-8") as f:
        f.write(RU_UNIT_02)
    with open(os.path.join(units_dir, "03.md"), "w", encoding="utf-8") as f:
        f.write(RU_UNIT_03)


def _run_assemble(tmp, workdir, out_md, lang="ru"):
    assemble_py = os.path.join(tmp, "tools", "assemble.py")
    return subprocess.run(
        [sys.executable, assemble_py, "01", workdir, out_md, lang],
        capture_output=True, text=True, timeout=10
    )


def _blocks_path(tmp):
    return os.path.join(tmp, "tools", "digest", "01", "blocks.json")


def _write_blocks(tmp, blocks):
    with open(_blocks_path(tmp), "w", encoding="utf-8") as f:
        json.dump(blocks, f)


class TestAssemble(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _setup_tmp_fixtures(self.tmp)
        self.workdir = os.path.join(self.tmp, "run", "ru", "01")
        _setup_workdir(self.workdir)
        self.out_md = os.path.join(self.tmp, "out.md")

    def _run(self, lang="ru"):
        return _run_assemble(self.tmp, self.workdir, self.out_md, lang)

    # ---- basics ----

    def test_correct_assembly_ok(self):
        r = self._run("ru")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK ch.01", r.stdout)
        self.assertIn("items=3", r.stdout)
        self.assertIn("tags=3", r.stdout)
        self.assertIn("sources=3", r.stdout)

    def test_output_contains_translated_content(self):
        self._run("ru")
        with open(self.out_md, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("Не умирайте рано", out)
        self.assertIn("Бросьте курить", out)
        self.assertIn("Ходите пешком", out)
        self.assertIn("Отказ от сладкого", out)
        self.assertIn("Стоимость:", out)
        self.assertIn("Простыми словами:", out)

    def test_output_sources_byte_identical(self):
        self._run("ru")
        with open(self.out_md, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("- Источники:Jha P 等 (2013). NEJM. https://doi.org/10.1056/NEJMsa1211128", out)
        self.assertIn("- Источники:Smith et al. (2022)", out)
        self.assertIn("- Источники:Lustig RH (2012). Nature. https://doi.org/10.1038/482027a", out)

    def test_output_has_tags(self):
        self._run("ru")
        with open(self.out_md, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("<!-- 成本标签:", out)

    # ---- error cases ----

    def test_missing_unit_fails(self):
        os.remove(os.path.join(self.workdir, "units", "02.md"))
        r = self._run("ru")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unit 02 missing", r.stdout)

    def test_extra_unit_ignored(self):
        with open(os.path.join(self.workdir, "units", "04.md"), "w", encoding="utf-8") as f:
            f.write("### 4. Extra\n§TAG§\n§SRC§\n")
        r = self._run("ru")
        self.assertEqual(r.returncode, 0)
        self.assertIn("OK ch.01", r.stdout)

    def test_missing_src_marker_fails(self):
        bad = RU_UNIT_01.replace("§SRC§", "")
        with open(os.path.join(self.workdir, "units", "01.md"), "w", encoding="utf-8") as f:
            f.write(bad)
        r = self._run("ru")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("§SRC§ marker not found", r.stdout)

    def test_leftover_placeholder_fails(self):
        bad = RU_UNIT_01 + "\n§EXTRA§\n"
        with open(os.path.join(self.workdir, "units", "01.md"), "w", encoding="utf-8") as f:
            f.write(bad)
        r = self._run("ru")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("leftover placeholder", r.stdout)

    # ---- integrity checks ----

    def test_source_mismatch_fails(self):
        blocks = json.loads(json.dumps(BLOCKS_JSON))
        blocks["blocks"]["1"]["src"] = ["- 来源：Tampered source line"]
        _write_blocks(self.tmp, blocks)
        r = self._run("ru")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("source line mismatch", r.stdout)

    def test_tag_count_mismatch_fails(self):
        blocks = json.loads(json.dumps(BLOCKS_JSON))
        blocks["blocks"]["2"]["tag"] = ""
        _write_blocks(self.tmp, blocks)
        r = self._run("ru")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tags", r.stdout)

    def test_items_count_mismatch_fails(self):
        bad = RU_UNIT_02.replace("### 2.", "## 2.")
        with open(os.path.join(self.workdir, "units", "02.md"), "w", encoding="utf-8") as f:
            f.write(bad)
        r = self._run("ru")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("items", r.stdout)

    # ---- hanzi detection ----

    def test_hanzi_body_warning_not_fail(self):
        bad = RU_UNIT_01 + "\n这行没翻译\n"
        with open(os.path.join(self.workdir, "units", "01.md"), "w", encoding="utf-8") as f:
            f.write(bad)
        r = self._run("ru")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("warning:", r.stdout)
        self.assertIn("untranslated lines", r.stdout)

    # ---- languages ----

    def test_lang_en(self):
        r = self._run("en")
        self.assertEqual(r.returncode, 0)
        with open(self.out_md, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("- Sources:", out)

    def test_lang_es(self):
        r = self._run("es")
        self.assertEqual(r.returncode, 0)
        with open(self.out_md, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("- Fuentes:", out)


if __name__ == "__main__":
    unittest.main()