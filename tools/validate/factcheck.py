#!/usr/bin/env python3
"""Factcheck orchestrator, pass E (plan Task 8): judge verdicts + grounding gate.

For each unit: build the factcheck prompt (CN source + translation), get a
verdict JSON from the judge backend (live waves in Task 9; mock/inline for
tests), then DISCARD any assertion whose cn_span is not literally present in
the CN unit body (service lines 来源/§SRC§/成本标签 excluded from search —
a span there proves nothing). Verdicts are persisted with audit fields.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)

RESULTS = os.path.join(REPO, "tools", "validate", "results")
PROMPT_PATH = os.path.join(REPO, "tools", "prompts", "judge-factcheck.md")

SERVICE_MARKERS = ("来源", "§SRC§", "成本标签", "证据等级")
SERVICE_LINE_RE = re.compile(r"^\s*-\s*(来源|证据等级)|§SRC§|<!--")


def cn_body(cn_text):
    """CN unit minus service lines (sources/evidence/tag-comments/§SRC§)."""
    keep = []
    for line in cn_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if any(m in s for m in SERVICE_MARKERS) or SERVICE_LINE_RE.match(s):
            continue
        keep.append(s)
    return "\n".join(keep)


def check_grounding(verdict, cn_text):
    """Drop assertions whose cn_span is absent from the CN body.

    Returns {grounded: bool, kept: [...], dropped: [{assertion, reason}]}.
    """
    body = cn_body(cn_text)
    kept, dropped = [], []
    for a in verdict.get("assertions", []):
        span = (a.get("cn_span") or "").strip()
        if not span:
            dropped.append({"assertion": a, "reason": "empty_span"})
        elif any(m in span for m in SERVICE_MARKERS):
            dropped.append({"assertion": a, "reason": "service_line"})
        elif span not in body:
            dropped.append({"assertion": a, "reason": "span_not_found"})
        else:
            kept.append(a)
    return {"grounded": not dropped, "kept": kept, "dropped": dropped}


def grounded_rate(verdicts, cn_text):
    """Share of verdicts that survive grounding unmodified."""
    if not verdicts:
        return 0.0
    ok = sum(1 for v in verdicts if check_grounding(v, cn_text)["grounded"])
    return ok / len(verdicts)


def write_result(outdir, nn, lang, verdict, cn_text, tr_text, backend, model_id):
    """Persist one unit verdict with reproducibility audit fields."""
    os.makedirs(outdir, exist_ok=True)
    unit_payload = (cn_text + "\x00" + tr_text).encode("utf-8")
    rec = {
        "chapter": nn, "lang": lang,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": backend, "model_id": model_id,
        "unit_sha256": hashlib.sha256(unit_payload).hexdigest(),
        "prompt_hash": hashlib.sha256(
            open(PROMPT_PATH, "rb").read()).hexdigest()[:16],
        "verdict": verdict,
        "grounding": check_grounding(verdict, cn_text),
    }
    path = os.path.join(outdir, f"{nn}-{lang}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return path


def load_prompt():
    return open(PROMPT_PATH, encoding="utf-8").read()


def main():
    ap = argparse.ArgumentParser(description="factcheck single unit (pass E)")
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--lang", required=True, choices=("ru", "en"))
    ap.add_argument("--cn-unit", required=True, help="path to CN unit md")
    ap.add_argument("--tr-unit", required=True, help="path to translated unit md")
    ap.add_argument("--stdin-verdict", help="inline verdict JSON (mock/tests)")
    ap.add_argument("--outdir", default=os.path.join(RESULTS, "factcheck"))
    args = ap.parse_args()
    cn_text = open(args.cn_unit, encoding="utf-8").read()
    tr_text = open(args.tr_unit, encoding="utf-8").read()
    if not args.stdin_verdict:
        print(json.dumps({"status": "judge_unavailable",
                          "reason": "live waves run via Task 9 wave runner"}))
        return 0
    verdict = json.loads(args.stdin_verdict)
    path = write_result(args.outdir, args.chapter, args.lang, verdict,
                        cn_text, tr_text, backend="inline", model_id="mock-1")
    print(json.dumps({"written": path,
                      "grounded": check_grounding(verdict, cn_text)["grounded"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
