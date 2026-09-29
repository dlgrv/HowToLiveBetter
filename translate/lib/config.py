"""Project config: translate/rules/project.json + per-language packs rules/<lang>.json."""

import json
import os


def load_config(root):
    """Load translate/rules/project.json (unit paths, judge/QE backends)."""
    path = os.path.join(root, "translate", "rules", "project.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_langs(root=None):
    """Site locale entries from translate/langs.json."""
    if root is None:
        root = default_root()
    path = os.path.join(root, "translate", "langs.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return list((data or {}).get("languages") or [])


def site_langs(root=None):
    """All published locale codes, including zh (CN site pages)."""
    return [e["code"] for e in load_langs(root) if e.get("code")]


def translation_langs(root=None):
    """Overlay translation codes (book/<code>/), not the zh mirror at book/."""
    out = []
    for entry in load_langs(root):
        code = entry.get("code")
        content_root = entry.get("contentRoot", "")
        if code and content_root.startswith("book/") and content_root != "book":
            out.append(code)
    return out


def load_lang_rules(lang, root=None):
    """Load the language pack rules/<lang>.json (labels, calques, style markers)."""
    if root is None:
        root = default_root()
    path = os.path.join(root, "translate", "rules", f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unit_dir(root, lang, chapter):
    """Resolve the unit directory for a language and chapter number.

    Relative templates (in-repo, e.g. cn digest) are rooted at `root`;
    absolute templates (wave dirs) pass through unchanged.
    """
    cfg = load_config(root)
    known = [*translation_langs(root), "cn"]
    if lang not in known:
        raise ValueError(f"unknown language {lang!r}; available: {known}")
    tmpl = cfg.get("unit_dirs", {}).get(lang)
    if not tmpl:
        raise ValueError(f"unit_dirs has no template for language {lang!r}")
    d = tmpl.format(nn=f"{int(chapter):02d}")
    if not os.path.isabs(d):
        d = os.path.join(root, d)
    return d


def default_root():
    """Repo root inferred from this file's location (<root>/translate/lib/)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
