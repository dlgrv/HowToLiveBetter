#!/usr/bin/env python3
"""Mutation-test harness for pass E (plan Task 4).

Design: 30 semantic mutations injected into CLEAN book chapters (each mutant
must pass tools/verify.py — i.e. only pass E can catch it) + 30 untouched
controls. The mutation list is generated once by subagents (seed=42, ref
sha256 pinned in SEED_REF) and committed as results/mutations_seed42.json;
harness runs are deterministic from that file.

Catch-rate protocol (pass E accept): E must flag >= 80% of mutants,
FP <= 10% on controls, novelty vs verify.py >= 70%.
"""

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile

from tools.pipeline.config import default_root
from tools.pipeline.paths import load_chapter_text

REPO = default_root()
RESULTS = os.path.join(REPO, "tools", "validate", "results")
SPEC_PATH = os.path.join(RESULTS, "mutations_seed42.json")

CHAPTERS = [
    "02",
    "04",
    "05",
    "06",
    "07",
    "09",
    "12",
    "14",
    "16",
    "17",
    "20",
    "22",
    "23",
    "25",
    "27",
    "32",
]

TAXONOMY = (
    "dropped_condition",
    "reversed_logic",
    "softened_claim",
    "added_advice",
    "subject_swapped",
    "cross_unit_contradiction",
)

SEED_REF_SPEC = {
    "seed": 42,
    "generation": "subagents, one batch per chapter, deterministic from this ref",
    "counts": {"mutations": 30, "controls": 30},
    "chapters": CHAPTERS,
    "taxonomy": list(TAXONOMY),
}


def run_verify(nn, lang, file_text=None):
    """Run tools/verify.py; returns (exit_code, {status, output}).

    With file_text, the text is written to a temp file and passed via --file
    (source chapter is still resolved from book/<NN>-*.md).
    """
    tmp = None
    if file_text is not None:
        fd, tmp = tempfile.mkstemp(suffix=".md", prefix="mut_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(file_text)
    try:
        cmd = [sys.executable, os.path.join(REPO, "tools", "verify.py"), str(nn), "--lang", lang]
        if tmp:
            cmd += ["--file", tmp]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, check=False)
        status = "pass" if proc.returncode == 0 else "fail"
        return proc.returncode, {"status": status, "output": proc.stdout[-2000:]}
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def init_spec():
    """Create the spec skeleton (SEED_REF filled after generation)."""
    os.makedirs(RESULTS, exist_ok=True)
    if os.path.isfile(SPEC_PATH):
        print(f"spec already exists: {SPEC_PATH}")
        return
    ref = hashlib.sha256(json.dumps(SEED_REF_SPEC, sort_keys=True).encode()).hexdigest()
    spec = {
        "seed_ref": ref,
        "chapters": CHAPTERS,
        "taxonomy": list(TAXONOMY),
        "mutations": [],
        "controls": [],
    }
    with open(SPEC_PATH, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"spec skeleton written: {SPEC_PATH}\nseed_ref: {ref}")


def validate_spec():
    """Validate the generated spec; raises SystemExit on any violation."""
    with open(SPEC_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    problems = []
    muts, ctrls = spec.get("mutations", []), spec.get("controls", [])
    if len(muts) != 30:
        problems.append(f"mutations: {len(muts)} != 30")
    if len(ctrls) != 30:
        problems.append(f"controls: {len(ctrls)} != 30")
    seen_excerpt = set()
    targets = set()
    for m in muts:
        key = (m["target"][0], m["target"][1], m["original_excerpt"])
        if key in seen_excerpt:
            problems.append(f"duplicate target/excerpt: {key}")
        seen_excerpt.add(key)
        targets.add((m["target"][0], m["target"][1]))
        if m["issue_type"] not in TAXONOMY:
            problems.append(f"bad issue_type: {m['issue_type']}")
        if m["mutant_text"] == m["original_excerpt"]:
            problems.append(f"mutation equals original: {key}")
        book = load_chapter_text(REPO, m["target"][0], m["target"][1])
        if m["original_excerpt"] not in book:
            problems.append(f"excerpt not in book: {key}")
    for c in ctrls:
        book = load_chapter_text(REPO, c["target"][0], c["target"][1])
        if c["original_excerpt"] not in book:
            problems.append(f"control excerpt not in book: {c['target']}")
    if problems:
        print("SPEC INVALID:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print(f"spec valid: 30 mutations / 30 controls over {len(targets)} chapter-languages")


def build_cases():
    """Materialise 60 verify-safe cases (mutants must PASS verify)."""
    validate_spec()
    with open(SPEC_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    cases, skipped = [], []
    for m in spec["mutations"]:
        nn, lang = m["target"]
        book = load_chapter_text(REPO, nn, lang)
        if book.count(m["original_excerpt"]) != 1:
            skipped.append(f"excerpt not unique in book: {lang}{nn}")
            continue
        mutant_full = book.replace(m["original_excerpt"], m["mutant_text"], 1)
        _code, out = run_verify(nn, lang, file_text=mutant_full)
        if out["status"] != "pass":
            skipped.append(f"verify catches it: {lang}{nn} {m['issue_type']}")
            continue
        cases.append(
            {
                "kind": "mutation",
                "issue_type": m["issue_type"],
                "target": [nn, lang],
                "text": mutant_full,
                "original_excerpt": m["original_excerpt"],
            }
        )
    for c in spec["controls"]:
        nn, lang = c["target"]
        cases.append(
            {"kind": "control", "target": [nn, lang], "text": load_chapter_text(REPO, nn, lang)}
        )
    with open(os.path.join(RESULTS, "mutations_cases.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "n_mutants": sum(1 for c in cases if c["kind"] == "mutation"),
                "n_controls": sum(1 for c in cases if c["kind"] == "control"),
                "skipped": skipped,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(
        f"cases: {sum(1 for c in cases if c['kind'] == 'mutation')} mutants / "
        f"{sum(1 for c in cases if c['kind'] == 'control')} controls, "
        f"{len(skipped)} skipped"
    )
    return cases


def merge_batches():
    """Merge subagent _batchN.json files into mutations_seed42.json.

    Keeps the pinned seed_ref and chapter pool from the skeleton; dedupes
    by (target, original_excerpt)."""
    with open(SPEC_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    seen = set()
    n_m = n_c = 0
    for path in sorted(glob.glob(os.path.join(RESULTS, "_batch*.json"))):
        batch = json.load(open(path, encoding="utf-8"))
        for m in batch.get("mutations", []):
            key = (tuple(m["target"]), m["original_excerpt"])
            if key in seen:
                continue
            seen.add(key)
            spec["mutations"].append(
                {
                    "target": list(m["target"]),
                    "issue_type": m["issue_type"],
                    "original_excerpt": m["original_excerpt"],
                    "mutant_text": m["mutant_text"],
                }
            )
            n_m += 1
        for c in batch.get("controls", []):
            key = (tuple(c["target"]), c["original_excerpt"])
            if key in seen:
                continue
            seen.add(key)
            spec["controls"].append(
                {"target": list(c["target"]), "original_excerpt": c["original_excerpt"]}
            )
            n_c += 1
    with open(SPEC_PATH, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    return {
        "mutations_added": n_m,
        "controls_added": n_c,
        "total": {"mutations": len(spec["mutations"]), "controls": len(spec["controls"])},
    }


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-spec", help="write spec skeleton with pinned seed_ref")
    sub.add_parser("merge-batches", help="merge subagent _batchN.json into spec")
    sub.add_parser("validate-spec", help="validate generated spec structure")
    sub.add_parser("build-cases", help="materialise verify-safe case list (JSON)")
    args = ap.parse_args()
    if args.cmd == "init-spec":
        init_spec()
    elif args.cmd == "merge-batches":
        print(json.dumps(merge_batches(), ensure_ascii=False))
    elif args.cmd == "validate-spec":
        validate_spec()
    elif args.cmd == "build-cases":
        cases = build_cases()
        print(
            json.dumps(
                {
                    "n": len(cases),
                    "mutations": sum(1 for c in cases if c["kind"] == "mutation"),
                    "controls": sum(1 for c in cases if c["kind"] == "control"),
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
