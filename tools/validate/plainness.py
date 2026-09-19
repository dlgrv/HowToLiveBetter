#!/usr/bin/env python3
"""Plainness pass (plan addendum, user standard 2026-09-19): "understandable
to a 5-year-old" — operationalized as WARN-only deterministic linting of the
plain-terms field (Простыми словами / In plain terms / 说人话).

Philosophy:
  - The standard applies where the book PROMISES simplicity: the plain-terms
    field. Эффект/Notes keep technical register on purpose.
  - Deterministic lint catches the mechanical side (sentence length, relative
    chains, unexplained abbreviations). The semantic side ("would a child get
    it?") is judge territory (tools/prompts/judge-plainness.md), validated
    before enabling via a new degradation recipe.

Checks (all WARN):
  long_sentence      > plain.max_sentence_words (default 25) in one sentence
  which_chain        >= 3 relative pronouns (который-/which) in one sentence
  unexplained_abbrev 2+ ALL-CAPS letter run not whitelisted and not explained
                     in parentheses right after first use
"""
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

RULES_DIR = os.path.join(REPO, "tools", "rules")

SENT_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+")
WORD_RE = re.compile(r"[\w}-]+", re.UNICODE)
WHICH_RE = {
    "ru": re.compile(r"\bкотор\S*", re.IGNORECASE),
    "en": re.compile(r"\bwhich\b|\bwho\b", re.IGNORECASE),
}
ABBREV_RE = re.compile(r"\b[A-ZА-ЯЁ]{2,}\b", re.UNICODE)
EXPLAIN_RE = re.compile(r"\(\s*[^)]{3,60}\s*\)")

# abbreviations every adult reader is expected to know / context-free
DEFAULT_OK = {
    "ru": {"РФ", "СНГ", "ВОЗ", "СМС", "ЛОР", "УЗИ", "МРТ", "КТ", "ЭКГ", "ЭЭГ",
           "ДНД", "ГИА", "ЕГЭ", "ДТП", "СИЗ", "ФАП", "ОМС"},
    "en": {"USA", "UK", "EU", "WHO", "SMS", "MRI", "CT", "ECG", "EEG", "DNA",
           "ER", "ICU", "AED", "OTC", "BP"},
}

# unit field that carries the plainness promise, per language
PLAIN_FIELD = {"ru": "Простыми словами", "en": "In plain terms", "cn": "说人话"}


def _pack(lang):
    path = os.path.join(RULES_DIR, f"{lang}.json")
    if os.path.isfile(path):
        return json.load(open(path, encoding="utf-8"))
    return {}


def plain_fields(body, pack):
    """Extract (unit_header, plain_field_text) pairs from a chapter body."""
    lang = pack.get("lang", "ru")
    field = PLAIN_FIELD.get(lang, "Простыми словами")
    out = []
    for block in re.split(r"\n(?=### )", body):
        m = re.search(rf"^- {re.escape(field)}:\s*(.+)$", block, re.MULTILINE)
        if m:
            header = "?"
            hm = re.match(r"#{2,4}\s*(.+)", block)
            if hm:
                header = hm.group(1).strip()
            out.append({"unit": header, "text": m.group(1).strip()})
    return out


def check_field(text, pack):
    """Return WARN list for one plain-terms field value."""
    lang = pack.get("lang", "ru")
    cfg = pack.get("plainness", {})
    max_words = cfg.get("max_sentence_words", 25)
    max_which = cfg.get("max_relative_clauses", 2)
    ok = set(DEFAULT_OK.get(lang, set())) | set(cfg.get("ok_abbrev", []))

    warns = []
    for sent in SENT_SPLIT_RE.split(text):
        words = WORD_RE.findall(sent)
        if len(words) > max_words:
            warns.append({"type": "long_sentence", "words": len(words),
                          "excerpt": " ".join(words[:12]) + "…"})
        which = WHICH_RE.get(lang)
        if which and len(which.findall(sent)) > max_which:
            warns.append({"type": "which_chain",
                          "count": len(which.findall(sent)),
                          "excerpt": sent[:80]})
    for m in ABBREV_RE.finditer(text):
        abbr = m.group(0)
        if abbr in ok:
            continue
        tail = text[m.end():m.end() + 70]
        if EXPLAIN_RE.match(tail.lstrip(" —-")):
            continue
        warns.append({"type": "unexplained_abbrev", "abbr": abbr})
    return warns


def check_chapter(body, pack):
    """WARN report per unit for one chapter body."""
    report = []
    for f in plain_fields(body, pack):
        warns = check_field(f["text"], pack)
        report.append({"unit": f["unit"], "warns": warns})
    return report


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Plainness lint (WARN-only)")
    ap.add_argument("chapter", help="chapter number, e.g. 16")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--book-dir", default=os.path.join(REPO, "book"))
    args = ap.parse_args()
    pack = _pack(args.lang)
    pack.setdefault("lang", args.lang)
    lang_dir = os.path.join(args.book_dir, args.lang)
    base = lang_dir if os.path.isdir(lang_dir) else args.book_dir
    files = [p for p in os.listdir(base)
             if p.startswith(f"{int(args.chapter)}-") and p.endswith(".md")]
    if not files:
        print(f"chapter {args.chapter}: not found", file=sys.stderr)
        return 2
    body = open(os.path.join(base, files[0]), encoding="utf-8").read()
    report = check_chapter(body, pack)
    n_warns = sum(len(r["warns"]) for r in report)
    flagged = [r for r in report if r["warns"]]
    print(f"units with plain field: {len(report)} | WARNs: {n_warns} "
          f"| flagged units: {len(flagged)}")
    for r in flagged[:10]:
        print(f"- {r['unit'][:60]}")
        for w in r["warns"][:4]:
            print(f"    {w['type']}: {w.get('excerpt') or w.get('abbr') or w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
