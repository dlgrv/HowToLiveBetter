#!/usr/bin/env python3
"""Collect blind-judge answers on the golden set (plan Task 11 prep).

Inputs: translate/validate/results/golden_verdicts_batch{1..6}.json
        ({"batch": N, "answers": {"gNN": 1|2|"="}})
Output: translate/validate/results/golden_blind_summary.json with
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

from translate.lib.config import default_root

REPO = default_root()

RESULTS = os.path.join(REPO, "translate", "validate", "results")


def load_answers(results_dir=RESULTS):
    answers = {}
    for path in sorted(glob.glob(os.path.join(results_dir, "golden_verdicts_batch*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        answers.update(data.get("answers", {}))
    return answers


def _rate(pairs, answers):
    """Share of pairs where the judge picked variant_a (the original).

    `rate` here is picked_native / answered — meaningful ONLY for non-decoy
    pairs, where variant_a is a real distinct original. For decoys (A==B)
    there is no "original" to prefer: which side the judge happens to pick
    when they wrongly claim a difference is a coin flip by construction, not
    a false-positive signal. Use `fp_rate` (judge expressed ANY preference
    instead of a tie) for decoys instead — see `_fp_rate` below.

    If the judge never even ANSWERED the pairs (empty/lost data), rate is
    null — a missing metric must not read as a perfect one (review code#6).
    """
    picked_native = answered = ties = 0
    for p in pairs:
        a = answers.get(p["id"])
        if a is None:
            continue
        if a in ("=", 0):
            ties += 1
            continue
        answered += 1
        native_first = p["show_order"] == "AB"
        if (a == 1) == native_first:
            picked_native += 1
    if answered == 0:
        missing = all(answers.get(p["id"]) is None for p in pairs)
        return {
            "picked_original": picked_native,
            "answered": 0,
            "ties": ties,
            "rate": None if missing else 0.0,
        }
    return {
        "picked_original": picked_native,
        "answered": answered,
        "ties": ties,
        "rate": round(picked_native / answered, 3),
    }


def _fp_rate(decoys, answers):
    """True false-positive rate on decoys: judge claimed a difference (any
    non-tie answer) on a pair where variant_a == variant_b. There is no
    "which side" signal to measure on a decoy, only answered-vs-tied."""
    answered = ties = 0
    for p in decoys:
        a = answers.get(p["id"])
        if a is None:
            continue
        if a in ("=", 0):
            ties += 1
        else:
            answered += 1
    total = answered + ties
    if total == 0:
        missing = all(answers.get(p["id"]) is None for p in decoys)
        return {"false_positives": answered, "ties": ties, "rate": None if missing else 0.0}
    return {
        "false_positives": answered,
        "ties": ties,
        "rate": round(answered / total, 3),
    }


def summarize(results_dir=RESULTS):
    manifest = json.load(open(os.path.join(results_dir, "golden_manifest.json"), encoding="utf-8"))
    answers = load_answers(results_dir)
    non_decoy = [p for p in manifest["pairs"] if not p["decoy"]]
    decoys = [p for p in manifest["pairs"] if p["decoy"]]
    per_recipe = {}
    for recipe in {p["recipe"] for p in non_decoy}:
        per_recipe[recipe] = _rate([p for p in non_decoy if p["recipe"] == recipe], answers)
    pref = _rate(non_decoy, answers)
    fp = _fp_rate(decoys, answers)
    summary = {
        "native_preference": pref["rate"],
        "native_detail": pref,
        "decoy_fp_rate": fp["rate"],
        "decoy_detail": fp,
        "tie_contrast": {
            "decoy_ties": fp["ties"],
            "content_ties": pref["ties"],
        },
        "per_recipe": per_recipe,
        "unanswered": [p["id"] for p in manifest["pairs"] if p["id"] not in answers],
    }
    with open(os.path.join(results_dir, "golden_blind_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def main():
    s = summarize()
    print(
        json.dumps(
            {k: s[k] for k in ("native_preference", "decoy_fp_rate", "unanswered")},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
