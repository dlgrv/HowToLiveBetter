#!/usr/bin/env python3
"""Validate subagent-produced degradation JSONs against the hard rules.

Checks per pair (recipe-aware):
  - digits multiset of variant_b == digits multiset of variant_a
  - protected lines byte-identical (### heading, <!-- tag, evidence level,
    sources lines)
  - language matches the pair's lang (cyrillic ratio vs latin)
  - length ratio within recipe band (abridgement 0.55–0.90, bloat 1.15–1.70)
  - variant_b != variant_a; no recipe/meta words leaked into text
Usage:
  python3 tools/validate/check_degrade.py --file results/_lite2_degrade_bloat.json \
      --recipe bloat
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROTECTED = re.compile(r"^(### |<!--|- Уровень доказательности|- Источники|"
                       r"- Evidence level|- Sources)")
DIGITS = re.compile(r"\d+")
RATIO_BANDS = {"abridgement": (0.55, 0.90), "bloat": (1.15, 1.70)}
LEAK = re.compile(r"variant_a|variant_b|decoy|recipe|placeholder|TODO|lorem",
                  re.I)


def digits_multiset(t):
    out = []
    for m in DIGITS.finditer(t):
        out.extend(m.group(0))
    return sorted(out)


def lang_ok(text, lang):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    cyr = sum(1 for c in letters if "\u0400" <= c <= "\u04FF")
    lat = sum(1 for c in letters if c.isascii())
    if lang == "ru":
        return cyr > lat
    return lat > cyr


def check(pair, orig, recipe):
    problems = []
    b = pair.get("variant_b") or ""
    if not b.strip():
        return ["variant_b empty"]
    if b == orig:
        return ["variant_b identical to variant_a"]
    if LEAK.search(b):
        problems.append("meta/leak words present")
    if digits_multiset(orig) != digits_multiset(b):
        problems.append("digits multiset differs")
    o_lines, b_lines = set(orig.split("\n")), set(b.split("\n"))
    for ln in o_lines:
        if PROTECTED.match(ln.strip()) and ln not in b_lines:
            problems.append(f"protected line altered: {ln.strip()[:40]!r}")
            break
    if not lang_ok(b, pair["lang"]):
        problems.append(f"language mismatch (expected {pair['lang']})")
    lo, hi = RATIO_BANDS[recipe]
    ratio = len(b) / max(1, len(orig))
    if not (lo <= ratio <= hi):
        problems.append(f"length ratio {ratio:.2f} outside [{lo}, {hi}]")
    # field labels preserved (same bullet labels as original)
    o_labels = {ln.split(":")[0] for ln in orig.split("\n")
                if ln.strip().startswith("- ") and ":" in ln}
    b_labels = {ln.split(":")[0] for ln in b.split("\n")
                if ln.strip().startswith("- ") and ":" in ln}
    if o_labels and not o_labels.issubset(b_labels):
        problems.append(f"missing field labels: {sorted(o_labels - b_labels)[:3]}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--recipe", required=True, choices=sorted(RATIO_BANDS))
    args = ap.parse_args()
    data = json.load(open(args.file, encoding="utf-8"))
    manifest = json.load(open(os.path.join(
        REPO, "tools/validate/results/golden_manifest.json"), encoding="utf-8"))
    by_id = {p["id"]: p for p in manifest["pairs"]}
    fail = 0
    for pair in data["pairs"]:
        pid = pair["pair_id"]
        orig = by_id[pid]["variant_a"]
        problems = check(pair, orig, args.recipe)
        status = "OK" if not problems else "FAIL: " + "; ".join(problems)
        if problems:
            fail += 1
        print(f"{pid}: {status}")
    print(f"\n{len(data['pairs']) - fail}/{len(data['pairs'])} passed "
          f"({args.recipe})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
