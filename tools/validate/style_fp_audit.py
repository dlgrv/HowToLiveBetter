#!/usr/bin/env python3
"""Style FP-audit (plan Task 6): sample >=100 fragments for human labeling.

Produces a labeling session file (results/style_fp_session.json) with
stratified fragments: every style_check WARN + equal number of clean
fragments (seed-fixed sampling). After Task 11 labeling
(results/style_fp_labels.json), `report` computes precision/recall:
  precision = true WARN / all engine WARN
  recall    = caught known-bad / 20 known-bad (calque history fragments)
  rule with FP > 40% -> DROPPED (not tuned), per plan.
"""
import argparse
import glob
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.style_check import check_text  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(REPO, "tools", "validate", "results")
SESSION = os.path.join(RESULTS, "style_fp_session.json")
LABELS = os.path.join(RESULTS, "style_fp_labels.json")
SEED = 42
KNOWN_BAD_PATTERNS = ["когорт", "популяц"]  # calque history (verify.py findings)


def collect_fragments(lang="ru"):
    """(file, line_no, line) for all non-empty body lines of book/<lang>/."""
    frags = []
    for path in sorted(glob.glob(os.path.join(REPO, "book", lang, "*.md"))):
        rel = os.path.basename(path)
        for i, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            if len(line.strip()) >= 30:  # meaningful fragments only
                frags.append({"file": rel, "line_no": i, "text": line})
    return frags


def build_session(lang="ru", clean_per_warn=1):
    frags = collect_fragments(lang)
    warned, clean = [], []
    warned_ids = set()
    for f in frags:
        if check_text(f["text"], lang):
            warned.append(f)
            warned_ids.add((f["file"], f["line_no"]))
    rng = random.Random(SEED)
    clean_pool = [f for f in frags if (f["file"], f["line_no"]) not in warned_ids]
    clean = rng.sample(clean_pool, min(len(warned) * clean_per_warn + 100, len(clean_pool)))
    known_bad = [f for f in frags
                 if any(re.search(p, f["text"], re.IGNORECASE) for p in KNOWN_BAD_PATTERNS)]
    session = {"lang": lang, "seed": SEED, "warned": warned, "clean_sample": clean,
               "known_bad": known_bad[:40]}
    os.makedirs(RESULTS, exist_ok=True)
    with open(SESSION, "w", encoding="utf-8") as fh:
        json.dump(session, fh, ensure_ascii=False, indent=2)
    return {"warned": len(warned), "clean": len(clean), "known_bad": len(known_bad[:40]),
            "total": len(warned) + len(clean)}


def report():
    """Precision/recall from labels file (written after Task 11 markup)."""
    if not os.path.isfile(LABELS):
        return {"status": "pending", "reason": "labels not yet marked (Task 11)"}
    session = json.load(open(SESSION, encoding="utf-8"))
    labels = json.load(open(LABELS, encoding="utf-8"))
    # labels: {"warned": {idx: true|false}, "clean": {idx: false-positives...}, "known_bad": {idx: caught?}}
    per_rule_tp, per_rule_fp = {}, {}
    for idx, f in enumerate(session["warned"]):
        hits = check_text(f["text"], session["lang"])
        is_bad = labels.get("warned", {}).get(str(idx), False)
        for h in hits:
            if is_bad:
                per_rule_tp[h["label"]] = per_rule_tp.get(h["label"], 0) + 1
            else:
                per_rule_fp[h["label"]] = per_rule_fp.get(h["label"], 0) + 1
    rules = {}
    for label in set(per_rule_tp) | set(per_rule_fp):
        tp, fp = per_rule_tp.get(label, 0), per_rule_fp.get(label, 0)
        precision = tp / (tp + fp) if tp + fp else None
        rules[label] = {"tp": tp, "fp": fp, "precision": round(precision, 3) if precision is not None else None,
                        "dropped": bool(precision is not None and precision < 0.6)}  # FP>40%
    kb = session["known_bad"]
    caught = sum(1 for idx, f in enumerate(kb)
                 if check_text(f["text"], session["lang"]) or labels.get("known_bad", {}).get(str(idx), False))
    clean_n = len(session["clean_sample"])
    clean_flagged = sum(1 for f in session["clean_sample"] if check_text(f["text"], session["lang"]))
    return {"status": "ok", "rules": rules,
            "precision_overall": round(
                sum(r["tp"] for r in rules.values()) /
                max(1, sum(r["tp"] + r["fp"] for r in rules.values())), 3),
            "recall_known_bad": round(caught / max(1, len(kb)), 3),
            "clean_fp_rate": round(clean_flagged / max(1, clean_n), 3),
            "n_fragments": len(session["warned"]) + clean_n}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-session")
    sub.add_parser("report")
    args = ap.parse_args()
    if args.cmd == "build-session":
        print(json.dumps(build_session(), ensure_ascii=False))
    else:
        print(json.dumps(report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
