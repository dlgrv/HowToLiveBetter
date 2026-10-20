"""llms-full.txt generator over a staged publish tree."""

from forge.site import build_llms_full

LANGS = [
    {"code": "en", "contentRoot": "book/en", "readme": "README.md"},
    {"code": "ru", "contentRoot": "book/ru", "readme": "README.ru.md"},
    {"code": "zh", "contentRoot": "book", "readme": "README.zh.md"},
]


def _make_publish(tmp_path):
    pub = tmp_path / ".publish"
    (pub / "book" / "en").mkdir(parents=True)
    (pub / "book" / "ru").mkdir(parents=True)
    (pub / "README.md").write_text("# Book (en)")
    (pub / "README.ru.md").write_text("# Книга (ru)")
    (pub / "book" / "01-source.md").write_text("# 第一章")
    (pub / "book" / "en" / "01-source.md").write_text("# Chapter One")
    (pub / "book" / "ru" / "01-source.md").write_text("# Глава One")
    (pub / "book" / "en" / "99-late.md").write_text("# Chapter Ninety-Nine")
    return pub


def test_sections_order_is_readmes_then_chapters_per_lang(tmp_path):
    pub = _make_publish(tmp_path)
    urls = [s["url"] for s in build_llms_full.collect_sections(str(pub), LANGS)]

    assert urls == [
        "https://book.dlgrv.com/README.md",
        "https://book.dlgrv.com/README.ru.md",
        # chapters follow langs.json order (en, ru, zh); zh root is the bare book/
        "https://book.dlgrv.com/book/en/01-source.md",
        "https://book.dlgrv.com/book/en/99-late.md",
        "https://book.dlgrv.com/book/ru/01-source.md",
        "https://book.dlgrv.com/book/01-source.md",
    ]


def test_render_has_header_and_separators(tmp_path):
    pub = _make_publish(tmp_path)
    sections = build_llms_full.collect_sections(str(pub), LANGS)
    text = build_llms_full.render_llms_full(sections, "2026-10-21")

    assert text.startswith("# How to Live Better — full book")
    assert "https://book.dlgrv.com/llms.txt" in text
    assert "Generated: 2026-10-21" in text
    # every section header is a stable URL followed by its body
    assert "# https://book.dlgrv.com/book/en/01-source.md\n\n# Chapter One" in text
    assert text.count("\n---\n\n") == len(sections)


def test_write_llms_full_roundtrip(tmp_path):
    pub = _make_publish(tmp_path)
    count = build_llms_full.write_llms_full(str(pub), LANGS, "2026-10-21")

    out = pub / "llms-full.txt"
    assert out.is_file()
    assert count == 6
    assert "# Книга (ru)" in out.read_text(encoding="utf-8")
