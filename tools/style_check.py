#!/usr/bin/env python3
"""Style check: bureaucratese / calque markers (pass A).

Engine is language-agnostic: patterns and whitelist zones come from
tools/rules/<lang>.json. Lines starting with a whitelisted prefix (evidence,
notes, sources) are never flagged — medical passive there is legitimate.

Glossary (tools/glossary.json) adds banned_calques stems/phrases and name_forms
anti-patterns (e.g. «в Бангладеш» instead of «в Бангладеше»).

CLI:
  python3 tools/style_check.py <file.md> --lang ru [--plain-only]   # WARN, exit 0
  python3 tools/style_check.py --book --lang ru [--strict] [--json] # book-wide gate
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from tools.pipeline import config as pconfig
from tools.pipeline.config import default_root
from tools.pipeline.labels import PLAIN_FIELD_INDEX, field_labels

REPO = default_root()
MAX_PER_CATEGORY = 5


def _compile_markers(raw_markers):
    out = []
    for m in raw_markers:
        compiled = dict(m)
        compiled["_re"] = re.compile(m["pattern"], re.IGNORECASE | re.UNICODE)
        out.append(compiled)
    return out


def load_glossary_marker_dicts(lang, root=REPO):
    """Uncompiled marker dicts from glossary (for merging / dedup)."""
    path = os.path.join(root, "tools", "glossary.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    markers = []
    for ban in data.get("banned_calques", {}).get(lang, []):
        if not ban:
            continue
        pat = re.escape(ban)
        if " " not in ban and not ban.startswith("в "):
            pat = rf"\b{pat}"
        markers.append(
            {
                "pattern": pat,
                "label": f"calque:{ban[:24]}",
                "note": "glossary banned_calques",
            }
        )
    for nf in data.get("name_forms", []):
        if nf.get("lang") != lang:
            continue
        if nf.get("gov") == "в+prep":
            lemma = nf["lemma"]
            markers.append(
                {
                    "pattern": rf"\bв\s+{re.escape(lemma)}\b",
                    "label": f"name_form:{lemma}",
                    "note": f"use {nf.get('form', lemma)}, not в {lemma}",
                }
            )
    return markers


def load_markers(lang, root=REPO, include_glossary=True):
    """Style markers for a language from its language pack + glossary."""
    try:
        rules = pconfig.load_lang_rules(lang, root=root)
    except FileNotFoundError:
        raise ValueError(
            f"unknown language {lang!r}; no language pack tools/rules/{lang}.json"
        ) from None
    raw = list(rules.get("style_markers", []))
    seen = {m["pattern"] for m in raw}
    if include_glossary:
        for gm in load_glossary_marker_dicts(lang, root=root):
            if gm["pattern"] not in seen:
                seen.add(gm["pattern"])
                raw.append(gm)
    return _compile_markers(raw)


def _is_plain_terms_line(line, lang):
    try:
        label = field_labels(lang)[PLAIN_FIELD_INDEX]
    except (KeyError, FileNotFoundError):
        return False
    stripped = line.lstrip()
    return stripped.startswith(f"- {label}:")


def check_text(
    text,
    lang,
    root=REPO,
    plain_only=False,
    include_glossary=True,
    max_per_category=MAX_PER_CATEGORY,
):
    """Return [{label, line_no, span, zone}] for style-marker hits.

    Whitelisted lines (evidence/notes/sources prefixes) are skipped entirely
    unless plain_only is set (then only plain-terms lines are scanned).
    Per-category cap defaults to MAX_PER_CATEGORY; pass None for no cap
    (book-wide quality gate).
    """
    markers = load_markers(lang, root=root, include_glossary=include_glossary)
    try:
        rules = pconfig.load_lang_rules(lang, root=root)
    except FileNotFoundError:
        raise ValueError(f"unknown language {lang!r}") from None
    zones = tuple(rules.get("whitelist_zones", []))
    findings = []
    per_label = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        if plain_only:
            if not _is_plain_terms_line(line, lang):
                continue
        elif any(line.startswith(z) or line.lstrip().startswith(z) for z in zones):
            continue
        for m in markers:
            for match in m["_re"].finditer(line):
                label = m["label"]
                if max_per_category is not None and per_label.get(label, 0) >= max_per_category:
                    break
                per_label[label] = per_label.get(label, 0) + 1
                findings.append(
                    {
                        "label": label,
                        "line_no": line_no,
                        "span": match.group(0),
                        "note": m.get("note", ""),
                    }
                )
    return findings


def check_file(path, lang, *, include_glossary=True, max_per_category=None):
    """Findings for one file as [(desc, span), ...] for book-wide reporting."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        findings = check_text(
            text,
            lang,
            include_glossary=include_glossary,
            max_per_category=max_per_category,
        )
    except ValueError:
        return []
    return [(f.get("note") or f["label"], f["span"]) for f in findings]


def check_dir(root_dir, lang, *, include_glossary=False, max_per_category=None):
    """Walk root_dir/**/*.md → {path: [(desc, match)]}."""
    results = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            issues = check_file(
                path,
                lang,
                include_glossary=include_glossary,
                max_per_category=max_per_category,
            )
            if issues:
                results[path] = issues
    return results


def _emit_book_results(results, *, root=REPO, as_json=False) -> int:
    """Print book-wide results. Return total finding count."""
    if as_json:
        out = {}
        for path, issues in results.items():
            out[os.path.relpath(path, root)] = [{"desc": d, "match": m} for d, m in issues]
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return sum(len(v) for v in results.values())

    total = sum(len(v) for v in results.values())
    if total == 0:
        print("OK — no style markers detected")
        return 0

    print(f"Found {total} style-marker instance(s):\n")
    for path, issues in sorted(results.items()):
        rel = os.path.relpath(path, root)
        print(f"  {rel}:")
        for desc, match in issues:
            print(f"    • {desc}: «{match}»")
        print()
    return total


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Style check (per-file WARN or book-wide gate)")
    ap.add_argument("file", nargs="?", help="chapter markdown (omit with --book)")
    ap.add_argument("--lang", required=True, help="language pack key (ru|en|es)")
    ap.add_argument("--plain-only", action="store_true", help="scan only plain-terms field lines")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument(
        "--book",
        action="store_true",
        help="scan book/<lang>/ (rules markers only, no glossary; no per-label cap)",
    )
    ap.add_argument(
        "--dir", default=None, help="with --book: directory to scan (default book/LANG)"
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="with --book: exit 1 when any findings (make quality)",
    )
    args = ap.parse_args(argv)

    if args.book:
        if args.file:
            print("ERROR: do not pass a file with --book", file=sys.stderr)
            return 2
        scan_dir = args.dir or os.path.join(REPO, "book", args.lang)
        if not os.path.isdir(scan_dir):
            print(f"Directory not found: {scan_dir}", file=sys.stderr)
            return 1
        results = check_dir(scan_dir, args.lang, include_glossary=False, max_per_category=None)
        total = _emit_book_results(results, as_json=args.json)
        if args.strict and total:
            return 1
        return 0

    if not args.file:
        print("ERROR: file required unless --book", file=sys.stderr)
        return 2

    try:
        text = open(args.file, encoding="utf-8").read()
    except OSError as e:
        print(f"ERROR: style_check cannot read {args.file}: {e}", file=sys.stderr)
        return 2
    try:
        findings = check_text(text, args.lang, plain_only=args.plain_only)
    except ValueError as e:
        msg = f"style_check skip: {e}"
        if args.json:
            print(
                json.dumps(
                    {
                        "file": args.file,
                        "lang": args.lang,
                        "plain_only": args.plain_only,
                        "status": "skip",
                        "reason": str(e),
                        "warnings": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"WARN: {msg}")
            print("style_check: 0 warnings (skip, exit 0)")
        return 0
    if args.json:
        print(
            json.dumps(
                {
                    "file": args.file,
                    "lang": args.lang,
                    "plain_only": args.plain_only,
                    "warnings": findings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for f in findings:
            print(f"WARN: line {f['line_no']}: [{f['label']}] {f['span']}")
        print(f"style_check: {len(findings)} warnings (advisory, exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
