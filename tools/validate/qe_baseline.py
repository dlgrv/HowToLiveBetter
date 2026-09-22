#!/usr/bin/env python3
"""QE per-unit baselines (plan Task 3): score every unit, cache under tools/.qe/.

Per-unit (not per-chapter) scores for the whole book; cached as
tools/.qe/<NN>-<lang>.json (transient, gitignored). Without the QE venv:
explicit SKIPPED, exit 0.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pipeline import qe as pqe    # noqa: E402
from tools.validate import common as vc # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def baseline_for_chapter(root, lang, nn):
    cn_dir = vc.unit_dir(root, "cn", nn)
    units = sorted(os.path.basename(p) for p in glob.glob(os.path.join(cn_dir, "[0-9][0-9].md")))
    segs, ids = [], []
    for uf in units:
        unit = os.path.splitext(uf)[0]
        cn_text = vc.norm_text(open(os.path.join(cn_dir, uf), encoding="utf-8").read())
        try:
            mt_text = vc.norm_text(vc.load_unit(root, nn, lang, unit))
        except FileNotFoundError:
            continue
        segs.append({"src": cn_text, "mt": mt_text})
        ids.append(unit)
    if not segs:
        return None
    scores = pqe.run_scores(segs, root=root)
    return dict(zip(ids, scores))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["ru", "en"])
    ap.add_argument("--chapters", default="all", help="comma list like 01,13 or 'all'")
    args = ap.parse_args()
    root = REPO
    if not pqe.available(root):
        print(json.dumps({"status": "skipped",
                          "reason": "QE venv not available (needs Mac ~/.venvs/qe)"}))
        return 0
    chapters = sorted(os.path.basename(d) for d in glob.glob(os.path.join(root, "tools", "digest", "*")))
    if args.chapters != "all":
        chapters = [f"{int(c):02d}" for c in args.chapters.split(",")]
    out = {"status": "ok", "lang": args.lang, "chapters": {}}
    for nn in chapters:
        try:
            per_unit = baseline_for_chapter(root, args.lang, int(nn))
        except pqe.QeUnavailable as e:
            print(json.dumps({"status": "skipped", "reason": str(e)}))
            return 0
        if per_unit is None:
            continue
        cache = os.path.join(root, "tools", ".qe", f"{nn}-{args.lang}.json")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(per_unit, f, ensure_ascii=False, indent=2)
        out["chapters"][nn] = len(per_unit)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
