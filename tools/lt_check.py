#!/usr/bin/env python3
"""LanguageTool grammar check on plain-terms lines only (WARN-only, plan Task 5).

Self-hosted LT (Docker, $0). Runs after factcheck in the translation pipeline.
If the LT server is unreachable, emits a single skip warning — never fails the
chapter gate.

CLI: python3 tools/lt_check.py --file book/<lang>/<chapter>.md --lang ru|en|es
Exit code is ALWAYS 0; findings go to stdout as WARN lines or JSON.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_BASE_URL = "http://127.0.0.1:8010"
DEFAULT_TIMEOUT = 30.0

# Plain-terms field labels — same as tools/style_check.py PLAIN_FIELD.
PLAIN_FIELD = {
    "ru": "Простыми словами",
    "en": "In plain terms",
    "es": "En términos sencillos",
}

LT_LANG = {
    "ru": "ru-RU",
    "en": "en-US",
    "es": "es",
}


def lt_language_code(lang):
    """Map pipeline lang key to LanguageTool language code."""
    code = LT_LANG.get(lang)
    if not code:
        raise ValueError(f"unknown language {lang!r}; supported: {sorted(LT_LANG)}")
    return code


def extract_plain_segments(text, lang):
    """Return [{line_no, text}] for plain-terms field bodies only."""
    label = PLAIN_FIELD.get(lang)
    if not label:
        return []
    prefix = f"- {label}:"
    out = []
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped.startswith(prefix):
            continue
        body = stripped[len(prefix):].strip()
        if body:
            out.append({"line_no": line_no, "text": body})
    return out


def parse_response(data):
    """Normalize a LanguageTool /v2/check JSON body into warning dicts."""
    if not isinstance(data, dict):
        return []
    matches = data.get("matches")
    if not isinstance(matches, list):
        return []
    hits = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        rule = m.get("rule") or {}
        repl = []
        for r in m.get("replacements") or []:
            if isinstance(r, dict) and r.get("value"):
                repl.append(r["value"])
        hits.append({
            "message": m.get("message", ""),
            "short_message": m.get("shortMessage", ""),
            "offset": m.get("offset", 0),
            "length": m.get("length", 0),
            "rule_id": rule.get("id", ""),
            "issue_type": rule.get("issueType", ""),
            "replacements": repl[:5],
        })
    return hits


def _post_check(text, lang, base_url, timeout):
    """POST one snippet to LT; return parsed JSON dict or None if unreachable."""
    lt_lang = lt_language_code(lang)
    url = base_url.rstrip("/") + "/v2/check"
    form = urllib.parse.urlencode({
        "text": text,
        "language": lt_lang,
        "enabledOnly": "false",
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def check_text(text, lang, base_url=DEFAULT_BASE_URL, timeout=DEFAULT_TIMEOUT):
    """Check plain-terms lines via LT. Server down → single skip entry."""
    segments = extract_plain_segments(text, lang)
    if not segments:
        return []

    findings = []
    for seg in segments:
        raw = _post_check(seg["text"], lang, base_url, timeout)
        if raw is None:
            return [{"status": "skip", "reason": "server_down"}]
        for hit in parse_response(raw):
            hit["line_no"] = seg["line_no"]
            hit["plain_text"] = seg["text"]
            findings.append(hit)
    return findings


def main():
    ap = argparse.ArgumentParser(description="WARN-only LanguageTool check (plain-terms)")
    ap.add_argument("--file", required=True, help="markdown chapter file")
    ap.add_argument("--lang", required=True, help="language pack key (ru|en|es)")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"LT server base URL (default {DEFAULT_BASE_URL})")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read()
    try:
        findings = check_text(
            text, args.lang, base_url=args.base_url, timeout=args.timeout)
    except ValueError as e:
        print(f"WARN: {e}", file=sys.stderr)
        return 0

    if args.json:
        print(json.dumps({
            "file": args.file,
            "lang": args.lang,
            "warnings": findings,
        }, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            if f.get("status") == "skip":
                print(f"WARN: lt_check skip: {f.get('reason', 'unknown')}")
            else:
                span_hint = ""
                if f.get("plain_text") and f.get("length"):
                    pt = f["plain_text"]
                    off, ln = f["offset"], f["length"]
                    if off + ln <= len(pt):
                        span_hint = pt[off:off + ln]
                print(
                    f"WARN: line {f['line_no']}: [{f.get('rule_id', '')}] "
                    f"{f.get('message', '')}"
                    + (f" «{span_hint}»" if span_hint else "")
                )
        n = len([x for x in findings if x.get("status") != "skip"])
        if any(x.get("status") == "skip" for x in findings):
            print("lt_check: skip (server down, advisory, exit 0)")
        else:
            print(f"lt_check: {n} warnings (advisory, exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
