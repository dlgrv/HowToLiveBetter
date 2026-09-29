#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from translate.lib.config import default_root, translation_langs, unit_dir
from translate.llm.client import LLMError, chat
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


def build_simplify_messages(
    lang: str,
    unit_body: str,
    current_tr: str,
    prompt_template: str,
    *,
    uu: str,
) -> list[dict[str, str]]:
    user_parts = [
        f"Target locale: {lang}",
        f"Unit id: {uu}",
        "",
        LOCALE_FIELD_HINTS[lang],
        "",
        "Rewrite ONLY the plain-terms field so a non-expert neighbor gets it.",
        "Keep every other field byte-identical in meaning and structure.",
        "Output ONLY the full unit markdown — no preamble, no fences.",
        "",
        "---",
        "Current translation of the unit:",
        "",
        current_tr.rstrip(),
        "---",
        "",
        "Chinese unit (meaning anchor):",
        "",
        unit_body.rstrip(),
    ]
    return [
        {"role": "system", "content": prompt_template.strip()},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Simplify plain-terms in one unit (Hy-MT2).")
    p.add_argument("--nn", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--lang", required=True, choices=translation_langs())
    p.add_argument("--out-dir", required=True, help="workdir (parent of units/)")
    args = p.parse_args(argv)

    root = Path(default_root())
    nn = normalize_nn(args.nn)
    uu = normalize_unit(args.unit)
    out_work = Path(args.out_dir).resolve()
    refuse_digest_outdir(out_work, root)

    digest_unit = Path(unit_dir(str(root), "cn", nn)) / f"{uu}.md"
    if not digest_unit.is_file():
        raise SystemExit(f"digest unit missing: {digest_unit}")
    unit_text = strip_mechanical_markers(digest_unit.read_text(encoding="utf-8"))

    tr_path = out_work / "units" / f"{uu}.md"
    if not tr_path.is_file():
        raise SystemExit(f"translated unit missing: {tr_path}")
    current_tr = strip_mechanical_markers(tr_path.read_text(encoding="utf-8"))

    prompt_path = root / "translate" / "prompts" / "simplify-plain.md"
    if not prompt_path.is_file():
        raise SystemExit(f"prompt missing: {prompt_path}")
    prompt_template = prompt_path.read_text(encoding="utf-8")

    messages = build_simplify_messages(args.lang, unit_text, current_tr, prompt_template, uu=uu)
    max_attempts = 3
    last_errs: list[str] = []
    simplified = ""
    for attempt in range(1, max_attempts + 1):
        try:
            simplified = chat(messages)
        except LLMError as e:
            print(f"LLM error: {e}", file=sys.stderr)
            return 1
        simplified = strip_fence(simplified)
        simplified = inject_mechanical_markers(simplified, uu)
        last_errs = validate_unit(simplified, uu, args.lang)
        if not last_errs:
            break
        print(
            f"attempt {attempt}/{max_attempts} structural fail ({uu}): " + ", ".join(last_errs),
            file=sys.stderr,
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous draft failed structural checks: "
                    + ", ".join(last_errs)
                    + ". Re-output the FULL unit: line 1 `### N. …`, "
                    "dashed `- Label:` fields, no §TAG§/§SRC§, no bold labels. "
                    "Change only the plain-terms field."
                ),
            }
        )
    else:
        print(f"simplify failed after {max_attempts} attempts ({uu})", file=sys.stderr)
        return 2

    atomic_write(tr_path, simplified if simplified.endswith("\n") else simplified + "\n")
    try:
        shown = tr_path.relative_to(root)
    except ValueError:
        shown = tr_path
    print(f"Simplified {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
