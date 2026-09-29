#!/usr/bin/env python3
"""LanguageTool grammar check on plain-terms lines (required local step).

Self-hosted LT (Docker :8010). Run after green verify, before polish.
Server unreachable with plain-terms to check → exit 2.
Grammar hits print as WARN lines; exit 0 when LT answered.

CLI: python3 translate/shelf/lt_check.py --file book/<lang>/<chapter>.md --lang ru|en|es
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from translate.lib.labels import PLAIN_FIELD_INDEX, field_labels

DEFAULT_BASE_URL = os.environ.get("HTLB_LT_BASE_URL", "http://127.0.0.1:8010")
DEFAULT_TIMEOUT = 30.0

LT_LANG = {
    "ru": "ru-RU",
    "en": "en-US",
    "es": "es",
}


def lt_language_code(lang):
    code = LT_LANG.get(lang)
    if not code:
        raise ValueError(f"unknown language {lang!r}; supported: {sorted(LT_LANG)}")
    return code


def extract_plain_segments(text, lang):
    if lang not in LT_LANG:
        return []
    prefix = f"- {field_labels(lang)[PLAIN_FIELD_INDEX]}:"
    out = []
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped.startswith(prefix):
            continue
        body = stripped[len(prefix) :].strip()
        if body:
            out.append({"line_no": line_no, "text": body})
    return out


def parse_response(data):
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
        repl = [
            r["value"]
            for r in m.get("replacements") or []
            if isinstance(r, dict) and r.get("value")
        ]
        hits.append(
            {
                "message": m.get("message", ""),
                "short_message": m.get("shortMessage", ""),
                "offset": m.get("offset", 0),
                "length": m.get("length", 0),
                "rule_id": rule.get("id", ""),
                "issue_type": rule.get("issueType", ""),
                "replacements": repl[:5],
            }
        )
    return hits


def _post_check(text, lang, base_url, timeout):
    lt_lang = lt_language_code(lang)
    url = base_url.rstrip("/") + "/v2/check"
    form = urllib.parse.urlencode(
        {
            "text": text,
            "language": lt_lang,
            "enabledOnly": "false",
        }
    ).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def check_text(text, lang, base_url=DEFAULT_BASE_URL, timeout=DEFAULT_TIMEOUT):
    segments = extract_plain_segments(text, lang)
    if not segments:
        return []

    findings = []
    saw_ok = False
    for seg in segments:
        raw = _post_check(seg["text"], lang, base_url, timeout)
        if raw is None:
            reason = "skip_partial" if saw_ok else "server_down"
            findings.append({"status": "skip", "reason": reason, "line_no": seg["line_no"]})
            continue
        saw_ok = True
        for hit in parse_response(raw):
            hit["line_no"] = seg["line_no"]
            hit["plain_text"] = seg["text"]
            findings.append(hit)
    return findings


def exit_code_for_findings(findings):
    if any(f.get("status") == "skip" for f in findings):
        return 2
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="LanguageTool check (plain-terms; required)")
    ap.add_argument("--file", required=True, help="markdown chapter file")
    ap.add_argument("--lang", required=True, help="language pack key (ru|en|es)")
    ap.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"LT server base URL (default {DEFAULT_BASE_URL})",
    )
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = ap.parse_args(argv)

    try:
        text = open(args.file, encoding="utf-8").read()
    except OSError as e:
        print(f"lt_check: cannot read {args.file}: {e}", file=sys.stderr)
        return 2

    try:
        findings = check_text(text, args.lang, base_url=args.base_url, timeout=args.timeout)
    except ValueError as e:
        print(f"lt_check: {e}", file=sys.stderr)
        return 2

    code = exit_code_for_findings(findings)
    if args.json:
        print(
            json.dumps(
                {
                    "file": args.file,
                    "lang": args.lang,
                    "warnings": findings,
                    "exit": code,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for f in findings:
            if f.get("status") == "skip":
                print(f"FAIL: lt_check {f.get('reason', 'unknown')}", file=sys.stderr)
            else:
                span_hint = ""
                if f.get("plain_text") and f.get("length"):
                    pt = f["plain_text"]
                    off, ln = f["offset"], f["length"]
                    if off + ln <= len(pt):
                        span_hint = pt[off : off + ln]
                print(
                    f"WARN: line {f['line_no']}: [{f.get('rule_id', '')}] "
                    f"{f.get('message', '')}" + (f" «{span_hint}»" if span_hint else "")
                )
        n = len([x for x in findings if x.get("status") != "skip"])
        skips = [x for x in findings if x.get("status") == "skip"]
        if code == 2:
            reasons = sorted({x.get("reason", "unknown") for x in skips})
            print(f"lt_check: LT_DOWN ({', '.join(reasons)})", file=sys.stderr)
        else:
            print(f"lt_check: {n} warnings")
    return code


if __name__ == "__main__":
    sys.exit(main())
