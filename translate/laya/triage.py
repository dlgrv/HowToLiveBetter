"""Triage after style_check: RU label hits → Laya System-1.

When style flags a triageable label (doubt), Laya is **required**:
server down / unreachable → exit 2 (same habit as make lt / LT down).
No triageable hits → exit 0 (no-op). Verdicts stay advisory (not HARD).

``--apply`` is reserved (default off; no autofix).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from translate.laya import client as laya_client
from translate.laya.questions import TRIAGE_LABELS, interpret_answer, questions_for_label
from translate.shelf.style_check import check_text

VERDICTS = frozenset({"bug", "ok", "unclear", "skip_server_down"})


def _state_for_finding(text: str, finding: dict[str, Any]) -> str:
    """Build a short state: line context + flagged span."""
    lines = text.splitlines()
    line_no = int(finding.get("line_no") or 1)
    idx = max(0, min(len(lines) - 1, line_no - 1))
    line = lines[idx] if lines else ""
    span = finding.get("span") or ""
    label = finding.get("label") or ""
    return f"label={label}\nspan={span}\nline={line}"


def triage_text(
    text: str,
    lang: str,
    *,
    base_url: str | None = None,
    timeout: float = laya_client.DEFAULT_TIMEOUT,
    plain_only: bool = False,
) -> list[dict[str, Any]]:
    """Filter style hits to triage labels; ask Laya; return cards."""
    findings = check_text(text, lang, plain_only=plain_only)
    candidates = [f for f in findings if f.get("label") in TRIAGE_LABELS]
    if not candidates:
        return []

    root = base_url or laya_client.base_url_from_env()
    if laya_client.healthz(root, timeout=timeout) is None:
        return [
            {
                "label": f.get("label"),
                "line_no": f.get("line_no"),
                "span": f.get("span"),
                "verdict": "skip_server_down",
            }
            for f in candidates
        ]

    out: list[dict[str, Any]] = []
    for finding in candidates:
        label = finding["label"]
        questions = questions_for_label(label)
        if questions is None:
            continue
        state = _state_for_finding(text, finding)
        resp = laya_client.systemone(
            state,
            questions,
            base_url=root,
            model="multilingual",
            timeout=timeout,
        )
        verdict = "skip_server_down" if resp is None else interpret_answer(resp)
        card = {
            "label": label,
            "line_no": finding.get("line_no"),
            "span": finding.get("span"),
            "verdict": verdict,
        }
        if resp is not None:
            card["raw_answer"] = (resp.get("answers") or {}).get("verdict")
        out.append(card)
    return out


def triage_file(
    path: Path | str,
    lang: str,
    *,
    base_url: str | None = None,
    timeout: float = laya_client.DEFAULT_TIMEOUT,
    plain_only: bool = False,
) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    return triage_text(
        text,
        lang,
        base_url=base_url,
        timeout=timeout,
        plain_only=plain_only,
    )


def exit_code_for_cards(cards: list[dict[str, Any]]) -> int:
    """0 = ok / no hits; 2 = triage required but Laya unreachable."""
    if any(c.get("verdict") == "skip_server_down" for c in cards):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Laya triage after style_check (RU). "
            "Required when triageable hits exist; exit 2 if server down."
        )
    )
    ap.add_argument("file", nargs="?", help="chapter markdown path")
    ap.add_argument("--lang", required=True, help="language pack (ru for triage labels)")
    ap.add_argument("--base-url", default=None, help="Override HTLB_LAYA_BASE_URL")
    ap.add_argument("--timeout", type=float, default=laya_client.DEFAULT_TIMEOUT)
    ap.add_argument("--plain-only", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit cards as JSON")
    ap.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="reserved: autofix OFF by default; not implemented",
    )
    args = ap.parse_args(argv)

    if args.apply:
        print(
            "laya triage: --apply is reserved (no autofix in this release); report only",
            file=sys.stderr,
        )

    if not args.file:
        print("ERROR: chapter file required", file=sys.stderr)
        return 2

    if args.lang != "ru":
        print(
            f"laya triage: skip (labels are RU-only; got lang={args.lang})",
            file=sys.stderr,
        )
        return 0

    try:
        cards = triage_file(
            args.file,
            args.lang,
            base_url=args.base_url,
            timeout=args.timeout,
            plain_only=args.plain_only,
        )
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    code = exit_code_for_cards(cards)
    if args.json:
        print(
            json.dumps(
                {
                    "file": args.file,
                    "lang": args.lang,
                    "cards": cards,
                    "exit": code,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for c in cards:
            print(
                f"WARN: line {c.get('line_no')}: [{c.get('label')}] "
                f"{c.get('verdict')} — {c.get('span')}"
            )
        if code == 2:
            print(
                f"laya triage: {len(cards)} cards need Laya but server down (exit 2)",
                file=sys.stderr,
            )
        elif not cards:
            print("laya triage: 0 cards (no triageable style hits, exit 0)")
        else:
            print(f"laya triage: {len(cards)} cards (advisory, exit 0)")
    return code


if __name__ == "__main__":
    sys.exit(main())
