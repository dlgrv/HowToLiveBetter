"""Published-book gates must stay green in `make test` (same as CI content step)."""

import unittest

from forge.ops import check_content
from forge.ops.check_content import section_count_issues, stale_status_issues


class CheckContentRepoTest(unittest.TestCase):
    def test_repo_content_gates_pass(self):
        self.assertEqual(check_content.main(), 0)


def test_section_count_matches():
    text = "The text is split into 34 section files under [book/en/](book/en/)."
    assert section_count_issues("README.md", text, 34) == []


def test_section_count_mismatch():
    text = "The text is split into 33 section files under [book/en/](book/en/)."
    issues = section_count_issues("README.md", text, 34)
    assert len(issues) == 1
    assert "33" in issues[0]
    assert "34" in issues[0]


def test_section_count_sentence_required():
    assert section_count_issues("README.md", "no count here", 34)


def test_ru_and_zh_patterns():
    ru = "Текст разбит на 34 файла по главам в каталоге [book/ru/](book/ru/)."
    ru_one = "Текст разбит на 21 файл по главам."
    ru_many = "Текст разбит на 35 файлов по главам."
    zh = "正文按节拆成 34 个文件放在 [book/](book/)。"
    assert section_count_issues("README.ru.md", ru, 34) == []
    assert section_count_issues("README.ru.md", ru_one, 21) == []
    assert section_count_issues("README.ru.md", ru_many, 35) == []
    assert section_count_issues("README.zh.md", zh, 34) == []
    assert section_count_issues("README.ru.md", ru, 35)


def test_stale_in_progress_when_complete():
    text = "leer en el sitio — *traducción en curso*"
    issues = stale_status_issues(text, all_complete=True)
    assert issues
    assert "traducción en curso" in issues[0]


def test_in_progress_allowed_while_incomplete():
    text = "traducción en curso"
    assert stale_status_issues(text, all_complete=False) == []


def test_no_marker_when_complete():
    assert stale_status_issues("leer en el sitio", all_complete=True) == []
