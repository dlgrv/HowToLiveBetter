"""Project config: tools/rules/project.yaml + per-language packs rules/<lang>.json."""
import json
import os

import yaml


def load_config(root):
    """Load tools/rules/project.yaml (languages, unit paths, judge/QE backends)."""
    path = os.path.join(root, "tools", "rules", "project.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_lang_rules(lang, root=None):
    """Load the language pack rules/<lang>.json (labels, calques, style markers)."""
    if root is None:
        root = default_root()
    path = os.path.join(root, "tools", "rules", f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unit_dir(root, lang, chapter):
    """Resolve the unit directory for a language and chapter number.

    Relative templates (in-repo, e.g. cn digest) are rooted at `root`;
    absolute templates (wave dirs) pass through unchanged.
    """
    cfg = load_config(root)
    known = list(cfg.get("languages", [])) + ["cn"]
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
    """Repo root inferred from this file's location (<root>/tools/pipeline/)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
