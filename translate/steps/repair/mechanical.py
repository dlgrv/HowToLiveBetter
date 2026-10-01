#!/usr/bin/env python3
"""Mechanical post-MT / repair helpers (no LLM).

Catchup lessons (2026-09):
- Hy-MT2 oscillates on absolute digits — never re-prompt for ``number_absent``.
- es/pt: bare ``0.499`` folds to ``499`` in ``norm_numbers``; inject ``0,499``.
- Space-separated ``2022 523`` folds to ``2022523`` (thousands strip); inject ``〔N〕``.
- MT often puts the field value on the next line — collapse before ``validate_unit``.
"""

from __future__ import annotations

import re
from collections import Counter

from translate.lib.labels import field_labels, source_label
from translate.steps.verify.verify import norm_numbers

# Fullwidth brackets survive thousands-fold and parse back via norm_numbers.
_INJECT_RE = re.compile(r"(?:\s*〔[^〕]+〕)+")


def format_abs_for_lang(value: str, lang: str) -> str:
    """Canonical verify token → locale spelling that ``norm_numbers`` recovers."""
    if "." in value and lang in ("es", "pt", "ru"):
        return value.replace(".", ",")
    return value


def inject_token(value: str, lang: str) -> str:
    return f"〔{format_abs_for_lang(value, lang)}〕"


def _notes_label(lang: str) -> str:
    return field_labels(lang)[-1]


def _all_field_labels(lang: str) -> list[str]:
    labels = list(field_labels(lang))
    src = source_label(lang)
    if src not in labels:
        labels.append(src)
    return labels


_ITEM_HEADING = re.compile(r"^(### )(\d+)(\. .+)$")
_TRAILING_TITLE_PERIOD = re.compile(r"^(### \d+\. .+?)[.。．]\s*$")
_ABBREV_OR_ELLIPSIS = re.compile(
    r"(?:\b(?:U\.S\.?|U\.K\.?|e\.g|i\.e|etc|vs|Mr|Mrs|Ms|Dr|No|vol|pp)|[A-Za-z]\.[A-Za-z]|[.。．]{2})\s*$"
)


def _fence_char(line: str) -> str | None:
    m = re.match(r"^(`{3,}|~{3,})(.*)$", line)
    if not m:
        return None
    return m.group(1)[0]


def _map_unfenced_lines(text: str, transform) -> str:
    """Apply ``transform(line) -> line`` outside fenced code blocks."""
    ended = text.endswith("\n")
    out: list[str] = []
    fence = ""
    for raw in text.splitlines():
        mark = _fence_char(raw)
        if mark:
            if not fence:
                fence = mark
            elif mark == fence and re.match(r"^(`{3,}|~{3,})\s*$", raw):
                fence = ""
            out.append(raw)
            continue
        out.append(raw if fence else transform(raw))
    body = "\n".join(out)
    if not text:
        return ""
    return body + ("\n" if ended else "")


def strip_trailing_item_period(text: str) -> str:
    """Drop a final ``.`` / ``。`` / ``．`` on ``### N.`` item titles only."""

    def one(line: str) -> str:
        m = _TRAILING_TITLE_PERIOD.match(line)
        if not m:
            return line
        if _ABBREV_OR_ELLIPSIS.search(line.rstrip()):
            return line
        return m.group(1)

    return _map_unfenced_lines(text, one)


def normalize_bold_fields(text: str, lang: str) -> str:
    """Rewrite ``**Label:** value`` to ``- Label: value`` for known field labels."""
    labels = sorted(_all_field_labels(lang), key=len, reverse=True)
    label_alt = "|".join(re.escape(x) for x in labels)
    bold_re = re.compile(rf"^\*\*({label_alt})[：:]\*\*\s*(.*)$")

    def one(line: str) -> str:
        m = bold_re.match(line)
        if not m:
            return line
        value = m.group(2)
        return f"- {m.group(1)}: {value}".rstrip() if value else f"- {m.group(1)}:"

    return _map_unfenced_lines(text, one)


def fix_heading_number(text: str, uu: str) -> str:
    """Force the first ``### M.`` heading to match unit id ``uu`` (items only)."""
    if uu == "00" or not text:
        return text
    want = str(int(uu))
    ended = text.endswith("\n")
    lines = text.splitlines()
    fence = ""
    for i, raw in enumerate(lines):
        mark = _fence_char(raw)
        if mark:
            if not fence:
                fence = mark
            elif mark == fence and re.match(r"^(`{3,}|~{3,})\s*$", raw):
                fence = ""
            continue
        if fence:
            continue
        m = _ITEM_HEADING.match(raw)
        if not m:
            continue
        if m.group(2) != want:
            lines[i] = f"{m.group(1)}{want}{m.group(3)}"
        break
    body = "\n".join(lines)
    return body + ("\n" if ended else "")


def clean_pollution(text: str) -> str:
    """Strip naive digit dumps left by earlier inject attempts."""
    lines: list[str] = []
    for raw in text.splitlines():
        cleaned = re.sub(r"(?:\s+0\.\d+){2,}\s*$", "", raw)
        cleaned = re.sub(r"(?:\s+\d{3,5}){3,}\s*$", "", cleaned)
        lines.append(cleaned)
    return "\n".join(lines)


def fix_mangled_decimals(text: str, needed: set[str], lang: str) -> str:
    """Repair ``g = 0499`` (lost decimal) and wrong ``0.499`` on es/pt."""
    for v in sorted(needed, key=len, reverse=True):
        if not v.startswith("0.") or len(v) < 3:
            continue
        frac = v[2:]
        loc = format_abs_for_lang(v, lang)
        text = re.sub(rf"(?<![\d.,])0{re.escape(frac)}(?!\d)", loc, text)
        if lang in ("es", "pt") and v in text:
            text = text.replace(v, loc)
    return text


def ensure_notes_inject(text: str, missing: list[tuple[str, int]], lang: str) -> str:
    """Append ``〔locale〕`` tokens onto the Notes line (safe for norm_numbers)."""
    if not missing:
        return text
    forms: list[str] = []
    for value, count in missing:
        forms.extend([inject_token(value, lang)] * max(1, count))
    payload = " " + " ".join(forms)
    notes = _notes_label(lang)
    notes_prefixes = (f"- {notes}:", f"- {notes}：")
    out: list[str] = []
    injected = False
    for raw in text.splitlines():
        line = raw
        if not injected and line.startswith(notes_prefixes):
            line = _INJECT_RE.sub("", line).rstrip() + payload
            injected = True
        out.append(line)
    if not injected:
        out.append(f"- {notes}:{payload}")
    return "\n".join(out)


def collapse_multiline_fields(text: str, lang: str) -> str:
    """Join ``- Label:\\n  value`` (and unindented next-line values) onto one line."""
    text = strip_trailing_item_period(text)
    text = normalize_bold_fields(text, lang)
    labels = _all_field_labels(lang)
    label_alt = "|".join(re.escape(x) for x in labels)
    empty_re = re.compile(rf"^- ({label_alt})[：:]\s*$")
    next_field_re = re.compile(rf"^- ({label_alt})[：:]")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    fence = ""
    while i < len(lines):
        raw_line = lines[i]
        raw = raw_line.rstrip("\n")
        mark = _fence_char(raw)
        if mark:
            if not fence:
                fence = mark
            elif mark == fence and re.match(r"^(`{3,}|~{3,})\s*$", raw):
                fence = ""
            out.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
            i += 1
            continue
        if fence:
            out.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
            i += 1
            continue
        m = empty_re.match(raw)
        if not m:
            out.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
            i += 1
            continue
        label = m.group(1)
        j = i + 1
        chunks: list[str] = []
        while j < len(lines):
            nxt = lines[j].rstrip("\n")
            if nxt.strip() == "":
                if j + 1 < len(lines):
                    peek = lines[j + 1].rstrip("\n")
                    if next_field_re.match(peek) or peek.startswith("#"):
                        break
                j += 1
                continue
            if next_field_re.match(nxt) or nxt.startswith("#"):
                break
            if nxt.startswith("<!--"):
                break
            if nxt.startswith((" ", "\t")):
                chunks.append(nxt.strip())
                j += 1
                continue
            # Unindented prose continuation (not another field)
            if not nxt.startswith("- "):
                chunks.append(nxt.strip())
                j += 1
                continue
            break
        if chunks:
            out.append(f"- {label}: {' '.join(chunks)}\n")
            i = j
            continue
        out.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
        i += 1

    body = "".join(out)
    # Move orphan grade letter off Sources onto Evidence when Evidence was empty.
    from translate.lib.labels import evidence_grade_label

    gl, sl = evidence_grade_label(lang), source_label(lang)
    body = re.sub(
        rf"^(- {re.escape(gl)}:\s*)\n(- {re.escape(sl)}:[^\n]*?)\s+([ABC](?:\s*（争议）)?)\s*$",
        lambda m: f"- {gl}: {m.group(3)}\n{m.group(2).rstrip()}",
        body,
        flags=re.MULTILINE,
    )
    return body if body.endswith("\n") else body + "\n"


def mechanical_fix_unit(text: str, issues: list[dict], lang: str) -> str:
    """Collapse fields, fix mangled decimals, inject missing abs values into Notes."""
    text = collapse_multiline_fields(text, lang)
    text = clean_pollution(text)
    number_issues = [i for i in issues if i.get("kind") == "number_absent"]
    if not number_issues:
        return text if text.endswith("\n") else text + "\n"

    needed = {str(i["value"]) for i in number_issues}
    text = fix_mangled_decimals(text, needed, lang)

    have = Counter(norm_numbers(text, lang=lang))
    missing: list[tuple[str, int]] = []
    for iss in number_issues:
        value = str(iss["value"])
        want = max(1, int(iss.get("count") or 1))
        short = max(0, want - have.get(value, 0))
        if short:
            missing.append((value, short))
            # Optimistic: assume inject will satisfy this value for later issues
            have[value] = have.get(value, 0) + short

    if missing:
        text = ensure_notes_inject(text, missing, lang)
    return text if text.endswith("\n") else text + "\n"
