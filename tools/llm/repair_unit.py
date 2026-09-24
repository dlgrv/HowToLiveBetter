#!/usr/bin/env python3
"""Repair one translated digest unit for verify.py HARD fails (LLM, constrained).

Repairs only kinds number_absent / banned_calque. After the LLM draft:
strip → inject mechanical markers → validate_unit (same gate as translation).

Exit codes: 0 ok; 2 structural fail after retries; 1 LLM/infra error.
Never writes under tools/digest/ (only <out-dir>/units/<unit>.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.llm.client import LLMError, chat, repo_root  # noqa: E402
from tools.llm.verify_issues import issues_still_present  # noqa: E402
from tools.llm.translate_unit import (  # noqa: E402
    LOCALE_FIELD_HINTS,
    atomic_write,
    normalize_nn,
    normalize_unit,
    refuse_digest_outdir,
    strip_fence,
    strip_mechanical_markers,
    inject_mechanical_markers,
    validate_unit,
)

REPAIRABLE_KINDS = frozenset({"number_absent", "banned_calque"})

ISSUE_LINES = {
    "number_absent": lambda iss: (
        f"- number_absent: must include the absolute value {iss['value']} "
        f"somewhere in the unit (count needed: {iss.get('count', 1)})"
        # CN anchor (review H4): when the CN unit has several similar numbers,
        # the anchor line tells the model WHICH sentence the value belongs to.
        + (f"\n  CN source line: {iss['cn_context']}" if iss.get("cn_context") else "")
    ),
    "banned_calque": lambda iss: (
        f"- banned_calque: replace the stem «{iss['stem']}» everywhere except "
        f"at most one first-use gloss (currently {iss.get('count', '?')} occurrences)"
    ),
}


def build_repair_messages(
    lang: str,
    unit_body: str,
    current_tr: str,
    issues: list[dict],
    prompt_template: str,
    *,
    uu: str,
) -> list[dict[str, str]]:
    issue_block = "\n".join(
        ISSUE_LINES[i["kind"]](i) for i in issues if i.get("kind") in REPAIRABLE_KINDS
    )
    user_parts = [
        f"Target locale: {lang}",
        f"Unit id: {uu}",
        "",
        LOCALE_FIELD_HINTS[lang],
        "",
        "Issues to fix (machine):",
        issue_block,
        "",
        "Output ONLY the repaired unit markdown — no preamble, no fences.",
        "",
        "---",
        "Current translation of the unit:",
        "",
        current_tr.rstrip(),
        "---",
        "",
        "Chinese unit (source of truth for numbers):",
        "",
        unit_body.rstrip(),
    ]
    return [
        {"role": "system", "content": prompt_template.strip()},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Repair one translated unit (verify fails).")
    p.add_argument("--nn", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--lang", required=True, choices=["ru", "en", "es"])
    p.add_argument("--out-dir", required=True, help="workdir (parent of units/)")
    p.add_argument(
        "--issues-json", required=True,
        help='JSON list, e.g. [{"kind":"number_absent","value":"610000","count":1}]',
    )
    args = p.parse_args(argv)

    try:
        issues = json.loads(args.issues_json)
    except ValueError as e:
        raise SystemExit(f"invalid --issues-json: {e}")
    if not isinstance(issues, list) or not issues:
        raise SystemExit("--issues-json must be a non-empty list")
    bad = [i for i in issues if i.get("kind") not in REPAIRABLE_KINDS]
    if bad:
        raise SystemExit(f"unrepairable kinds in --issues-json: {bad}")

    root = Path(repo_root())
    nn = normalize_nn(args.nn)
    uu = normalize_unit(args.unit)
    out_work = Path(args.out_dir).resolve()
    refuse_digest_outdir(out_work, root)

    digest_unit = root / "tools" / "digest" / nn / "units" / f"{uu}.md"
    if not digest_unit.is_file():
        raise SystemExit(f"digest unit missing: {digest_unit}")
    unit_text = strip_mechanical_markers(digest_unit.read_text(encoding="utf-8"))

    tr_path = out_work / "units" / f"{uu}.md"
    if not tr_path.is_file():
        raise SystemExit(f"translated unit missing: {tr_path}")
    current_tr = strip_mechanical_markers(tr_path.read_text(encoding="utf-8"))

    prompt_path = root / "tools" / "prompts" / "repair-unit.md"
    if not prompt_path.is_file():
        raise SystemExit(f"prompt missing: {prompt_path}")
    prompt_template = prompt_path.read_text(encoding="utf-8")

    messages = build_repair_messages(
        args.lang, unit_text, current_tr, issues, prompt_template, uu=uu)
    max_attempts = 3
    last_errs: list[str] = []
    repaired = ""
    for attempt in range(1, max_attempts + 1):
        try:
            repaired = chat(messages)
        except LLMError as e:
            print(f"LLM error: {e}", file=sys.stderr)
            return 1
        repaired = strip_fence(repaired)
        repaired = inject_mechanical_markers(repaired, uu)
        last_errs = validate_unit(repaired, uu, args.lang)
        if last_errs:
            print(
                f"attempt {attempt}/{max_attempts} structural fail ({uu}): "
                + ", ".join(last_errs),
                file=sys.stderr,
            )
            messages.append({
                "role": "user",
                "content": (
                    "Your previous draft failed structural checks: "
                    + ", ".join(last_errs)
                    + ". Re-output the FULL repaired unit: line 1 `### N. …`, "
                    "dashed `- Label:` fields, no §TAG§/§SRC§, no bold labels."
                ),
            })
            continue
        leftovers = issues_still_present(strip_mechanical_markers(repaired),
                                         issues, args.lang)
        if not leftovers:
            break
        print(
            f"attempt {attempt}/{max_attempts} issue assert fail ({uu}): "
            + ", ".join(leftovers),
            file=sys.stderr,
        )
        messages.append({
            "role": "user",
            "content": (
                "Your previous draft did NOT fix: " + ", ".join(leftovers)
                + ". Re-output the FULL unit with the listed issue(s) fixed. "
                "Numbers: write the absolute value with digits (e.g. 610 000)."
            ),
        })
    else:
        print(f"repair failed after {max_attempts} attempts ({uu})", file=sys.stderr)
        return 2

    atomic_write(tr_path, repaired if repaired.endswith("\n") else repaired + "\n")
    try:
        shown = tr_path.relative_to(root)
    except ValueError:
        shown = tr_path
    print(f"Repaired {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
