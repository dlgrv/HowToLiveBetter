#!/usr/bin/env python3
"""Retro pass-E report (plan Task 9): aggregate judge verdicts -> findings.

Reads tools/judge/factcheck/<NN>-ru-<unit>.json, re-checks grounding
programmatically against the CN digest units, classifies gates, and writes
tools/validate/results/retro_e_findings.json.

Known-defect cross-check (2026-09-18 baseline):
  - ch 10/11 RU: numbers (verify.py domain, NOT expected from pass E)
  - ch 13/28/30 RU: calques "когорт" x9 / "популяц" x2 (style domain)
  - pass E is expected to find: logic/conditions/additions issues only.
"""
import glob
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

from tools.validate import factcheck as fc  # noqa: E402

JUDGE_DIR = os.path.join(REPO, "tools", "judge", "factcheck")
DIGEST = os.path.join(REPO, "tools", "digest")
OUT = os.path.join(REPO, "tools", "validate", "results", "retro_e_findings.json")
CHAPTERS = ["10", "11", "13", "28", "30"]
KNOWN = {
    "10": ["numbers: verify domain (not E)"],
    "11": ["numbers: verify domain (not E)"],
    "13": ["calque когорт: style domain (not E)"],
    "28": ["calque когорт: style domain (not E)"],
    "30": ["calque когорт: style domain (not E)"],
}


def cn_unit_text(nn, unit):
    path = os.path.join(DIGEST, nn, "units", f"{unit}.md")
    if not os.path.isfile(path):
        return None
    return open(path, encoding="utf-8").read()


def build_report():
    per_chapter = {}
    totals = {"verdicts": 0, "assertions": 0, "grounded_issues": 0,
              "ungrounded_dropped": 0, "gates": {"fail": 0, "warn": 0, "pass": 0}}
    for path in sorted(glob.glob(os.path.join(JUDGE_DIR, "*-ru-*.json"))):
        base = os.path.basename(path)[:-5]
        nn, unit = base.split("-ru-")
        rec = json.load(open(path, encoding="utf-8"))
        cn_text = cn_unit_text(nn, unit)
        totals["verdicts"] += 1
        ch = per_chapter.setdefault(nn, {"units": [], "gates": {"fail": 0, "warn": 0, "pass": 0}})
        entry = {"unit": unit, "verdict_file": os.path.relpath(path, REPO),
                 "grounding": None, "gate": None, "issues": [], "unverifiable": []}
        if cn_text is None:
            entry["grounding"] = {"error": f"cn unit {nn}/{unit} not found"}
            ch["units"].append(entry)
            continue
        g = fc.check_grounding(rec, cn_text)
        gate = fc.gate_major(rec)
        entry["grounding"] = {"grounded": g["grounded"], "dropped": len(g["dropped"])}
        entry["gate"] = gate["gate"]
        entry["issues"] = [
            {"claim": a.get("claim"), "cn_span": a.get("cn_span"),
             "issue_type": a.get("issue_type")}
            for a in g["kept"] if a.get("status") == "issue"]
        entry["unverifiable"] = rec.get("unverifiable", [])
        totals["assertions"] += len(rec.get("assertions", []))
        totals["grounded_issues"] += len(entry["issues"])
        totals["ungrounded_dropped"] += len(g["dropped"])
        totals["gates"][gate["gate"]] += 1
        ch["gates"][gate["gate"]] += 1
        ch["units"].append(entry)
    report = {
        "ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "chapters": CHAPTERS, "known_defects": KNOWN,
        "totals": totals,
        "per_chapter": {nn: per_chapter.get(nn, {"units": [], "gates": {"fail": 0, "warn": 0, "pass": 0}})
                        for nn in CHAPTERS},
        "note": ("expected: pass E finds logic/condition/additions issues; "
                 "numbers (10/11) and calques (13/28/30) belong to verify/style"),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main():
    r = build_report()
    t = r["totals"]
    print(json.dumps({
        "verdicts": t["verdicts"], "assertions": t["assertions"],
        "grounded_issues": t["grounded_issues"], "dropped_ungrounded": t["ungrounded_dropped"],
        "gates": t["gates"], "out": os.path.relpath(OUT, REPO)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
