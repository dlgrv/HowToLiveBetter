#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.llm.client import LLMError, chat, repo_root

LANGS = ("ru", "en", "es")

LOCALE_FIELD_HINTS = {
    "ru": (
        "Russian field labels (exact, as in book/ru):\n"
        "- Стоимость: (from - 成本：)\n"
        "- Простыми словами: (from - 说人话：)\n"
        "- Эффект: (from - 收益：)\n"
        "- Уровень доказательности: (from - 证据等级：)\n"
        "- Примечания: (from - 备注：)\n"
        "Do not translate 来源 lines; keep a single line §SRC§ for assemble to inject "
        "- Источники: verbatim from Chinese."
    ),
    "en": (
        "English field labels (exact, as in book/en):\n"
        "- Cost: (from - 成本：)\n"
        "- In plain terms: (from - 说人话：)\n"
        "- Benefit: (from - 收益：)\n"
        "- Evidence grade: (from - 证据等级：)\n"
        "- Notes: (from - 备注：)\n"
        "Do not translate 来源 lines; keep §SRC§ for assemble to inject - Sources:."
    ),
    "es": (
        "Spanish field labels (exact, as in book/es):\n"
        "- Costo: (from - 成本：)\n"
        "- En términos sencillos: (from - 说人话：)\n"
        "- Beneficio: (from - 收益：)\n"
        "- Nivel de evidencia: (from - 证据等级：)\n"
        "- Notas: (from - 备注：)\n"
        "Do not translate 来源 lines; keep §SRC§ for assemble to inject - Fuentes:."
    ),
}

RETRY_FIELD_EXAMPLES = {
    "ru": "- Стоимость: / - Простыми словами:",
    "en": "- Cost: / - In plain terms:",
    "es": "- Costo: / - En términos sencillos:",
}


def normalize_nn(nn: str) -> str:
    nn = nn.strip()
    if not re.fullmatch(r"\d{1,2}", nn):
        raise SystemExit(f"invalid --nn: {nn!r}")
    return f"{int(nn):02d}"


def normalize_unit(unit: str) -> str:
    unit = unit.strip()
    if not re.fullmatch(r"\d{1,2}", unit):
        raise SystemExit(f"invalid --unit: {unit!r}")
    return f"{int(unit):02d}"


def digest_root(root: Path) -> Path:
    return (root / "tools" / "digest").resolve()


def out_dir_is_under_digest(out_dir: Path, root: Path | None = None) -> bool:
    root = root or repo_root()
    digest = digest_root(root)
    try:
        out_dir.resolve().relative_to(digest)
        return True
    except ValueError:
        return False


def refuse_digest_outdir(out_dir: Path, root: Path | None = None) -> None:
    if out_dir_is_under_digest(out_dir, root):
        raise SystemExit(
            f"refusing --out-dir under tools/digest/: {out_dir.resolve()}"
        )


def strip_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", t, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip() + "\n"
    return t if t.endswith("\n") else t + "\n"


def build_messages(
    lang: str,
    unit_body: str,
    gloss: str | None,
    prompt_template: str,
) -> list[dict[str, str]]:
    user_parts = [
        f"Target locale: {lang}",
        "",
        LOCALE_FIELD_HINTS[lang],
        "",
        "Preserve §TAG§ and §SRC§ exactly (one line each). Preserve cost-tag HTML comments.",
        "If the unit starts with a Markdown heading (`### …` or `# …`), keep that heading "
        "as the first line and translate its title text — do not drop it.",
        "Unit 00 is chapter intro/preamble only: translate as prose (+ back-link if present). "
        "Do NOT invent Стоимость/Cost field blocks for unit 00.",
        "Output ONLY the translated unit markdown — no preamble, no fences.",
        "",
    ]
    if gloss:
        user_parts.extend(["---", gloss.rstrip(), "---", ""])
    user_parts.extend(["Chinese unit to translate:", "", unit_body.rstrip()])
    return [
        {"role": "system", "content": prompt_template.strip()},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def validate_item_unit(text: str, uu: str) -> list[str]:
    errs: list[str] = []
    if uu == "00":
        return errs
    if "§TAG§" not in text:
        errs.append("missing §TAG§")
    if "§SRC§" not in text:
        errs.append("missing §SRC§")
    if not re.search(r"^### ", text, re.M):
        errs.append("missing ### heading")
    return errs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Translate one digest unit via HTLB LLM.")
    p.add_argument("--nn", required=True, help="Chapter number (e.g. 01 or 1)")
    p.add_argument("--unit", required=True, help="Unit number (e.g. 01 or 1)")
    p.add_argument("--lang", required=True, choices=LANGS)
    p.add_argument(
        "--out-dir",
        required=True,
        help="Assemble workdir (parent of units/); never under tools/digest/",
    )
    args = p.parse_args(argv)

    root = repo_root()
    nn = normalize_nn(args.nn)
    uu = normalize_unit(args.unit)
    out_work = Path(args.out_dir)
    if not out_work.is_absolute():
        out_work = (Path.cwd() / out_work).resolve()
    else:
        out_work = out_work.resolve()

    refuse_digest_outdir(out_work, root)

    digest_unit = root / "tools" / "digest" / nn / "units" / f"{uu}.md"
    if not digest_unit.is_file():
        raise SystemExit(f"digest unit missing: {digest_unit}")

    unit_text = digest_unit.read_text(encoding="utf-8")
    gloss_path = digest_unit.with_suffix(".gloss.md")
    gloss = gloss_path.read_text(encoding="utf-8") if gloss_path.is_file() else None

    prompt_path = root / "tools" / "prompts" / "translate-unit.md"
    if not prompt_path.is_file():
        raise SystemExit(f"prompt missing: {prompt_path}")
    prompt_template = prompt_path.read_text(encoding="utf-8")

    messages = build_messages(args.lang, unit_text, gloss, prompt_template)
    max_attempts = 3 if uu != "00" else 2
    last_errs: list[str] = []
    translated = ""
    field_ex = RETRY_FIELD_EXAMPLES[args.lang]
    for attempt in range(1, max_attempts + 1):
        try:
            translated = chat(messages)
        except LLMError as e:
            print(f"LLM error: {e}", file=sys.stderr)
            return 1
        translated = strip_fence(translated)
        last_errs = validate_item_unit(translated, uu)
        if not last_errs:
            break
        print(
            f"attempt {attempt}/{max_attempts} structural fail ({uu}): "
            + ", ".join(last_errs),
            file=sys.stderr,
        )
        messages = build_messages(args.lang, unit_text, gloss, prompt_template)
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous draft failed structural checks: "
                    + ", ".join(last_errs)
                    + ". Re-output the FULL unit. Keep the translated ### title as "
                    "line 1, then a line with only §TAG§, then dashed field lines "
                    f"({field_ex} / …), then a line with only §SRC§. "
                    "Do not omit §TAG§ or §SRC§."
                ),
            }
        )
    else:
        print(
            f"structural validation failed after {max_attempts} attempts ({uu}): "
            + ", ".join(last_errs),
            file=sys.stderr,
        )
        return 2

    out_path = out_work / "units" / f"{uu}.md"
    atomic_write(out_path, translated if translated.endswith("\n") else translated + "\n")
    print(f"Wrote {out_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
