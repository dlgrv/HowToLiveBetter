"""Laya clarity pass: each plain-terms line → понятно | непонятно.

Same question for ru / en / es. Advisory: ``непонятно`` does not fail the
chapter. Server down when there are lines to score → exit 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from translate.laya import client as laya_client
from translate.laya.questions import CLARITY_QUESTIONS, interpret_clarity
from translate.lib.labels import PLAIN_FIELD_INDEX, field_labels

VERDICTS = frozenset({"понятно", "непонятно", "skip_server_down"})


def plain_terms_lines(text: str, lang: str) -> list[dict[str, Any]]:
    """Return [{line_no, text}] for the plain-terms field only."""
    label = field_labels(lang)[PLAIN_FIELD_INDEX]
    prefix = f"- {label}:"
    out: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(prefix):
            body = stripped[len(prefix) :].strip()
            if body:
                out.append({"line_no": i, "text": body})
    return out


def score_lines(
    lines: list[dict[str, Any]],
    *,
    base_url: str | None = None,
    timeout: float = laya_client.DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Ask Laya about each plain-terms line. Empty input → []."""
    if not lines:
        return []

    root = base_url or laya_client.base_url_from_env()
    if laya_client.healthz(root, timeout=timeout) is None:
        return [
            {
                "line_no": row["line_no"],
                "text": row["text"],
                "verdict": "skip_server_down",
            }
            for row in lines
        ]

    cards: list[dict[str, Any]] = []
    for row in lines:
        resp = laya_client.systemone(
            row["text"],
            CLARITY_QUESTIONS,
            base_url=root,
            model="multilingual",
            timeout=timeout,
        )
        verdict = "skip_server_down" if resp is None else interpret_clarity(resp)
        cards.append({"line_no": row["line_no"], "text": row["text"], "verdict": verdict})
    return cards


def exit_code_for_cards(cards: list[dict[str, Any]]) -> int:
    if any(c.get("verdict") == "skip_server_down" for c in cards):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Laya clarity on plain-terms lines (понятно/непонятно; ru|en|es)"
    )
    ap.add_argument("file", help="chapter markdown")
    ap.add_argument("--lang", required=True, choices=("ru", "en", "es"))
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--timeout", type=float, default=laya_client.DEFAULT_TIMEOUT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        text = Path(args.file).read_text(encoding="utf-8")
        lines = plain_terms_lines(text, args.lang)
        cards = score_lines(lines, base_url=args.base_url, timeout=args.timeout)
    except (OSError, KeyError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    code = exit_code_for_cards(cards)
    unclear = [c for c in cards if c["verdict"] == "непонятно"]
    if args.json:
        print(
            json.dumps(
                {
                    "file": args.file,
                    "lang": args.lang,
                    "cards": cards,
                    "not_plain": len(unclear),
                    "exit": code,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for c in cards:
            if c["verdict"] == "понятно":
                continue
            snippet = c["text"]
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            print(f"{c['verdict']}: line {c['line_no']}: {snippet}")
        if code == 2:
            print(
                f"laya clarity: {len(cards)} lines but server down (exit 2)",
                file=sys.stderr,
            )
        else:
            print(f"laya clarity: {len(cards)} lines, {len(unclear)} непонятно (advisory, exit 0)")
    return code


if __name__ == "__main__":
    sys.exit(main())
