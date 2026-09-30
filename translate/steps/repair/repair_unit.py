#!/usr/bin/env python3
"""Repair one translated digest unit for verify.py HARD fails.

Kinds: number_absent / banned_calque.

**number_absent is mechanical first** (locale-aware digit inject into Notes).
LLM re-prompt for digits is skipped when inject clears the assert — Hy-MT2
oscillates on absolute values and is not worth the slot. banned_calque still
uses the constrained LLM path.

After any draft: strip → collapse multiline fields → markers → validate_unit.

Exit codes: 0 ok; 2 structural fail after retries; 1 LLM/infra error.
Never writes under translate/digest/ (only <out-dir>/units/<unit>.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from translate.lib.config import default_root, translation_langs
from translate.llm.client import LLMError, chat
from translate.steps.repair.mechanical import collapse_multiline_fields, mechanical_fix_unit
from translate.steps.repair.verify_issues import REPAIRABLE_KINDS, issues_still_present
from translate.steps.translate.translate_unit import (
    LOCALE_FIELD_HINTS,
    atomic_write,
    inject_mechanical_markers,
    normalize_nn,
    normalize_unit,
    refuse_digest_outdir,
    strip_fence,
    strip_mechanical_markers,
    validate_unit,
)

ISSUE_LINES = {
    "number_absent": lambda iss: (
        f"- number_absent: must include the absolute value {iss['value']} "
        f"somewhere in the unit (count needed: {iss.get('count', 1)})"
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
    p.add_argument("--lang", required=True, choices=translation_langs())
    p.add_argument("--out-dir", required=True, help="workdir (parent of units/)")
    p.add_argument(
        "--issues-json",
        required=True,
        help='JSON list, e.g. [{"kind":"number_absent","value":"610000","count":1}]',
    )
    args = p.parse_args(argv)

    try:
        issues = json.loads(args.issues_json)
    except ValueError as e:
        raise SystemExit(f"invalid --issues-json: {e}") from None
    if not isinstance(issues, list) or not issues:
        raise SystemExit("--issues-json must be a non-empty list")
    bad = [i for i in issues if i.get("kind") not in REPAIRABLE_KINDS]
    if bad:
        raise SystemExit(f"unrepairable kinds in --issues-json: {bad}")

    root = Path(default_root())
    nn = normalize_nn(args.nn)
    uu = normalize_unit(args.unit)
    out_work = Path(args.out_dir).resolve()
    refuse_digest_outdir(out_work, root)

    from translate.lib.config import unit_dir

    digest_unit = Path(unit_dir(str(root), "cn", nn)) / f"{uu}.md"
    if not digest_unit.is_file():
        raise SystemExit(f"digest unit missing: {digest_unit}")
    unit_text = strip_mechanical_markers(digest_unit.read_text(encoding="utf-8"))

    tr_path = out_work / "units" / f"{uu}.md"
    if not tr_path.is_file():
        raise SystemExit(f"translated unit missing: {tr_path}")
    current_tr = strip_mechanical_markers(tr_path.read_text(encoding="utf-8"))

    # 1) Structural collapse + mechanical number inject (no LLM).
    draft = collapse_multiline_fields(current_tr, args.lang)
    number_issues = [i for i in issues if i.get("kind") == "number_absent"]
    calque_issues = [i for i in issues if i.get("kind") == "banned_calque"]
    if number_issues:
        draft = mechanical_fix_unit(draft, number_issues, args.lang)
        leftover_nums = issues_still_present(draft, number_issues, args.lang)
        if leftover_nums:
            print(
                f"mechanical number fix failed ({uu}): " + ", ".join(leftover_nums),
                file=sys.stderr,
            )
            return 2
        print(f"mechanical number_absent cleared ({uu})", file=sys.stderr)

    # 2) LLM only for banned_calque (digits stay mechanical).
    repaired = draft
    if calque_issues:
        prompt_path = root / "translate" / "prompts" / "repair-unit.md"
        if not prompt_path.is_file():
            raise SystemExit(f"prompt missing: {prompt_path}")
        prompt_template = prompt_path.read_text(encoding="utf-8")
        messages = build_repair_messages(
            args.lang, unit_text, draft, calque_issues, prompt_template, uu=uu
        )
        max_attempts = 3
        last_errs: list[str] = []
        for attempt in range(1, max_attempts + 1):
            try:
                repaired = chat(messages)
            except LLMError as e:
                print(f"LLM error: {e}", file=sys.stderr)
                return 1
            repaired = strip_fence(repaired)
            repaired = collapse_multiline_fields(repaired, args.lang)
            # Re-apply number inject so calque rewrite cannot drop digits again.
            if number_issues:
                repaired = mechanical_fix_unit(repaired, number_issues, args.lang)
            repaired = inject_mechanical_markers(repaired, uu)
            last_errs = validate_unit(repaired, uu, args.lang)
            if last_errs:
                print(
                    f"attempt {attempt}/{max_attempts} structural fail ({uu}): "
                    + ", ".join(last_errs),
                    file=sys.stderr,
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous draft failed structural checks: "
                            + ", ".join(last_errs)
                            + ". Re-output the FULL repaired unit: line 1 `### N. …`, "
                            "dashed `- Label:` fields, no §TAG§/§SRC§, no bold labels."
                        ),
                    }
                )
                continue
            leftovers = issues_still_present(
                strip_mechanical_markers(repaired), calque_issues, args.lang
            )
            if not leftovers:
                break
            print(
                f"attempt {attempt}/{max_attempts} issue assert fail ({uu}): "
                + ", ".join(leftovers),
                file=sys.stderr,
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous draft did NOT fix: "
                        + ", ".join(leftovers)
                        + ". Re-output the FULL unit with the listed issue(s) fixed."
                    ),
                }
            )
        else:
            print(f"repair failed after {max_attempts} attempts ({uu})", file=sys.stderr)
            return 2
    else:
        repaired = inject_mechanical_markers(repaired, uu)
        last_errs = validate_unit(repaired, uu, args.lang)
        if last_errs:
            print(
                f"structural fail after mechanical ({uu}): " + ", ".join(last_errs),
                file=sys.stderr,
            )
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
