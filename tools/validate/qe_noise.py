#!/usr/bin/env python3
"""QE noise measurement (plan Task 3): anchors x 5 runs -> sigma -> tau.

Anchors (seed-fixed): ru 01, 13, 24 + en 13 — five independent scoring runs
per anchor; sigma = mean of per-anchor std-devs; tau = max(3*sigma, 0.01).
Writes tools/validate/results/qe_noise.json. Without the QE venv this
prints an explicit SKIPPED report (exit 0) so pipelines degrade cleanly.
"""
import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pipeline import qe as pqe      # noqa: E402
from tools.validate import common as vc   # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ANCHORS = [("ru", 1), ("ru", 13), ("ru", 24), ("en", 13)]
RUNS = 5


def anchor_segments(root, lang, nn, max_units=3):
    """First N (cn, translation) segment pairs of an anchor chapter."""
    import glob
    cn_dir = vc.unit_dir(root, "cn", nn)
    cn_files = sorted(glob.glob(os.path.join(cn_dir, "[0-9][0-9].md")))[:max_units]
    segs = []
    for cf in cn_files:
        unit = os.path.splitext(os.path.basename(cf))[0]
        cn_text = vc.norm_text(open(cf, encoding="utf-8").read())
        try:
            mt_text = vc.norm_text(vc.load_unit(root, nn, lang, unit))
        except FileNotFoundError:
            continue
        segs.append({"src": cn_text, "mt": mt_text})
    return segs


def build_report(root=REPO, force_skip=False):
    if force_skip or not pqe.available(root):
        return {"status": "skipped",
                "reason": "QE venv not available on this machine (needs Mac ~/.venvs/qe)",
                "anchors": [f"{lang}{nn:02d}" for lang, nn in ANCHORS]}
    per_anchor_sigma = []
    anchor_details = {}
    for lang, nn in ANCHORS:
        segs = anchor_segments(root, lang, nn)
        if not segs:
            anchor_details[f"{lang}{nn:02d}"] = {"error": "no segments"}
            continue
        means = []
        for _ in range(RUNS):
            scores = pqe.run_scores(segs, root=root)
            means.append(statistics.fmean(scores))
        anchor_details[f"{lang}{nn:02d}"] = {"runs": RUNS, "segment_means": means}
        if len(means) >= 2:
            per_anchor_sigma.append(statistics.stdev(means))
    if not per_anchor_sigma:
        return {"status": "error", "reason": "no anchor produced scores"}
    sigma = statistics.fmean(per_anchor_sigma)
    return {"status": "ok", "runs": RUNS, "sigma": sigma,
            "tau": pqe.compute_tau(sigma), "anchors": anchor_details}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-skip", action="store_true", help="emit SKIPPED report without probing")
    ap.add_argument("--out", default=os.path.join(REPO, "tools", "validate", "results", "qe_noise.json"))
    args = ap.parse_args()
    report = build_report(force_skip=args.force_skip)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: report[k] for k in report if k != "anchors"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
