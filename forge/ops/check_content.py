#!/usr/bin/env python3
"""Content gates for the translated HowToLiveBetter repo.

Five gates, one runner:

1. CJK LEAKS      No untranslated Chinese prose in book/{en,ru}, docs/{en,ru}.
                  Legal CJK: 《book titles》, parenthetical glosses (… — …),
                  dash-gloss table style (ICP 备案 — ICP filing), source lines
                  (- Sources: / - Источники: / - 来源： keep CN citations by
                  convention, see TRANSLATION.md), cost-tag HTML comments
                  (index.html parses them), link targets, path-like link
                  labels, fenced/inline code.
2. FILENAMES      No CJK characters in file names under translated dirs
                  (book/en, book/ru, docs/en, docs/ru). CN originals in book/
                  and docs/ root are Chinese by definition.
3. PARITY         Each chapter NN exists once in book/ and each translated
                  tree; every NN is linked from each langs.json README; item
                  (###) counts match per chapter; each README links >=4 docs
                  long reads in its language.
4. STATS          Items / A-grade / primary-link counts recomputed from
                  book/*.md must appear in every langs.json README (badge sync).
5. README         Section-count sentence and in-progress markers are checked
                  for every langs.json README.

Exit codes: 0 = all gates pass, 1 = violations found.
"""

import glob
import json
import os
import re
import sys

from translate.lib.config import default_root, load_langs, translation_langs
from translate.lib.labels import field_labels, source_label

ROOT = default_root()
CJK = re.compile(r"[\u4e00-\u9fff]")
NN = re.compile(r"^(\d{2})-")
SRC_BULLET = re.compile(r"^\s*-\s*[\u4e00-\u9fff]")
FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
PATHLIKE_LINK = re.compile(r"\[[^\]\n]*[/\\][^\]\n]*\.(?:md|png|html)\]\([^)]*\)")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
BOOK_TITLE = re.compile(r"《[^》]*》")
GLOSS_PAREN = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fff/0-9]{0,20}\s*[（(][^()（）]*[）)]")
TERM_THEN_TITLE = re.compile(r"[\"«“][^\"»”]*[\"»”]\s*《")
TITLE_IDIOM = re.compile(
    r"[\u4e00-\u9fff][\u4e00-\u9fff0-9]{0,12}\s*《[^》]*》\s*[\u4e00-\u9fff][\u4e00-\u9fff0-9]{0,12}"
)
FW_PAREN = re.compile(r"（[^（）]*）")
DOC_NUM = re.compile(
    r"[\u4e00-\u9fff][\u4e00-\u9fff0-9]{0,20}\s*[〔[][^〕\]]{0,20}[〕\]]\s*[\u4e00-\u9fff0-9]{0,10}\s*号?"
    r"|[\u4e00-\u9fff][\u4e00-\u9fff]{1,15}\s*[（(]\d{4}[）)]\s*[\u4e00-\u9fff]{1,15}\s*\d{1,5}\s*号"
    r"|[\u4e00-\u9fff][\u4e00-\u9fff]{1,15}\s*\d{1,5}\s*号"
)
DASH_GLOSS = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fff0-9·／/]{0,20}\s*—\s*[A-Za-zА-Яа-яЁё]")
EQ_GLOSS = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fff/]{0,15}\s*=\s*\S")
QUOTED_TERM = re.compile(r"[\"«“][\u4e00-\u9fff][\u4e00-\u9fff0-9·—－\s（）():：]{0,60}[\"»”]")
PAREN = re.compile(r"[（(][^（）()]*[）)]")


FIELD_LANGS = tuple(translation_langs(ROOT))


def _src_line_pattern():
    names = set()
    for lang in ("cn", *FIELD_LANGS):
        try:
            names.add(source_label(lang, root=ROOT))
        except (FileNotFoundError, KeyError):
            continue
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"^\s*(?:-\s*)?(?:{alt})\s*[:：]")


SRC_LINE = _src_line_pattern()


def translated_dirs():
    codes = translation_langs(ROOT)
    dirs = [f"book/{c}" for c in codes]
    for c in codes:
        d = f"docs/{c}"
        if os.path.isdir(os.path.join(ROOT, d)):
            dirs.append(d)
    return dirs


def gate_parity(issues):
    codes = translation_langs(ROOT)
    cn = chapter_nns("book")
    expected = sorted(set(cn))
    marker = os.path.join(ROOT, "docs", ".retranslate-pending")
    pending = set()
    if os.path.exists(marker):
        pending = {
            ln.strip()
            for ln in open(marker, encoding="utf-8")
            if ln.strip() and not ln.startswith("#")
        }
    per_lang = {"book": cn}
    for c in codes:
        per_lang[f"book/{c}"] = chapter_nns(f"book/{c}")
    for label, got in per_lang.items():
        dup = {x for x in got if got.count(x) > 1}
        if dup:
            issues.append(f"[parity] {label}: duplicate chapters {sorted(dup)}")
        miss = [x for x in expected if x not in got]
        extra = [x for x in got if x not in expected]
        if miss:
            if label.startswith("book/"):
                soft = [x for x in miss if x in pending]
                hard = [x for x in miss if x not in pending]
                if soft:
                    print(f"[parity] {label}: missing chapters (retranslate pending): {soft}")
                if hard:
                    issues.append(f"[parity] {label}: missing chapters {hard}")
            else:
                issues.append(f"[parity] {label}: missing chapters {miss}")
        if extra:
            issues.append(f"[parity] {label}: unexpected chapters {extra}")
    for nn in expected:
        counts = {}
        for label in per_lang:
            files = glob.glob(os.path.join(ROOT, label, f"{nn}-*.md"))
            if len(files) == 1:
                counts[label] = len(
                    re.findall(r"^### ", open(files[0], encoding="utf-8").read(), re.MULTILINE)
                )
        if len(set(counts.values())) > 1:
            if nn in pending:
                print(f"[parity] ch.{nn} item counts differ (retranslate pending): {counts}")
            elif "book/ru" in counts and counts.get("book") == counts.get("book/ru"):
                print(f"[parity] ch.{nn} item counts differ (non-RU trailing CN): {counts}")
            else:
                issues.append(f"[parity] ch.{nn} item counts differ: {counts}")
    readme_expect = {}
    docs_expect = {}
    for entry in load_langs(ROOT):
        readme = entry["readme"]
        readme_expect[readme] = entry["contentRoot"].rstrip("/") + "/"
        if entry["contentRoot"] == "book":
            docs_expect[readme] = "docs/research/"
        else:
            docs_expect[readme] = f"docs/research/{entry['code']}/"
    for rf, prefix in readme_expect.items():
        text = open(os.path.join(ROOT, rf), encoding="utf-8").read()
        for nn in expected:
            if f"{prefix}{nn}-" not in text:
                if nn in pending:
                    print(f"[parity] {rf}: chapter {nn} not linked (retranslate pending)")
                else:
                    issues.append(f"[parity] {rf}: chapter {nn} not linked")
        docs_prefix = docs_expect[rf]
        n_docs = len(re.findall(rf"\]\({re.escape(docs_prefix)}[^/)]*\.md", text))
        if n_docs < 4:
            issues.append(f"[parity] {rf}: only {n_docs} long-read links ({docs_prefix}…), need 4")


def strip_legal_cjk(text):
    """Remove everything where CJK is legal; residue CJK = leak."""
    text = FENCE.sub("", text)
    text = HTML_COMMENT.sub("", text)
    text = INLINE_CODE.sub("", text)
    text = PATHLIKE_LINK.sub(" ", text)
    text = LINK_TARGET.sub("]()", text)
    text = TERM_THEN_TITLE.sub(" 《", text)
    text = TITLE_IDIOM.sub(" 《》 ", text)
    text = BOOK_TITLE.sub("《》", text)
    text = GLOSS_PAREN.sub(" ", text)
    text = FW_PAREN.sub(" ", text)
    text = DOC_NUM.sub(" № ", text)
    text = DASH_GLOSS.sub(" — ", text)
    text = EQ_GLOSS.sub("= ", text)
    text = QUOTED_TERM.sub('""', text)
    return PAREN.sub("()", text)


def gate_cjk_leaks(issues):
    for d in translated_dirs():
        for path in sorted(glob.glob(os.path.join(ROOT, d, "*.md"))):
            rel = os.path.relpath(path, ROOT)
            for ln, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
                if SRC_LINE.match(line) or SRC_BULLET.match(line):
                    continue
                residue = strip_legal_cjk(line)
                m = CJK.search(residue)
                if m:
                    ctx = residue.strip()[:80]
                    issues.append(f"[cjk-leak] {rel}:{ln} '{m.group(0)}' :: {ctx}")


def _empty_field_pattern():
    """'- Field:' with nothing after it, for every label in the language packs."""
    names = set()
    for lang in FIELD_LANGS:
        try:
            names.update(field_labels(lang, root=ROOT))
            names.add(source_label(lang, root=ROOT))
        except (FileNotFoundError, KeyError):
            continue
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"^- (?:{alt}):\s*$")


def gate_empty_fields(issues):
    """Field labels (Стоимость/Эффект/...) must carry their text on the same line.
    The site parser matches '- Field: value' on one line; a bare '- Field:' line
    renders an empty card in the sidebar/entry view."""
    pat = _empty_field_pattern()
    for d in translated_dirs():
        for path in sorted(glob.glob(os.path.join(ROOT, d, "*.md"))):
            rel = os.path.relpath(path, ROOT)
            for ln, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
                if pat.match(line):
                    issues.append(
                        f"[empty-field] {rel}:{ln} '{line.strip()}' "
                        f"(field text must be on the same line)"
                    )


def gate_filenames(issues):
    for d in translated_dirs():
        for name in sorted(os.listdir(os.path.join(ROOT, d))):
            if CJK.search(name):
                issues.append(f"[cjk-filename] {d}/{name}")


def chapter_nns(subdir):
    nns = []
    for name in sorted(os.listdir(os.path.join(ROOT, subdir))):
        m = NN.match(name)
        if name.endswith(".md") and m:
            nns.append(m.group(1))
    return nns


def gate_stats(issues):
    items = a_grade = links = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "book", "[0-9][0-9]-*.md"))):
        s = open(path, encoding="utf-8").read()
        items += len(re.findall(r"^### ", s, re.MULTILINE))
        a_grade += len(re.findall(r"^\s*-\s*证据等级：A", s, re.MULTILINE))
        for line in s.splitlines():
            if line.startswith(("- 来源：", "- 来源:", "- 备注：", "- 备注:")):
                links += len(re.findall(r"https?://", line))
    computed = {"items": items, "A-grade": a_grade, "links": links}
    marker = os.path.join(ROOT, "docs", ".retranslate-pending")
    retranslate_pending = os.path.exists(marker) and any(
        ln.strip() and not ln.startswith("#") for ln in open(marker, encoding="utf-8")
    )
    for rf in (entry["readme"] for entry in load_langs(ROOT)):
        text = open(os.path.join(ROOT, rf), encoding="utf-8").read()
        for label, val in computed.items():
            if str(val) not in text:
                if retranslate_pending:
                    print(f"[stats] {rf}: {label}={val} not in badges (retranslate pending)")
                else:
                    issues.append(
                        f"[stats] {rf}: {label}={val} from book/*.md not found "
                        f"(badge out of sync? run sync-stats / update badges)"
                    )


SECTION_COUNT = {
    "README.md": re.compile(r"split into (\d+) section files"),
    "README.es.md": re.compile(r"split into (\d+) section files"),
    "README.ru.md": re.compile(r"разбит на (\d+) файл(?:а|ов)?"),
    "README.zh.md": re.compile(r"拆成 (\d+) 个文件"),
}

IN_PROGRESS_MARKERS = (
    "traducción en curso",
    "translation in progress",
    "перевод в процессе",
    "翻译进行中",
)


def section_count_issues(readme_name, text, n_chapters):
    pat = SECTION_COUNT.get(readme_name)
    if pat is None:
        return []
    m = pat.search(text)
    if not m:
        return [f"[readme] {readme_name}: section-count sentence missing"]
    stated = int(m.group(1))
    if stated != n_chapters:
        return [
            f"[readme] {readme_name}: says {stated} section files, found {n_chapters} chapter files"
        ]
    return []


def stale_status_issues(text, all_complete):
    if not all_complete:
        return []
    return [
        f"[readme] stale in-progress marker {marker!r} but every chapter is complete"
        for marker in IN_PROGRESS_MARKERS
        if marker in text
    ]


def _all_complete(lang_code):
    path = os.path.join(ROOT, "translations.json")
    data = json.load(open(path, encoding="utf-8"))
    block = data.get(lang_code)
    if not isinstance(block, dict):
        return None  # zh and unknown langs: skip
    chapters = [v for v in block.values() if isinstance(v, dict) and "status" in v]
    if not chapters:
        return None
    return all(v["status"] == "complete" for v in chapters)


def gate_readme_facts(issues):
    for entry in load_langs(ROOT):
        readme = entry["readme"]
        text = open(os.path.join(ROOT, readme), encoding="utf-8").read()
        n = len(chapter_nns(entry["contentRoot"]))
        issues.extend(section_count_issues(readme, text, n))
        complete = _all_complete(entry["code"])
        if complete is None:
            continue
        for item in stale_status_issues(text, complete):
            issues.append(f"{item} ({readme})")


def main():
    issues = []
    gate_filenames(issues)
    gate_cjk_leaks(issues)
    gate_empty_fields(issues)
    gate_parity(issues)
    gate_stats(issues)
    gate_readme_facts(issues)
    print("content gates: filenames, cjk-leaks, empty-fields, parity, stats, readme")
    if issues:
        print(f"VIOLATIONS: {len(issues)}")
        for i in issues:
            print(" ", i)
        return 1
    print("all gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
