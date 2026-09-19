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
JUDGE_DIR = os.path.join(REPO, "tools", "judge", "factcheck")  # transient (gitignored)

# plan Task 8: major classes fail the chapter gate (after verify.py, before style/QE)
MAJOR_ISSUE_TYPES = ("reversed_logic", "invented", "dropped_condition")

SERVICE_MARKERS = ("来源", "§SRC§", "成本标签", "证据等级")
SERVICE_LINE_RE = re.compile(r"^\s*-\s*(来源|证据等级)|§SRC§|<!--")
WS_RE = re.compile(r"\s+")


def _norm(s):
    return WS_RE.sub("", s)


def cn_body(cn_text):
    """CN unit minus service lines (positional rule: a LINE that starts a
    service block — sources/evidence/tag-comments/§SRC§ — is removed; body
    text merely CONTAINING e.g. 出资来源 stays)."""
    keep = []
    for line in cn_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if SERVICE_LINE_RE.match(s) or any(s.startswith(m) for m in SERVICE_MARKERS):
            continue
        keep.append(s)
    return "\n".join(keep)


def check_grounding(verdict, cn_text):
    """Drop assertions whose cn_span is absent from the CN body.

    Service-line rule is positional: a span sitting ON a service line
    (来源/§SRC§/成本标签/证据等级) proves nothing and is dropped; a body span
    that merely CONTAINS a marker substring (出资来源 = source of funds) is fine.
    Returns {grounded: bool, kept: [...], dropped: [{assertion, reason}]}.
    """
    kept, dropped = [], []
    for a in verdict.get("assertions", []):
        span = (a.get("cn_span") or "").strip()
        if not span:
            dropped.append({"assertion": a, "reason": "empty_span"})
            continue
        # locate span in the ORIGINAL text to learn its line context
        pos = cn_text.find(span)
        if pos < 0:
            # tolerate whitespace drift: collapse all whitespace on both sides
            pos = _norm(cn_text).find(_norm(span))
            if pos < 0:
                dropped.append({"assertion": a, "reason": "span_not_found"})
                continue
            # map collapsed position back to original line for context
            line_start = _line_of_collapsed(cn_text, pos)
        else:
            line_start = cn_text.rfind("\n", 0, pos) + 1
        line = cn_text[line_start:cn_text.find("\n", line_start)
                       if cn_text.find("\n", line_start) >= 0 else len(cn_text)]
        if SERVICE_LINE_RE.match(line.strip()) or any(
                line.strip().startswith(m) for m in SERVICE_MARKERS):
            dropped.append({"assertion": a, "reason": "service_line"})
            continue
        # final gate: span must survive inside the filtered body
        if span not in cn_body(cn_text) and _norm(span) not in _norm(cn_body(cn_text)):
            dropped.append({"assertion": a, "reason": "span_not_found"})
            continue
        kept.append(a)
    return {"grounded": not dropped, "kept": kept, "dropped": dropped}


def _line_of_collapsed(cn_text, collapsed_pos):
    """Map a position in whitespace-collapsed text back to an original line start."""
    seen = 0
    line_start = 0
    for i, ch in enumerate(cn_text):
        if seen >= collapsed_pos:
            return line_start
        if not ch.isspace():
            seen += 1
        if ch == "\n":
            line_start = i + 1
    return line_start


def grounded_rate(verdicts, cn_text):
    """Share of verdicts that survive grounding unmodified."""
    if not verdicts:
        return 0.0
    ok = sum(1 for v in verdicts if check_grounding(v, cn_text)["grounded"])
    return ok / len(verdicts)


def gate_major(verdict):
    """Chapter-gate: any major finding -> FAIL ('fail'), else 'pass'/'warn'.

    Numeric drift is excluded here on purpose (verify.py owns numbers) —
    duplication would only add noise.
    """
    findings = verdict.get("assertions", []) if isinstance(verdict, dict) else []
    major = [a for a in findings
             if a.get("status") == "issue" and a.get("issue_type") in MAJOR_ISSUE_TYPES]
    minor = [a for a in findings
             if a.get("status") == "issue" and a.get("issue_type") not in MAJOR_ISSUE_TYPES]
    if major:
        return {"gate": "fail", "major": major, "minor": minor}
    if minor:
        return {"gate": "warn", "major": [], "minor": minor}
    return {"gate": "pass", "major": [], "minor": []}


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
