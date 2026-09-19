#!/usr/bin/env python3
"""Judge agreement metrics (plan Task 7): Cohen's kappa, screening gates.

Inputs are the markup results:
  - results/golden_labels.json    — Лёня's markup of 60 pairs (1/2/=)
  - results/golden_verdicts.json  — judge model's answers for the same session

Verdict encoding everywhere: 1 = first shown variant preferred (VARIANT 1),
2 = second, 0 = tie. Mapping to native/degraded is done here (never leaked
into markup files).
"""
import argparse
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(REPO, "tools", "validate", "results")
MANIFEST = os.path.join(RESULTS, "golden_manifest.json")
LABELS = os.path.join(RESULTS, "golden_labels.json")
VERDICTS = os.path.join(RESULTS, "golden_verdicts.json")


def cohens_kappa(a, b):
    """Cohen's kappa for two equal-length lists of labels.

    Returns None when kappa is undefined (unanimous marginals, pe == 1):
    with every rater in one category the statistic is 0/0, and the
    prevalence paradox makes a bare 1.0 meaningless. Callers must treat
    None as "not computable", never as a pass.
    """
    if len(a) != len(b):
        raise ValueError("rater lists must have equal length")
    n = len(a)
    if n == 0:
        raise ValueError("empty lists")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    levels = set(a) | set(b)
    pe = sum((sum(1 for x in a if x == l) / n) * (sum(1 for y in b if y == l) / n)
             for l in levels)
    if pe == 1.0:
        return None  # undefined: unanimous marginals (prevalence paradox)
    return (po - pe) / (1 - pe)


def screening_metrics(gold, pred, positive=0):
    """Confusion matrix with calque (positive=0... here positive=1 default).

    Encoding: gold/pred use 1 = native, 0 = calque/degraded.
    positive class = 1 (native).
    """
    if len(gold) != len(pred):
        raise ValueError("lists must have equal length")
    tp = sum(1 for g, p in zip(gold, pred) if g == 1 and p == 1)
    fp = sum(1 for g, p in zip(gold, pred) if g == 0 and p == 1)
    fn = sum(1 for g, p in zip(gold, pred) if g == 1 and p == 0)
    tn = sum(1 for g, p in zip(gold, pred) if g == 0 and p == 0)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    fnr = fn / (fn + tp) if fn + tp else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and precision + recall else None)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "fpr": fpr, "fnr": fnr, "f1": f1}


def gate_fnr(metrics, threshold=0.2):
    """Pass C/D utility gate: judge must MISS at most `threshold` of natives."""
    return metrics["fnr"] is not None and metrics["fnr"] <= threshold


def load_pair_verdicts(path):
    """Load judge answers for native-first and degraded-first sessions."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("native", []), data.get("degraded", [])


def nativeness_rate(verdicts):
    """Per-group share of 'native is more natural' answers (decoys excluded)."""
    out = {}
    for group, marks in verdicts.items():
        marks = [m for m in marks if m is not None]
        out[group] = (sum(1 for m in marks if m == 1) / len(marks)) if marks else None
    if out.get("native") is not None and out.get("degraded") is not None:
        out["gap"] = out["native"] - out["degraded"]
    return out


def main():
    ap = argparse.ArgumentParser(description="judge agreement metrics")
    ap.add_argument("--labels", default=LABELS)
    ap.add_argument("--verdicts", default=VERDICTS)
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--fnr-gate", type=float, default=0.2)
    args = ap.parse_args()
    if not (os.path.isfile(args.labels) and os.path.isfile(args.verdicts)):
        print(json.dumps({"status": "pending",
                          "reason": "golden_labels.json / golden_verdicts.json not yet present"}))
        return 0
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    labels = json.load(open(args.labels, encoding="utf-8"))
    verdicts = json.load(open(args.verdicts, encoding="utf-8"))

    # A/B-against-degradation: score judge answers against known ground truth
    def decode(session, marks):
        """marks (1|2|0 tie) -> 1 if 'native variant chosen' else 0 (ties excluded)."""
        if len(marks) != len(session["pairs"]):
            raise ValueError(
                f"marks {len(marks)} != pairs {len(session['pairs'])} — answer file misaligned")
        out = []
        for p, m in zip(session["pairs"], marks):
            if m in (None, 0, "="):
                continue
            native_shown_first = (p["show_order"] == "AB")  # A is native
            chosen_first = (m == 1)
            chose_native = chosen_first if native_shown_first else not chosen_first
            out.append(1 if chose_native else 0)
        return out

    native_scored = decode({"pairs": manifest["pairs"]}, verdicts.get("native", []))
    degraded_scored = decode({"pairs": manifest["pairs"]}, verdicts.get("degraded", []))
    nr = nativeness_rate({"native": native_scored, "degraded": degraded_scored})

    # kappa: judge vs Лёня on the same pair preferences (first run only).
    # Dimension: 3-category marks (1/2/=), ties included — documented policy.
    k = None
    kappa_note = None
    if labels.get("marks") and verdicts.get("first"):
        judge_first = verdicts["first"]
        lenya = labels["marks"]
        k = cohens_kappa(judge_first, lenya)
        if k is None:
            kappa_note = ("kappa undefined (unanimous marginals): use po and "
                          "Gwet's AC1 as the prevalence-robust check")
    po_agreement = None
    if labels.get("marks") and verdicts.get("first"):
        pairs_ = zip(verdicts["first"], labels["marks"])
        po_agreement = round(sum(1 for x, y in pairs_ if x == y) / len(labels["marks"]), 3)

    report = {"status": "ok",
              "nativeness": nr,
              "kappa_vs_lenya": (round(k, 3) if k is not None else None),
              "kappa_note": kappa_note,
              "po_agreement": po_agreement,
              "gap_gate": {"gap_required": 0.25,
                           "passed": bool(nr.get("gap") is not None and nr["gap"] >= 0.25)},
              "fnr_gate": {"threshold": args.fnr_gate}}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
