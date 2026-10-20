#!/usr/bin/env python3
"""Generate llms-full.txt — the whole book in one file (llmstxt.org convention).

Sections follow the primary-first language order from translate/langs.json:
each chapter is emitted as

    # <absolute URL>
    <original markdown>

so an LLM crawler can ingest the entire book with one request and still cite
stable per-chapter URLs. The Chinese source lives at /book/NN-*.md, translated
locales at /book/<lang>/NN-*.md (mirrors the publish tree layout).
"""

from __future__ import annotations

import os
import sys

HOST = "https://book.dlgrv.com"


def _chapter_files(publish_dir: str, content_root: str) -> list[str]:
    """Sorted markdown chapter names directly inside a content root."""
    full = os.path.join(publish_dir, content_root)
    if not os.path.isdir(full):
        return []
    names = [n for n in os.listdir(full) if n.endswith(".md")]
    return sorted(names)


def collect_sections(publish_dir: str, langs: list[dict]) -> list[dict]:
    """Return [{url, body}] in primary-first, chapter-stable order."""
    sections: list[dict] = []
    # front matter first: per-language README in the same language order
    for lang in langs:
        readme = os.path.join(publish_dir, lang["readme"])
        if os.path.isfile(readme):
            sections.append({"url": f"{HOST}/{lang['readme']}", "body": _read(readme)})
    # chapters per locale, primary-first (zh's contentRoot is the bare book/)
    for lang in langs:
        root_rel = lang["contentRoot"]  # e.g. "book/en", zh → "book"
        for name in _chapter_files(publish_dir, root_rel):
            path = os.path.join(publish_dir, root_rel, name)
            sections.append({"url": f"{HOST}/{root_rel}/{name}", "body": _read(path)})
    return sections


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read().rstrip()


def render_llms_full(sections: list[dict], generated_at: str) -> str:
    header = (
        f"# How to Live Better — full book (single file)\n\n"
        f"> Canonical site: {HOST}/ — file map: {HOST}/llms.txt\n"
        f"> Each section header below is the chapter's stable URL.\n"
        f"> License: Unlicense (public domain dedication).\n"
        f"> Generated: {generated_at}\n\n"
    )
    parts = [header]
    parts.extend(f"# {s['url']}\n\n{s['body']}\n\n---\n\n" for s in sections)
    return "".join(parts)


def write_llms_full(publish_dir: str, langs: list[dict], generated_at: str) -> int:
    sections = collect_sections(publish_dir, langs)
    if not sections:
        sys.exit("llms-full: no sections collected — refusing to write an empty file")
    out_path = os.path.join(publish_dir, "llms-full.txt")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_llms_full(sections, generated_at))
    print(f"llms-full: {len(sections)} sections → {out_path}")
    return len(sections)
