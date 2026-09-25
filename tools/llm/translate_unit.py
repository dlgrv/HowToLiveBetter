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

# Exact list-field prefixes assemble / verify / index expect (locale book style).
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "ru": (
        "- Стоимость:",
        "- Простыми словами:",
        "- Эффект:",
        "- Уровень доказательности:",
        "- Примечания:",
    ),
    "en": (
        "- Cost:",
        "- In plain terms:",
        "- Benefit:",
        "- Evidence grade:",
        "- Notes:",
    ),
    "es": (
        "- Costo:",
        "- En términos sencillos:",
        "- Beneficio:",
        "- Nivel de evidencia:",
        "- Notas:",
    ),
}

LOCALE_FIELD_HINTS = {
    "ru": (
        "Russian field labels (exact list syntax, as in book/ru):\n"
        + "\n".join(REQUIRED_FIELDS["ru"])
        + "\nDo NOT use bold labels like **Стоимость:** — only `- Стоимость:`.\n"
        "Do NOT output §TAG§ or §SRC§ — the pipeline injects them after you translate.\n"
        "Do not translate 来源 lines (they are stripped from the source you see)."
    ),
    "en": (
        "English field labels (exact list syntax, as in book/en):\n"
        + "\n".join(REQUIRED_FIELDS["en"])
        + "\nDo NOT use bold labels like **Cost:** — only `- Cost:`.\n"
        "Do NOT output §TAG§ or §SRC§ — the pipeline injects them after you translate.\n"
        "Do not translate 来源 lines (they are stripped from the source you see)."
    ),
    "es": (
        "Spanish field labels (exact list syntax, as in book/es):\n"
        + "\n".join(REQUIRED_FIELDS["es"])
        + "\nDo NOT use bold labels like **Costo:** — only `- Costo:`.\n"
        "Do NOT output §TAG§ or §SRC§ — the pipeline injects them after you translate.\n"
        "Do not translate 来源 lines (they are stripped from the source you see)."
    ),
}

RETRY_FIELD_EXAMPLES = {
    "ru": "- Стоимость: / - Простыми словами:",
    "en": "- Cost: / - In plain terms:",
    "es": "- Costo: / - En términos sencillos:",
}

_MARKER_LINE = re.compile(r"^§(?:TAG|SRC)§\s*$")
_BOLD_FIELD = re.compile(r"^\*\*[^*:\n]+:\*\*", re.M)


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


def strip_mechanical_markers(text: str) -> str:
    """Drop §TAG§ / §SRC§ lines (digest or model-invented) before LLM / before reinject."""
    out: list[str] = []
    for line in text.splitlines():
        if _MARKER_LINE.match(line.strip()):
            continue
        # Model sometimes writes "§TAG§ something"
        s = line.strip()
        if s.startswith("§TAG§") or s.startswith("§SRC§"):
            continue
        out.append(line)
    return ("\n".join(out).rstrip() + "\n") if out else "\n"


def inject_mechanical_markers(text: str, uu: str) -> str:
    """
    Item units: after first ### line insert §TAG§; append lone §SRC§ at end.
    Unit 00: only strip markers — intro must stay prose + # title.
    """
    cleaned = strip_mechanical_markers(text)
    if uu == "00":
        return cleaned if cleaned.endswith("\n") else cleaned + "\n"

    lines = cleaned.splitlines()
    out: list[str] = []
    tagged = False
    for line in lines:
        out.append(line)
        if not tagged and line.startswith("### "):
            out.append("§TAG§")
            tagged = True
    while out and out[-1].strip() == "":
        out.pop()
    out.append("§SRC§")
    return "\n".join(out) + "\n"


def validate_unit(text: str, uu: str, lang: str) -> list[str]:
    """Structural gate after marker inject (items) or strip (intro)."""
    errs: list[str] = []
    fields = REQUIRED_FIELDS[lang]

    if uu == "00":
        if "§TAG§" in text or "§SRC§" in text:
            errs.append("intro must not contain §TAG§/§SRC§")
        if re.search(r"^### ", text, re.M):
            errs.append("intro must not use ### (item) heading")
        if not re.search(r"^# ", text, re.M):
            errs.append("intro missing # chapter title")
        for lab in fields:
            if re.search(rf"^{re.escape(lab)}", text, re.M):
                errs.append(f"intro must not invent field {lab}")
        if _BOLD_FIELD.search(text):
            errs.append("intro must not use bold **Label:** fields")
        return errs

    tag_n = len(re.findall(r"^§TAG§\s*$", text, re.M))
    src_n = len(re.findall(r"^§SRC§\s*$", text, re.M))
    if tag_n != 1:
        errs.append(f"need exactly one §TAG§ line (got {tag_n})")
    if src_n != 1:
        errs.append(f"need exactly one §SRC§ line (got {src_n})")

    heads = re.findall(r"^### .+$", text, re.M)
    if len(heads) != 1:
        errs.append(f"need exactly one ### heading (got {len(heads)})")
    else:
        m = re.match(r"^### (\d+)\.", heads[0])
        if m and int(m.group(1)) != int(uu):
            errs.append(f"heading number {m.group(1)} != unit {uu}")

    if _BOLD_FIELD.search(text):
        errs.append("bold **Label:** fields forbidden; use - Label:")

    for lab in fields:
        if not re.search(rf"^{re.escape(lab)}", text, re.M):
            errs.append(f"missing {lab}")

    return errs


def build_messages(
    lang: str,
    unit_body: str,
    gloss: str | None,
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
    ]
    if uu == "00":
        user_parts.extend(
            [
                "This is unit 00 (chapter intro only).",
                "Output: optional Markdown back-link, then one `# …` title, then prose.",
                "Do NOT invent ### headings, §TAG§, §SRC§, or Cost/Стоимость field blocks.",
                "",
            ]
        )
    else:
        user_parts.extend(
            [
                "Item unit: first line must be `### N. …` (same N as Chinese), then dashed "
                "field lines with exact locale labels.",
                "Do NOT output §TAG§ or §SRC§ (pipeline injects them).",
                "Do NOT use bold **Label:** for fields.",
                "",
            ]
        )
    user_parts.append("Output ONLY the translated unit markdown — no preamble, no fences.")
    user_parts.append("")
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

    unit_text = strip_mechanical_markers(digest_unit.read_text(encoding="utf-8"))
    gloss_path = digest_unit.with_suffix(".gloss.md")
    gloss = gloss_path.read_text(encoding="utf-8") if gloss_path.is_file() else None

    prompt_path = root / "tools" / "prompts" / "translate-unit.md"
    if not prompt_path.is_file():
        raise SystemExit(f"prompt missing: {prompt_path}")
    prompt_template = prompt_path.read_text(encoding="utf-8")

    messages = build_messages(args.lang, unit_text, gloss, prompt_template, uu=uu)
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
        translated = inject_mechanical_markers(translated, uu)
        last_errs = validate_unit(translated, uu, args.lang)
        if not last_errs:
            break
        print(
            f"attempt {attempt}/{max_attempts} structural fail ({uu}): "
            + ", ".join(last_errs),
            file=sys.stderr,
        )
        messages = build_messages(args.lang, unit_text, gloss, prompt_template, uu=uu)
        if uu == "00":
            fix = (
                "Your previous draft failed: "
                + ", ".join(last_errs)
                + ". Re-output ONLY intro: optional back-link, one `# …` title, prose. "
                "No ###, no §TAG§/§SRC§, no Стоимость/Cost field blocks."
            )
        else:
            fix = (
                "Your previous draft failed structural checks: "
                + ", ".join(last_errs)
                + ". Re-output the FULL unit. Line 1: `### N. …` (same N). "
                f"Then dashed fields ({field_ex} / …). "
                "Do NOT output §TAG§ or §SRC§. Do NOT use **Label:** bold fields."
            )
        messages.append({"role": "user", "content": fix})
    else:
        print(
            f"structural validation failed after {max_attempts} attempts ({uu}): "
            + ", ".join(last_errs),
            file=sys.stderr,
        )
        return 2

    out_path = out_work / "units" / f"{uu}.md"
    atomic_write(out_path, translated if translated.endswith("\n") else translated + "\n")
    try:
        shown = out_path.relative_to(root)
    except ValueError:
        shown = out_path
    print(f"Wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
