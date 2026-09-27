#!/usr/bin/env python3
"""Book-wide канцелярит gate — same markers as style_check, two CLIs.

Per-file review: tools/style_check.py (WARN, exit 0).
This script walks book/{lang}/ and can --strict fail for make quality.
Glossary calques stay on the style/verify path, not here.
"""

import json
import os
import sys

from tools.pipeline.config import default_root
from tools.style_check import check_text

ROOT = default_root()


def check_file(path, lang):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        findings = check_text(text, lang, include_glossary=False, max_per_category=None)
    except ValueError:
        return []
    return [(f.get("note") or f["label"], f["span"]) for f in findings]


def check_dir(root_dir, lang):
    """Walk root_dir/**/*.md and return {path: [(desc, match)]}."""
    results = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            issues = check_file(path, lang)
            if issues:
                results[path] = issues
    return results


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Bureaucratese checker")
    ap.add_argument("lang", nargs="?", default="ru", help="Target language (ru/en/es)")
    ap.add_argument("--dir", default=None, help="Directory to scan (default: book/LANG/)")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when findings exist (for gating)")
    args = ap.parse_args()

    scan_dir = args.dir or os.path.join(ROOT, "book", args.lang)
    if not os.path.isdir(scan_dir):
        print(f"Directory not found: {scan_dir}", file=sys.stderr)
        sys.exit(1)

    results = check_dir(scan_dir, args.lang)

    if args.json:
        out = {}
        for path, issues in results.items():
            out[os.path.relpath(path, ROOT)] = [{"desc": d, "match": m} for d, m in issues]
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        return

    total = sum(len(v) for v in results.values())
    if total == 0:
        print("OK — no bureaucratese detected")
        return

    print(f"Found {total} instance(s) of канцелярит:\n")
    for path, issues in sorted(results.items()):
        rel = os.path.relpath(path, ROOT)
        print(f"  {rel}:")
        for desc, match in issues:
            print(f"    • {desc}: «{match}»")
        print()

    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
