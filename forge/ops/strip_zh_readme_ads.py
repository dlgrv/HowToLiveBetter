#!/usr/bin/env python3
"""Apply fork overlays to README.zh.md after a path-filtered upstream sync.

Upstream README.md ends with a 「广告位」 section linking ads/, and a 「赞赏」
reward QR that also lives under ads/. This fork does not carry ads in its
READMEs. Strip both sections whenever README.zh.md is refreshed from upstream
so the next sync does not reintroduce them.

Also remaps upstream paths that this fork relocates:
- markdown ``](docs/…`` → ``](docs/research/…`` (idempotent if already remapped)
- hero ``og.png`` → ``site/assets/og/zh.png``
- Pages search URLs ``eternity4719.github.io/HowToLiveBetter/`` →
  ``dlgrv.github.io/HowToLiveBetter/zh/``
- inserts the shipped-language table from root README.md when missing
  (detected by absence of ``[README.md](README.md)``)
"""

from __future__ import annotations

import os
import re
import sys

ADS_SECTION_RE = re.compile(
    r"\n## 广告位\n.*\Z",
    re.DOTALL,
)
REWARD_SECTION_RE = re.compile(
    r"\n## 赞赏\n.*\Z",
    re.DOTALL,
)
# Match ](docs/X but not ](docs/research/
DOCS_LINK_RE = re.compile(r"\]\(docs/(?!research/)")
LANG_TABLE_RE = re.compile(
    r"\| Language \| Site \| README \| PDF \| EPUB \|\n"
    r"\| --- \| --- \| --- \| --- \| --- \|\n"
    r"(?:\| .*\n)+",
)
FIRST_H2_RE = re.compile(r"^## ", re.MULTILINE)


def strip_ads(text: str) -> str:
    text = ADS_SECTION_RE.sub("\n", text)
    text = REWARD_SECTION_RE.sub("\n", text)
    return text.rstrip() + "\n"


def remap_docs_links(text: str) -> str:
    return DOCS_LINK_RE.sub("](docs/research/", text)


def remap_og_image(text: str) -> str:
    # Cover both <img src="og.png"> and markdown ![…](og.png)
    text = re.sub(r'src="(?:\.\/)?og\.png"', 'src="site/assets/og/zh.png"', text)
    return re.sub(r"\]\((?:\.\/)?og\.png\)", "](site/assets/og/zh.png)", text)


def remap_pages_urls(text: str) -> str:
    """Point Chinese search-page links at this fork's /zh/ site."""
    return text.replace(
        "https://eternity4719.github.io/HowToLiveBetter/",
        "https://dlgrv.github.io/HowToLiveBetter/zh/",
    )


def _language_table_from_readme(repo_root: str) -> str | None:
    readme = os.path.join(repo_root, "README.md")
    if not os.path.isfile(readme):
        return None
    with open(readme, encoding="utf-8") as f:
        body = f.read()
    m = LANG_TABLE_RE.search(body)
    if not m:
        return None
    table = m.group(0)
    # Chinese column headers for README.zh.md; rows stay as in README.md.
    table = table.replace(
        "| Language | Site | README | PDF | EPUB |",
        "| 语言 | 网站 | README | PDF | EPUB |",
        1,
    )
    return table.rstrip() + "\n"


def insert_language_table(text: str, repo_root: str) -> str:
    if "[README.md](README.md)" in text:
        return text
    table = _language_table_from_readme(repo_root)
    if table is None:
        return text
    block = "\n" + table + "\n---\n\n"
    m = FIRST_H2_RE.search(text)
    if m is None:
        return text.rstrip() + "\n" + block
    return text[: m.start()] + block + text[m.start() :]


def apply_fork_overlay(text: str, repo_root: str | None = None) -> str:
    """Full post-sync transform for README.zh.md."""
    if repo_root is None:
        repo_root = os.getcwd()
    text = strip_ads(text)
    text = remap_docs_links(text)
    text = remap_og_image(text)
    text = remap_pages_urls(text)
    text = insert_language_table(text, repo_root)
    return text.rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: strip_zh_readme_ads.py README.zh.md", file=sys.stderr)
        return 2
    path = args[0]
    repo_root = os.path.dirname(os.path.abspath(path)) or os.getcwd()
    with open(path, encoding="utf-8") as f:
        original = f.read()
    cleaned = apply_fork_overlay(original, repo_root=repo_root)
    if cleaned != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print("applied fork overlay to", path)
    else:
        print("no fork overlay changes in", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
