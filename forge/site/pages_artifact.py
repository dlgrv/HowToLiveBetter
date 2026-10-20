#!/usr/bin/env python3
"""Stage a flat GitHub Pages artifact in .publish/.

The published tree mirrors the public URL space:

  .publish/
    index.html, {en,ru,es,zh}/, assets/, robots.txt, llms.txt, …   ← from site/
    book/, docs/research/                                ← from repo
    README*.md                                           ← from repo

Locale pages use __HTLB_BASE__='../', so README and book must sit next to
en/ in this flat root (not under site/ in git).
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
from datetime import UTC, datetime

from translate.lib.config import default_root
from translate.lib.config import load_langs as load_langs_registry

from forge.site.build_llms_full import write_llms_full
from forge.site.build_sitemap import write_sitemap

ROOT = default_root()
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, ".publish")


def main() -> int:
    if not os.path.isdir(SITE):
        sys.exit("missing site/ — run forge/site/build_pages.py first")
    if not os.path.isfile(os.path.join(SITE, "index.html")):
        sys.exit("missing site/index.html")

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT)

    book_src = os.path.join(ROOT, "book")
    if not os.path.isdir(book_src):
        sys.exit("missing book/")
    shutil.copytree(book_src, os.path.join(OUT, "book"))

    research_src = os.path.join(ROOT, "docs", "research")
    if os.path.isdir(research_src):
        shutil.copytree(research_src, os.path.join(OUT, "docs", "research"))

    readmes = sorted(glob.glob(os.path.join(ROOT, "README*.md")))
    if not readmes:
        sys.exit("no README*.md at repo root")
    for path in readmes:
        shutil.copy2(path, os.path.join(OUT, os.path.basename(path)))

    # Generated after staging: these must reflect the assembled publish tree,
    # not the source tree (they overwrite the placeholders copied from site/).
    langs = load_langs_registry(ROOT)
    lang_codes = [lang["code"] for lang in langs]
    write_sitemap(OUT, ROOT, lang_codes)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d")
    write_llms_full(OUT, langs, generated_at)

    # IndexNow key: must be served from the docroot root (deploy-book.sh pings
    # keyLocation=https://book.dlgrv.com/<key>.txt).
    for key_file in sorted(glob.glob(os.path.join(ROOT, "deploy", "indexnow", "*.txt"))):
        shutil.copy2(key_file, os.path.join(OUT, os.path.basename(key_file)))

    print("staged", os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
