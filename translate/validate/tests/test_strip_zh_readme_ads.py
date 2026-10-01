"""strip_zh_readme_ads applies fork overlays after upstream README sync."""

from forge.ops.strip_zh_readme_ads import (
    apply_fork_overlay,
    insert_language_table,
    remap_docs_links,
    remap_og_image,
    strip_ads,
)


def test_strips_reward_qr_and_keeps_license():
    text = (
        "## 许可\n\nCC BY\n\n## Star 走势\n\nchart\n\n## 赞赏\n\n"
        '<img src="ads/wechat-reward.png" alt="微信赞赏码" width="240">\n'
    )
    cleaned = strip_ads(text)
    assert "## 赞赏" not in cleaned
    assert "ads/wechat-reward.png" not in cleaned
    assert "## 许可" in cleaned
    assert "## Star 走势" in cleaned


def test_strips_ad_slot():
    text = "## 许可\n\nbody\n\n## 广告位\n\n[ad](ads/mcyyy.webp)\n"
    cleaned = strip_ads(text)
    assert "## 广告位" not in cleaned
    assert "ads/" not in cleaned
    assert "## 许可" in cleaned


def test_remap_docs_links_to_research():
    text = (
        "[核实](docs/核实记录/) · [长文](docs/结婚划不划算.md)\n"
        "[already](docs/research/结婚划不划算.md)\n"
    )
    cleaned = remap_docs_links(text)
    assert "](docs/research/核实记录/)" in cleaned
    assert "](docs/research/结婚划不划算.md)" in cleaned
    # Idempotent: research/ not doubled
    assert cleaned.count("docs/research/research/") == 0
    assert cleaned.count("](docs/research/结婚划不划算.md)") == 2


def test_remap_og_image():
    html = '<img src="og.png" alt="guide" width="820">\n'
    md = "![guide](og.png)\n"
    assert 'src="site/assets/og/zh.png"' in remap_og_image(html)
    assert "](site/assets/og/zh.png)" in remap_og_image(md)
    already = '<img src="site/assets/og/zh.png" alt="x">\n'
    assert remap_og_image(already) == already


def test_insert_language_table_from_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# EN\n\n"
        "| Language | Site | README | PDF | EPUB |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 🇬🇧 English | [site](https://example/en/) | [README.md](README.md) | [PDF](p.pdf) | [EPUB](e.epub) |\n"
        "| 🇧🇷 Português | [site](https://example/pt/) | [README.pt.md](README.pt.md) | [PDF](p.pdf) | [EPUB](e.epub) |\n"
        "\n---\n\n## Questions\n",
        encoding="utf-8",
    )
    zh = "# 中文\n\nintro\n\n## 这本书想回答的问题\n\nbody\n"
    out = insert_language_table(zh, str(tmp_path))
    assert "[README.md](README.md)" in out
    assert "README.pt.md" in out
    assert "| 语言 | 网站 | README | PDF | EPUB |" in out
    assert out.index("| 语言 |") < out.index("## 这本书想回答的问题")
    # Idempotent when table already present
    again = insert_language_table(out, str(tmp_path))
    assert again.count("[README.md](README.md)") == 1


def test_apply_fork_overlay_full(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "| Language | Site | README | PDF | EPUB |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 🇬🇧 English | [s](https://e/en/) | [README.md](README.md) | [P](p) | [E](e) |\n",
        encoding="utf-8",
    )
    upstream = (
        '<img src="og.png" alt="x" width="820">\n\n'
        "# 指南\n\n"
        "[核实](docs/核实记录/) · [长文](docs/结婚划不划算.md)\n\n"
        "## 这本书想回答的问题\n\n"
        "body\n\n"
        "## 赞赏\n\n"
        '<img src="ads/wechat-reward.png" alt="qr" width="240">\n'
    )
    out = apply_fork_overlay(upstream, repo_root=str(tmp_path))
    assert "## 赞赏" not in out
    assert 'src="site/assets/og/zh.png"' in out
    assert "](docs/research/核实记录/)" in out
    assert "](docs/research/结婚划不划算.md)" in out
    assert "[README.md](README.md)" in out
