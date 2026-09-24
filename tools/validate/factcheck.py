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
MAJOR_ISSUE_TYPES = ("reversed_logic", "invented", "dropped_condition",
                     "hardened_claim")

SERVICE_MARKERS = ("来源", "§SRC§", "成本标签", "证据等级")
SERVICE_LINE_RE = re.compile(r"^\s*-\s*(来源|证据等级)|§SRC§|<!--")
WS_RE = re.compile(r"\s+")


def _norm(s):
    return WS_RE.sub("", s)


ELLIPSIS_RE = re.compile(r"\u2026+|\.{3,}")


def parse_verdict(reply):
    """Parse a judge reply; unparseable output becomes an explicit error.

    A truncated or prose-wrapped reply used to become {"raw_reply": ...} and
    silently gated as pass (no assertions). Now it is flagged parse_error so
    every gate consumer can fail loudly.
    """
    try:
        v = json.loads(reply)
    except (json.JSONDecodeError, TypeError):
        return {"parse_error": True, "raw_reply": str(reply)[:2000]}
    if not isinstance(v, dict):
        return {"parse_error": True, "raw_reply": str(reply)[:2000]}
    return v


def normalize_assertions(verdict):
    """Accept both verdict schemas; return (assertions, usable).

    Deployed schema keys assertions on `status: "ok"|"issue"`; the committed
    prompt schema keys on `ru_ok`/`en_ok` booleans. The gate consumes `status`,
    so prompt-schema verdicts are mapped here instead of silently gating as
    pass (every gate previously computed major=[] for them — fail-open).

    usable=False means the reply carried no parseable assertion list
    (parse error / truncation) — gates must report "error", not "pass".
    """
    if not isinstance(verdict, dict) or verdict.get("parse_error"):
        return [], False
    raw = verdict.get("assertions")
    if not isinstance(raw, list):
        return [], False
    out = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        a = dict(a)
        if "status" not in a:
            failed = (a.get("ru_ok") is False) or (a.get("en_ok") is False)
            a["status"] = "issue" if failed else "ok"
        out.append(a)
    return out, True


def cn_body(cn_text):
    keep = []
    for line in cn_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if SERVICE_LINE_RE.match(s) or any(s.startswith(m) for m in SERVICE_MARKERS):
            continue
        keep.append(s)
    return "\n".join(keep)


def tr_body(tr_text):
    keep = []
    for line in tr_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s in ("§TAG§", "§SRC§") or s.startswith("§TAG§") or s.startswith("§SRC§"):
            continue
        if s.startswith("<!--"):
            continue
        keep.append(s)
    return "\n".join(keep)


def build_judge_prompt(cn_text, tr_text, lang):
    template = load_prompt()
    return (
        f"{template.strip()}\n\n"
        f"## CHINESE SOURCE\n\n{cn_body(cn_text)}\n\n"
        f"## TRANSLATION ({lang})\n\n{tr_body(tr_text)}\n"
    )


def open_live_judge(root=None):
    root = root or REPO
    from tools.pipeline import judges

    api_key = judges.resolve_api_key()
    try:
        name = judges.backend_name(root)
        model_id = judges.configured_model_id(root)
    except Exception:
        name = "subagent-glm"
        model_id = "glm-5.3-flash"
    if name != "local-ollama" and not api_key:
        return None
    try:
        backend_cls = judges.get_backend(name)
    except Exception:
        return None
    client = backend_cls(model_id=model_id, api_key=api_key)
    return client, name, model_id


def _locate(span, cn_text):
    pos = cn_text.find(span)
    if pos >= 0:
        end = pos + len(span)
        starts = [cn_text.rfind("\n", 0, pos) + 1]
        nxt = cn_text.find("\n", pos)
        while 0 <= nxt < end:
            starts.append(nxt + 1)
            nxt = cn_text.find("\n", nxt + 1)
        return starts, [span]
    ntext = _norm(cn_text)
    pos = ntext.find(_norm(span))
    if pos >= 0:
        return [_line_of_collapsed(cn_text, pos)], [span]
    parts = [p for p in ELLIPSIS_RE.split(span) if _norm(p)]
    if len(parts) > 1:
        starts, searched = [], 0
        for part in parts:
            idx = ntext.find(_norm(part), searched)
            if idx < 0:
                return None
            starts.append(_line_of_collapsed(cn_text, idx))
            searched = idx + len(_norm(part))
        return starts, parts
    return None


def check_grounding(verdict, cn_text):
    """Drop assertions whose cn_span is absent from the CN body.

    Service-line rule is positional: a span sitting ON a service line
    (来源/§SRC§/成本标签/证据等级) proves nothing and is dropped; a body span
    that merely CONTAINS a marker substring (出资来源 = source of funds) is fine.
    A span is checked against EVERY line it grounds on (a multi-line span
    touching a service line is dropped). Additionally, an assertion with
    span_supports_claim=false is dropped: the span exists but does not
    support the claim (fabricated-claim defense).
    Returns {grounded: bool, kept: [...], dropped: [{assertion, reason}]}.
    """
    assertions, usable = normalize_assertions(verdict)
    kept, dropped = [], []
    if not usable:
        return {"grounded": False, "kept": [], "dropped": [], "error": "unparseable verdict"}
    for a in assertions:
        span = (a.get("cn_span") or "").strip()
        if not span:
            dropped.append({"assertion": a, "reason": "empty_span"})
            continue
        if a.get("span_supports_claim") is False:
            dropped.append({"assertion": a, "reason": "span_does_not_support_claim"})
            continue
        located = _locate(span, cn_text)
        if located is None:
            dropped.append({"assertion": a, "reason": "span_not_found"})
            continue
        line_starts, fragments = located
        service = False
        for ls in line_starts:
            line = cn_text[ls:cn_text.find("\n", ls)
                           if cn_text.find("\n", ls) >= 0 else len(cn_text)]
            if SERVICE_LINE_RE.match(line.strip()) or any(
                    line.strip().startswith(m) for m in SERVICE_MARKERS):
                service = True
        if service:
            dropped.append({"assertion": a, "reason": "service_line"})
            continue
        # final gate: every grounded fragment must survive inside the
        # filtered body (ellipsis spans are checked fragment-wise)
        nbody = _norm(cn_body(cn_text))
        if not all(f in cn_body(cn_text) or _norm(f) in nbody for f in fragments):
            dropped.append({"assertion": a, "reason": "span_not_found"})
            continue
        kept.append(a)
    return {"grounded": not dropped, "kept": kept, "dropped": dropped}


def _line_of_collapsed(cn_text, collapsed_pos):
    """Map a position in whitespace-collapsed text back to an original line start."""
    seen = 0
    for i, ch in enumerate(cn_text):
        if not ch.isspace():
            if seen == collapsed_pos:
                # the collapsed offset lands exactly on this char: the span
                # STARTS here, so it lives on the line containing i
                return cn_text.rfind("\n", 0, i) + 1
            seen += 1
    return 0


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
    assertions, usable = normalize_assertions(verdict)
    if not usable:
        # broken judge output must not read as "clean chapter"
        return {"gate": "error", "major": [], "minor": [],
                "error": "unparseable or missing assertions"}
    findings = assertions
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
    gate = gate_major(verdict)
    rec = {
        "chapter": nn, "lang": lang,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": backend, "model_id": model_id,
        "unit_sha256": hashlib.sha256(unit_payload).hexdigest(),
        "prompt_hash": hashlib.sha256(
            open(PROMPT_PATH, "rb").read()).hexdigest()[:16],
        "verdict": verdict,
        "gate": gate["gate"],
        "grounding": check_grounding(verdict, cn_text),
    }
    path = os.path.join(outdir, f"{nn}-{lang}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return path


def load_prompt():
    return open(PROMPT_PATH, encoding="utf-8").read()


def run_factcheck_cli(
    *,
    chapter,
    lang,
    cn_unit,
    tr_unit,
    outdir,
    stdin_verdict=None,
):
    cn_text = open(cn_unit, encoding="utf-8").read()
    tr_text = open(tr_unit, encoding="utf-8").read()
    backend = "inline"
    model_id = "mock-1"
    if stdin_verdict is not None:
        verdict = parse_verdict(stdin_verdict)
    else:
        opened = open_live_judge()
        if opened is None:
            print(json.dumps({
                "status": "judge_unavailable",
                "reason": "pass --stdin-verdict (mock) or set ZAI_API_KEY "
                          "(or judge.backend local-ollama); "
                          "exit 2 so pipelines do not treat this as clean",
            }, ensure_ascii=False))
            return 2
        client, backend, model_id = opened
        prompt = build_judge_prompt(cn_text, tr_text, lang)
        try:
            reply = client.complete(prompt)
        except Exception as e:
            print(json.dumps({
                "status": "judge_unavailable",
                "reason": f"live judge failed: {e}",
            }, ensure_ascii=False))
            return 2
        verdict = parse_verdict(reply)

    path = write_result(
        outdir, chapter, lang, verdict, cn_text, tr_text, backend, model_id
    )
    gate = gate_major(verdict)["gate"]
    grounding = check_grounding(verdict, cn_text)
    grounded = grounding["grounded"]
    print(json.dumps({
        "written": path,
        "gate": gate,
        "grounded": grounded,
        "backend": backend,
        "model_id": model_id,
    }, ensure_ascii=False))
    if gate in ("fail", "error") or not grounded:
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description="factcheck single unit (pass E)")
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--lang", required=True, choices=("ru", "en"))
    ap.add_argument("--cn-unit", required=True, help="path to CN unit md")
    ap.add_argument("--tr-unit", required=True, help="path to translated unit md")
    ap.add_argument("--stdin-verdict", help="inline verdict JSON (mock/tests)")
    ap.add_argument("--outdir", default=os.path.join(RESULTS, "factcheck"))
    args = ap.parse_args()
    return run_factcheck_cli(
        chapter=args.chapter,
        lang=args.lang,
        cn_unit=args.cn_unit,
        tr_unit=args.tr_unit,
        outdir=args.outdir,
        stdin_verdict=args.stdin_verdict,
    )


if __name__ == "__main__":
    sys.exit(main())
