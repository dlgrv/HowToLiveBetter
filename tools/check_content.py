#!/usr/bin/env python3
"""Content gates for the translated HowToLiveBetter repo.

Four gates, one runner:

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
3. PARITY         Chapters NN 01..32 exist exactly once in book/, book/en,
                  book/ru; every NN is linked from all three READMEs; item
                  (###) count matches across the three languages per chapter;
                  each README links >=4 docs long reads in its language.
4. STATS          Items / A-grade / primary-link counts recomputed from
                  book/*.md must appear in all three READMEs (badge sync).

Exit codes: 0 = all gates pass, 1 = violations found.
"""
import glob
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[\u4e00-\u9fff]')
NN = re.compile(r'^(\d{2})-')
SRC_LINE = re.compile(r'^\s*(?:-\s*)?(?:Sources?|Fuentes|Источник(?:и)?|来源)\s*[:：]')
# RU docs keep the CN citation bullet format (CJK author first) — see TRANSLATION.md
SRC_BULLET = re.compile(r'^\s*-\s*[\u4e00-\u9fff]')
FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
PATHLIKE_LINK = re.compile(r"\[[^\]\n]*[/\\][^\]\n]*\.(?:md|png|html)\]\([^)]*\)")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
BOOK_TITLE = re.compile(r"《[^》]*》")
# ordered legal-CJK rules (applied before the generic PAREN)
GLOSS_PAREN = re.compile(  # 面子 (mianzi — social face), 民法典 (), 彩礼 ()
    r"[\u4e00-\u9fff][\u4e00-\u9fff/0-9]{0,20}\s*[（(][^()（）]*[）)]")
TERM_THEN_TITLE = re.compile(  # «термин»《Title》— quoted term directly before a title
    r"[\"«“][^\"»”]*[\"»”]\s*《")
TITLE_IDIOM = re.compile(  # 关于适用《X》的解释 — CN citation names wrapping a 《title》
    r"[\u4e00-\u9fff][\u4e00-\u9fff0-9]{0,12}\s*《[^》]*》\s*[\u4e00-\u9fff][\u4e00-\u9fff0-9]{0,12}")
FW_PAREN = re.compile(r"（[^（）]*）")
DOC_NUM = re.compile(  # 国食药监办〔2010〕432 号, 最高法知民终 51 号 — official IDs
    r"[\u4e00-\u9fff][\u4e00-\u9fff0-9]{0,20}\s*[〔[][^〕\]]{0,20}[〕\]]\s*[\u4e00-\u9fff0-9]{0,10}\s*号?"
    r"|[\u4e00-\u9fff][\u4e00-\u9fff]{1,15}\s*[（(]\d{4}[）)]\s*[\u4e00-\u9fff]{1,15}\s*\d{1,5}\s*号"
    r"|[\u4e00-\u9fff][\u4e00-\u9fff]{1,15}\s*\d{1,5}\s*号")
DASH_GLOSS = re.compile(  # 网络直播营销 — livestream marketing / — маркетинг
    r"[\u4e00-\u9fff][\u4e00-\u9fff0-9·／/]{0,20}\s*—\s*[A-Za-zА-Яа-яЁё]")
EQ_GLOSS = re.compile(  # 出国/出境 = выезд из КНР
    r"[\u4e00-\u9fff][\u4e00-\u9fff/]{0,15}\s*=\s*\S")
QUOTED_TERM = re.compile(  # "定金", «全国基础版…建议清单» — referenced terms/titles in quotes
    r"[\"«“][\u4e00-\u9fff][\u4e00-\u9fff0-9·—－\s（）():：]{0,60}[\"»”]")
PAREN = re.compile(r"[（(][^（）()]*[）)]")


def load_lang_codes():
    """Translated content codes from langs.json (exclude zh mirror at book/)."""
    path = os.path.join(ROOT, "tools", "langs.json")
    if not os.path.isfile(path):
        return ["en", "ru"]
    data = json.load(open(path, encoding="utf-8"))
    out = []
    for L in data.get("languages", []):
        root = L.get("contentRoot", "")
        if root.startswith("book/") and root != "book":
            out.append(L["code"])
    return out or ["en", "ru"]


def translated_dirs():
    codes = load_lang_codes()
    dirs = [f"book/{c}" for c in codes]
    for c in codes:
        d = f"docs/{c}"
        if os.path.isdir(os.path.join(ROOT, d)):
            dirs.append(d)
    return dirs


def gate_parity(issues):
    codes = load_lang_codes()
    cn = chapter_nns("book")
    expected = [f"{n:02d}" for n in range(1, 34)]
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
            issues.append(f"[parity] {label}: missing chapters {miss}")
        if extra:
            issues.append(f"[parity] {label}: unexpected chapters {extra}")
    for nn in expected:
        counts = {}
        for label in per_lang:
            files = glob.glob(os.path.join(ROOT, label, f"{nn}-*.md"))
            if len(files) == 1:
                counts[label] = len(
                    re.findall(r"^### ", open(files[0], encoding="utf-8").read(), re.M))
        if len(set(counts.values())) > 1:
            issues.append(f"[parity] ch.{nn} item counts differ: {counts}")
    # EN-primary: README.md → book/en/; ZH mirror → book/; RU → book/ru/
    readme_expect = {"README.md": "book/en/", "README.ru.md": "book/ru/", "README.zh.md": "book/"}
    docs_expect = {"README.md": "docs/en/", "README.ru.md": "docs/ru/", "README.zh.md": "docs/"}
    for rf, prefix in readme_expect.items():
        text = open(os.path.join(ROOT, rf), encoding="utf-8").read()
        for nn in expected:
            if f"{prefix}{nn}-" not in text:
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
    text = PAREN.sub("()", text)
    return text


def gate_cjk_leaks(issues):
    for d in translated_dirs():
        for path in sorted(glob.glob(os.path.join(ROOT, d, "*.md"))):
            rel = os.path.relpath(path, ROOT)
            for ln, line in enumerate(
                    open(path, encoding="utf-8").read().splitlines(), 1):
                if SRC_LINE.match(line) or SRC_BULLET.match(line):
                    continue
                residue = strip_legal_cjk(line)
                m = CJK.search(residue)
                if m:
                    ctx = residue.strip()[:80]
                    issues.append(f"[cjk-leak] {rel}:{ln} '{m.group(0)}' :: {ctx}")


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
        items += len(re.findall(r"^### ", s, re.M))
        a_grade += len(re.findall(r"^\s*-\s*证据等级：A", s, re.M))
        for line in s.splitlines():
            if line.startswith(("- 来源：", "- 来源:", "- 备注：", "- 备注:")):
                links += len(re.findall(r"https?://", line))
    computed = {"items": items, "A-grade": a_grade, "links": links}
    for rf in ("README.md", "README.ru.md", "README.zh.md"):
        text = open(os.path.join(ROOT, rf), encoding="utf-8").read()
        for label, val in computed.items():
            if str(val) not in text:
                issues.append(
                    f"[stats] {rf}: {label}={val} from book/*.md not found "
                    f"(badge out of sync? run sync-stats / update badges)")


def main():
    issues = []
    gate_filenames(issues)
    gate_cjk_leaks(issues)
    gate_parity(issues)
    gate_stats(issues)
    print(f"content gates: filenames, cjk-leaks, parity, stats")
    if issues:
        print(f"VIOLATIONS: {len(issues)}")
        for i in issues:
            print(" ", i)
        return 1
    print("all gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
