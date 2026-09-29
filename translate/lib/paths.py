"""Canonical chapter file resolution under book/ and book/<lang>/.

Unit directories are not resolved here — see translate/lib/config.unit_dir.
"""

from __future__ import annotations

import glob
import os
import re


def _nn(chapter) -> str:
    """Normalize chapter id to two-digit form ('2' / 2 / '02' → '02')."""
    return f"{int(chapter):02d}"


def cn_chapter_path(root: str, chapter) -> str:
    """Absolute path of book/NN-*.md (Chinese source). Requires exactly one match."""
    nn = _nn(chapter)
    book = os.path.join(root, "book")
    hits = [
        name
        for name in os.listdir(book)
        if re.match(rf"{re.escape(nn)}-", name) and name.endswith(".md")
    ]
    if len(hits) != 1:
        raise FileNotFoundError(
            f"chapter {nn} not found: expected 1 book/{nn}-*.md under {root}, got {len(hits)}"
        )
    return os.path.join(book, hits[0])


def tr_chapter_path(root: str, chapter, lang: str) -> str:
    """Absolute path of book/<lang>/NN-*.md. Requires exactly one match."""
    nn = _nn(chapter)
    pattern = os.path.join(root, "book", lang, f"{nn}-*.md")
    hits = sorted(glob.glob(pattern))
    if len(hits) != 1:
        raise FileNotFoundError(
            f"chapter {nn} not found: expected 1 book/{lang}/{nn}-*.md under {root}, got {len(hits)}"
        )
    return hits[0]


def load_chapter_text(root: str, chapter, lang: str | None = None) -> str:
    """Read CN (lang is None) or translated chapter text."""
    path = cn_chapter_path(root, chapter) if lang is None else tr_chapter_path(root, chapter, lang)
    with open(path, encoding="utf-8") as f:
        return f.read()
