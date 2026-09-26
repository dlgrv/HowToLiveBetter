#!/usr/bin/env python3
"""Bureaucratese detector — flags канцелярит in translations.

North Star: перевод должен быть безумно понятным для носителя.
Uses a seeded list of bureaucratic patterns (RU / EN / ES) plus
generalisations: passive-voice chains, nominalisations, long genitive
chains, and verbosity heuristics.
"""

import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── bureaucratese profiles ──────────────────────────────────────────

PROFILES = {
    "ru": {
        "patterns": [
            # Nominalisations
            (r"(?:производить|произвести|осуществлять|осуществить|произвести)\s+[а-яё]+(?:ие|ие|ку)", "действие → глагол"),
            (r"(?:подвергать|подвергаться|подвергнуть|подвергнуться)\s+[а-яё]+(?:ию|ию)", "подвергать → глагол"),
            (r"являться\s+\S+ным", "являться → опустить"),
            (r"носить\s+\S+ный\s+характер", "носить … характер → опустить"),
            (r"иметь место\s", "иметь место → происходить"),
            (r"принимать участие\b", "принимать участие → участвовать"),
            (r"оказывать помощь\b", "оказывать помощь → помогать"),
            (r"оказывать влияние\b", "оказывать влияние → влиять"),
            (r"проводить анализ\b", "проводить анализ → анализировать"),
            # Genitive chains (4+ nested genitives)
            (r"\b\w+ого\s+\w+ой\s+\w+ого\s", "цепочка родительных падежей"),
            (r"\b\w+ия\s+\w+ого\s+\w+ия\s", "цепочка родительных падежей"),
            # Passive / impersonal
            (r"(?:является|было|будет)\s+сделан[аоы]", "пассив: было сделано → сделали"),
            (r"(?:является|считается)\s+\S+ным", "пассив: является … → глагол"),
            (r"в целях\s", "в целях → чтобы"),
            (r"в рамках\s", "в рамках → в/при"),
            (r"в соответствии с\b", "в соответствии с → по / согласно"),
            (r"на основании\b", "на основании → из-за / на основе"),
            (r"в связи с тем, что\b", "в связи с тем, что → потому что"),
            (r"в случае, если\b", "в случае, если → если"),
            (r"в том числе\b", "в том числе → включая / например"),
            (r"\bв данном\b", "в данном → в этом"),
            (r"\bданн(?:ый|ая|ое|ом)\b", "данный → этот (искл. данные как data)"),
            (r"вышеуказанн|нижеуказанн|вышеописанн", "вышеуказанный → этот"),
            (r"посредством\b", "посредством → через / с помощью"),
            (r"необходимо отметить\b", "необходимо отметить → важно / опустить"),
            # Formal sentence starts
            (r"вместе с тем\b", "вместе с тем → однако / но"),
        ],
    },
    "en": {
        "patterns": [
            (r"it should be noted that\b", "it should be noted that → note that / omit"),
            (r"it is important to note that\b", "→ note that"),
            (r"in order to\b", "in order to → to"),
            (r"in the event that\b", "in the event that → if"),
            (r"in accordance with\b", "in accordance with → under / per"),
            (r"for the purpose of\b", "for the purpose of → for / to"),
            (r"with regard to\b", "with regard to → about / on"),
            (r"in respect of\b", "in respect of → about"),
            (r"in relation to\b", "in relation to → about / on"),
            (r"by means of\b", "by means of → by / using"),
            (r"on the basis of\b", "on the basis of → based on / because"),
            (r"with the exception of\b", "with the exception of → except"),
            (r"as a consequence of\b", "as a consequence of → because of"),
            (r"prior to\b", "prior to → before"),
            (r"subsequent to\b", "subsequent to → after"),
            (r"in the course of\b", "in the course of → during"),
            (r"a number of\b", "a number of → several / some"),
        ],
    },
    "es": {
        "patterns": [
            (r"cabe señalar que\b", "cabe señalar que → omitir"),
            (r"es importante señalar que\b", "→ señalar que"),
            (r"con el fin de\b", "con el fin de → para"),
            (r"a fin de\b", "a fin de → para"),
            (r"de conformidad con\b", "de conformidad con → según"),
            (r"en relación con\b", "en relación con → sobre"),
            (r"por medio de\b", "por medio de → con / mediante"),
            (r"con respecto a\b", "con respecto a → sobre"),
            (r"por parte de\b", "por parte de → de"),
            (r"en caso de que\b", "en caso de que → si"),
            (r"antes de que\b", "antes de que → si no es necesario, reducir"),
        ],
    },
}


def check_text(text, lang):
    """Return list of (pattern_desc, match_text) for each violation."""
    profile = PROFILES.get(lang)
    if not profile:
        return []
    issues = []
    for pattern, desc in profile["patterns"]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            # Filter false positives: numbers
            match_text = m.group(0)
            if re.search(r'\d', match_text):
                continue
            issues.append((desc, match_text.strip()))
    return issues


def check_file(path, lang):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return check_text(text, lang)


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
    ap.add_argument("lang", nargs="?", default="ru",
                    help="Target language (ru/en/es)")
    ap.add_argument("--dir", default=None,
                    help="Directory to scan (default: book/LANG/)")
    ap.add_argument("--json", action="store_true",
                    help="Output JSON")
    args = ap.parse_args()

    scan_dir = args.dir or os.path.join(ROOT, "book", args.lang)
    if not os.path.isdir(scan_dir):
        print(f"Directory not found: {scan_dir}", file=sys.stderr)
        sys.exit(1)

    results = check_dir(scan_dir, args.lang)

    if args.json:
        out = {}
        for path, issues in results.items():
            out[os.path.relpath(path, ROOT)] = [
                {"desc": d, "match": m} for d, m in issues
            ]
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

    sys.exit(1)


if __name__ == "__main__":
    main()