"""Shared helpers for tools/validate/ scripts: paths, text, hashes, verdict IO.

Thin re-exports of the reusable core (tools/pipeline/) plus the two
unit/book loaders used by every validation script.
"""
import glob
import os

from tools.pipeline import config as _config
from tools.pipeline import store as _store

load_config = _config.load_config
load_lang_rules = _config.load_lang_rules
unit_dir = _config.unit_dir
default_root = _config.default_root

norm_text = _store.norm_text
unit_sha256 = _store.unit_sha256
hash_prompt = _store.hash_prompt
build_payload = _store.build_payload
write_verdict = _store.write_verdict
read_verdict = _store.read_verdict


def load_unit(root, chapter, lang, unit):
    """Read one translation unit (<NN>/<lang>/<unit>.md), placeholders intact."""
    path = os.path.join(unit_dir(root, lang, chapter), f"{unit}.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_book(root, chapter, lang):
    """Read the assembled chapter book/<lang>/NN-*.md (committed canonical text)."""
    hits = sorted(glob.glob(os.path.join(root, "book", lang, f"{int(chapter):02d}-*.md")))
    if not hits:
        raise FileNotFoundError(f"no book/{lang}/{int(chapter):02d}-*.md under {root}")
    with open(hits[0], encoding="utf-8") as f:
        return f.read()
