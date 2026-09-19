#!/usr/bin/env python3
"""Collect blind-judge answers on the golden set (plan Task 11 prep).

Inputs: tools/validate/results/golden_verdicts_batch{1..6}.json
        ({"batch": N, "answers": {"gNN": 1|2|"="}})
Output: tools/validate/results/golden_blind_summary.json with
  - native_preference: share of non-decoy pairs where the judge picked the
    ORIGINAL text (variant_a) — A-B-against-degradation signal;
  - decoy_fp_rate: share of decoys (A==B) where the judge expressed a
    preference (false preference = judge noise floor);
  - per_recipe: native preference by degradation recipe.
"""
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

RESULTS = os.path.join(REPO, "tools", "validate", "results")
MANIFEST = os.path.join(RESULTS, "golden_manifest.json")
OUT = os.path.join(RESULTS, "golden_blind_summary.json")


def load_answers(results_dir=RESULTS):
    answers = {}
    for path in sorted(glob.glob(os.path.join(results_dir, "golden_verdicts_batch*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        answers.update(data.get("answers", {}))
    return answers


def _rate(pairs, answers):
    """Share of pairs where the judge picked variant_a (the original)."""
    picked_native = answered = 0
    for p in pairs:
        a = answers.get(p["id"])
        if a in (None, "=", 0):
            continue
        answered += 1
        native_first = p["show_order"] == "AB"
        if (a == 1) == native_first:
            picked_native += 1
    return {"picked_original": picked_native, "answered": answered,
            "rate": round(picked_native / answered, 3) if answered else None}


def summarize(results_dir=RESULTS):
    manifest = json.load(open(os.path.join(results_dir, "golden_manifest.json"),
                              encoding="utf-8"))
    answers = load_answers(results_dir)
    non_decoy = [p for p in manifest["pairs"] if not p["decoy"]]
    decoys = [p for p in manifest["pairs"] if p["decoy"]]
    per_recipe = {}
    for recipe in {p["recipe"] for p in non_decoy}:
        per_recipe[recipe] = _rate([p for p in non_decoy if p["recipe"] == recipe], answers)
    pref = _rate(non_decoy, answers)
    fp = _rate(decoys, answers)  # on decoys both variants identical -> any pick is FP
    summary = {
        "native_preference": pref["rate"],
        "native_detail": pref,
        "decoy_fp_rate": fp["rate"],
        "decoy_detail": fp,
        "per_recipe": per_recipe,
        "unanswered": [p["id"] for p in manifest["pairs"] if p["id"] not in answers],
    }
    with open(os.path.join(results_dir, "golden_blind_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def main():
    s = summarize()
    print(json.dumps({k: s[k] for k in ("native_preference", "decoy_fp_rate",
                                        "unanswered")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
