#!/usr/bin/env python3
"""Style check, pass A (WARN-only, plan Task 6): bureaucratese / calque markers.

Engine is language-agnostic: patterns and whitelist zones come from
tools/rules/<lang>.json. Lines starting with a whitelisted prefix (evidence,
notes, sources) are never flagged — medical passive there is legitimate.

CLI: python3 tools/style_check.py <file.md> --lang ru
Exit code is ALWAYS 0 (advisory pass); findings go to stdout as WARN lines.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.pipeline import config as pconfig  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAX_PER_CATEGORY = 5


def load_markers(lang, root=REPO):
    """Style markers for a language from its language pack."""
    try:
        rules = pconfig.load_lang_rules(lang, root=root)
    except FileNotFoundError:
        raise ValueError(
            f"unknown language {lang!r}; no language pack tools/rules/{lang}.json") from None
    markers = rules.get("style_markers", [])
    for m in markers:
        m["_re"] = re.compile(m["pattern"], re.IGNORECASE | re.UNICODE)
    return markers


def load_zones(lang, root=REPO):
    try:
        rules = pconfig.load_lang_rules(lang, root=root)
    except FileNotFoundError:
        raise ValueError(f"unknown language {lang!r}") from None
    return tuple(rules.get("whitelist_zones", []))


def check_text(text, lang, root=REPO):
    """Return [{label, line_no, span, zone}] for style-marker hits.

    Whitelisted lines (evidence/notes/sources prefixes) are skipped entirely;
    per-category cap = MAX_PER_CATEGORY (mirrors verify.py calque mechanism).
    """
    markers = load_markers(lang, root=root)
    zones = load_zones(lang, root=root)
    findings = []
    per_label = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        if any(line.startswith(z) or line.lstrip().startswith(z) for z in zones):
            continue
        for m in markers:
            for match in m["_re"].finditer(line):
                label = m["label"]
                if per_label.get(label, 0) >= MAX_PER_CATEGORY:
                    break
                per_label[label] = per_label.get(label, 0) + 1
                findings.append({
                    "label": label, "line_no": line_no,
                    "span": match.group(0), "note": m.get("note", ""),
                })
    return findings


def main():
    ap = argparse.ArgumentParser(description="WARN-only style check (pass A)")
    ap.add_argument("file")
    ap.add_argument("--lang", required=True, help="language pack key (ru|en)")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = ap.parse_args()
    text = open(args.file, encoding="utf-8").read()
    findings = check_text(text, args.lang)
    if args.json:
        print(json.dumps({"file": args.file, "lang": args.lang,
                          "warnings": findings}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"WARN: line {f['line_no']}: [{f['label']}] {f['span']}")
        print(f"style_check: {len(findings)} warnings (advisory, exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
