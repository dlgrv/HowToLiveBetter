#!/usr/bin/env python3
"""Stage a flat GitHub Pages artifact in .publish/.

The published tree mirrors the public URL space:

  .publish/
    index.html, {en,ru,es,zh}/, assets/, robots.txt, …   ← from site/
    book/                                                ← from repo
    README*.md                                           ← from repo

Locale pages use __HTLB_BASE__='../', so README and book must sit next to
en/ in this flat root (not under site/ in git).
"""

from __future__ import annotations

import glob
import os
import shutil
import sys

from tools.pipeline.config import default_root

ROOT = default_root()
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, ".publish")


def main() -> int:
    if not os.path.isdir(SITE):
        sys.exit("missing site/ — run tools/build_pages.py first")
    if not os.path.isfile(os.path.join(SITE, "index.html")):
        sys.exit("missing site/index.html")

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT)

    book_src = os.path.join(ROOT, "book")
    if not os.path.isdir(book_src):
        sys.exit("missing book/")
    shutil.copytree(book_src, os.path.join(OUT, "book"))

    readmes = sorted(glob.glob(os.path.join(ROOT, "README*.md")))
    if not readmes:
        sys.exit("no README*.md at repo root")
    for path in readmes:
        shutil.copy2(path, os.path.join(OUT, os.path.basename(path)))

    print("staged", os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
