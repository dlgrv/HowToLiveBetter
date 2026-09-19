#!/usr/bin/env python3
"""Integrity gate for one translated chapter (RU or EN) against the Chinese original.

Usage:
  python3 tools/verify.py <NN> --lang ru          # book/ru/NN-*.md
  python3 tools/verify.py <NN> --lang en          # book/en/NN-*.md
  python3 tools/verify.py <NN> --lang ru --file /tmp/candidate.md

Checks (fail = exit 1, warn = printed only):
  1. heading (### N.) count == original
  2. cost-tag comment count == original
  3. source lines: count == original AND content after the field label is
     byte-identical (label `：` vs `:` stripped first)
  4. field-label counts (成本/说人话/收益/证据等级/备注 ↔ Стоимость…/Cost…)
  5. numbers: every numeric token of the original body (sources/tags excluded)
     must survive in the translation. 万 is expanded (2 万 → 20000) before
     comparison; thousand separators (20,000 / 20 000 / 20 000 NBSP) and RU
     decimal commas (97,2) are normalized. Numbers ADDED by the translation
     (localization inserts like "112/103") are listed as warnings, not fails.
  6. CJK / fullwidth punctuation outside allowed zones (sources, tag comments,
     first 4 status lines, markdown link targets, parenthetical glosses)
  7. RU only: banned epidemiology calques (когорта/экспозиция/квартиль/…)
     — >1 occurrence per file fails, 1 occurrence must be a first-use gloss.

On success writes tools/.status/<NN>-<lang>.ok (mtime-stamped) for status.py.
"""
import argparse, glob, json, os, re, sys, time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LABELS = {
    "cn": ["成本", "说人话", "收益", "证据等级", "备注"],
    "ru": ["Стоимость", "Простыми словами", "Эффект", "Уровень доказательности", "Примечания"],
    "en": ["Cost", "In plain terms", "Benefit", "Evidence grade", "Notes"],
}
SRC_LABEL = {"cn": "- 来源：", "ru": "- Источники:", "en": "- Sources:"}
CJK = re.compile(r"[\u4e00-\u9fff]")
FULLWIDTH = re.compile(r"[，。：；！？「」『』（）]")
NUM = re.compile(r"\d+(?:\.\d+)?")
BANNED_RU = ["когорт", "экспозици", "квартил", "квинтил", "конфаунд", "популяц"]


def _lang_pack(lang):
    """Load tools/rules/<lang>.json (labels/banned_calques); None if absent/empty.

    Fallback contract (plan Task 10b): while the language pack is not yet
    filled, verify.py keeps its built-in LABELS/BANNED_RU — zero behavior
    change until Task 10b lands in full.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules", f"{lang}.json")
    try:
        pack = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not pack or (not pack.get("labels") and not pack.get("banned_calques")):
        return None
    return pack


WORD_VALUES = [
    # compound first
    (r"двадцать[\s-]?четыре", "24"), (r"twenty-four", "24"),
    (r"круглосуточн\w*", "24"), (r"(a?round|around)-the-clock", "24"),
    # months (stems) — «11 月 1 日» legitimately becomes «1 ноября»
    (r"январ\w*", "1"), (r"феврал\w*", "2"), (r"март\w*", "3"), (r"апрел\w*", "4"),
    (r"мая", "5"), (r"июн\w*", "6"), (r"июл\w*", "7"), (r"август\w*", "8"),
    (r"сентябр\w*", "9"), (r"октябр\w*", "10"), (r"ноябр\w*", "11"), (r"декабр\w*", "12"),
    (r"january", "1"), (r"february", "2"), (r"march", "3"), (r"april", "4"),
    (r"june", "6"), (r"july", "7"), (r"august", "8"), (r"september", "9"),
    (r"october", "10"), (r"november", "11"), (r"december", "12"),
    # spelled-out numerals the translations legitimately use in prose
    (r"одиннадцат\w*", "11"), (r"двенадцат\w*", "12"),
    (r"один(?!\w)", "1"), (r"одна(?!\w)", "1"), (r"одного", "1"), (r"одной", "1"),
    (r"одну", "1"), (r"два(?!\w)", "2"), (r"две(?!\w)", "2"), (r"двух", "2"),
    (r"двум", "2"), (r"обеих", "2"), (r"обоих", "2"), (r"трёх", "3"), (r"трем", "3"),
    (r"четырёх", "4"), (r"четыре(?!\w)", "4"), (r"пяти", "5"), (r"пять(?!\w)", "5"),
    (r"шести", "6"), (r"семи", "7"), (r"восьми", "8"), (r"девяти", "9"),
    (r"полтора", "1.5"),
    (r"нулю|ноль", "0"),
    (r"\bzero\b", "0"),
    (r"\bone\b", "1"), (r"\btwo\b", "2"), (r"\bthree\b", "3"), (r"\bfour\b", "4"),
    (r"\bfive\b", "5"), (r"\bsix\b", "6"), (r"\bseven\b", "7"), (r"\beight\b", "8"),
    (r"\bnine\b", "9"), (r"\bten\b", "10"), (r"\beleven\b", "11"), (r"\btwelve\b", "12"),
]
WORD_RX = re.compile("|".join(f"(?P<w{i}>{p})" for i, (p, _) in enumerate(WORD_VALUES)),
                     flags=re.I)


def fold_words(text):
    """Replace spelled-out numerals / month names with their digit values so the
    value-space comparison treats «1 ноября» == «11 月 1 日» == «November 1»."""
    def rep(m):
        idx = next(i for i in range(len(WORD_VALUES)) if m.group(f"w{i}") is not None)
        return f" {WORD_VALUES[idx][1]} "
    return WORD_RX.sub(rep, text)


def norm_numbers(text, ru=False):
    """Multiset of ABSOLUTE numeric values: scale-words (万/亿/тыс./млн/млрд/
    thousand/million/billion) are folded into the value, so «65.4 万» == «654
    тыс.» == «654,000». Comma handling is language-dependent: RU uses the comma
    as the decimal separator and a space as the thousands separator; CN/EN use
    the dot as decimal and the comma as thousands separator."""
    text = text.replace("\u00a0", " ")
    if ru:
        # «4,257 млрд» — a comma directly before a scale word is DECIMAL
        text = re.sub(r"(\d),(\d{3})(?=\s*(?:тыс|млн|млрд|трлн|триллион|миллион|"
                      r"миллиард|thousand|million|billion|trillion)\b)",
                      r"\1.\2", text, flags=re.I)
        # EN-style comma thousands may survive in RU prose («25,871 человек»),
        # but a comma right after a lone 0 is decimal («0,001»)
        text = re.sub(r"(?<![0.,]),(?=\d{3}(?!\d))", "", text)
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)          # RU decimal comma
        text = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", text)  # RU space thousands
    else:
        text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)  # EN/CN comma thousands
    text = fold_words(text)
    # distributive scale: «от 81 до 138 тыс.» == «8.1 万 到 13.8 万» — the scale
    # word applies to BOTH endpoints in Russian prose; duplicate it backwards.
    text = re.sub(r"(\d+(?:\.\d+)?)((?:\s+(?:до|and|to)\s*|\s*[–—-]\s*)\d+(?:\.\d+)?)"
                  r"\s*(тыс\.?|млн\.?|млрд\.?|трлн\.?|thousand|million|billion)",
                  lambda m: f"{m.group(1)} {m.group(3)}{m.group(2)} {m.group(3)}",
                  text, flags=re.I)
    scale = [("тысяч", 1e3), ("тыс", 1e3), ("миллион", 1e6), ("млн", 1e6),
             ("миллиард", 1e9), ("млрд", 1e9), ("трлн", 1e12), ("триллион", 1e12),
             ("trillion", 1e12), ("万亿", 1e12), ("万", 1e4), ("亿", 1e8), ("千", 1e3),
             ("thousand", 1e3), ("million", 1e6), ("billion", 1e9)]
    out = []
    for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*[多余]?\s*(万亿|万|亿|千)\s*[多余]?|"
            r"(\d+(?:\.\d+)?)\s*(万亿|万|亿|千|тысяч\w*|тыс\.?|миллион\w*|млн|"
            r"миллиард\w*|млрд|трлн|триллион\w*|trillion|thousand|million|billion)?",
            text, flags=re.I):
        g_num, g_scale = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        v = float(g_num)
        if g_scale:
            key = g_scale.lower().rstrip(".")
            v *= next((f for k, f in scale if key.startswith(k)), 1)
        v = round(v, 3)   # kill float dust: 8.1万 -> 81000.00000000001
        out.append(str(int(v)) if v == int(v) else str(v))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter")
    ap.add_argument("--lang", required=True, choices=["ru", "en"])
    ap.add_argument("--file", help="explicit translated-file path (default: book/<lang>/NN-*)")
    args = ap.parse_args()
    n, lang = args.chapter, args.lang

    srcs = [f for f in os.listdir(os.path.join(root, "book"))
            if re.match(rf"{n}-", f) and f.endswith(".md")]
    if not srcs:
        sys.exit(f"chapter {n} not found in book/")
    src_path = os.path.join(root, "book", srcs[0])
    if args.file:
        tr_path = args.file
    else:
        cand = glob.glob(os.path.join(root, "book", lang, f"{n}-*.md"))
        if len(cand) != 1:
            sys.exit(f"expected exactly 1 book/{lang}/{n}-*.md, got {len(cand)}")
        tr_path = cand[0]
    if not os.path.exists(tr_path):
        sys.exit(f"translated file not found: {tr_path}")

    sl = open(src_path, encoding="utf-8").read().splitlines()
    tl = open(tr_path, encoding="utf-8").read().splitlines()

    def body(lines, src_label):
        return [l for l in lines if not l.startswith(src_label) and "成本标签" not in l]

    fails, warns = [], []

    # 1. headings ------------------------------------------------------------
    sh = [x for x in sl if x.startswith("### ")]
    th = [x for x in tl if x.startswith("### ")]
    if len(sh) != len(th):
        fails.append(f"headings {len(sh)} != {len(th)}")

    # 2. cost tags -------------------------------------------------------------
    st = sum(1 for x in sl if "成本标签" in x)
    tt = sum(1 for x in tl if "成本标签" in x)
    if st != tt:
        fails.append(f"cost tags {st} != {tt}")

    # 3. sources: count + byte-identity after label ---------------------------
    ss = [x.split("：", 1)[1].strip() for x in sl if x.startswith("- 来源：")]
    ts = [x.split(":", 1)[1].strip() for x in tl if x.startswith(SRC_LABEL[lang])]
    # post-translation retrofits insert declared title glosses:
    #   [рус. «…»] / [eng. "…"] — strip them from BOTH sides so the byte-identity
    # check still guards everything OUTSIDE the declared insert pattern.
    retrofit = re.compile(r"\s*\[(?:рус\.|eng\.)\s*[«\"](?:[^«»\"]|[«\"][^»\"]*[»\"])*[»\"]\]")
    ss = [retrofit.sub("", x) for x in ss]
    ts = [retrofit.sub("", x) for x in ts]
    if len(ss) != len(ts):
        fails.append(f"sources {len(ss)} != {len(ts)}")
    else:
        for a, b in zip(ss, ts):
            if a != b:
                fails.append("source line mismatch: " + a[:60])

    # 4. field labels (labels from language pack, fallback to built-ins) ---------
    cn_body = body(sl, "- 来源：")
    tr_body = body(tl, SRC_LABEL[lang])
    pack = _lang_pack(lang)
    if pack and pack.get("labels"):
        labels = pack["labels"]
    else:
        labels = LABELS
    if pack and pack.get("banned_calques"):
        banned = pack["banned_calques"]
    else:
        banned = BANNED_RU if lang == "ru" else []
    for i, cn_lab in enumerate(labels["cn"]):
        want = sum(1 for x in cn_body if x.lstrip().startswith("- " + cn_lab))
        got = sum(1 for x in tr_body if x.lstrip().startswith("- " + labels[lang][i]))
        if want != got:
            fails.append(f'field {labels[lang][i]}: {got} != {want} ("- {cn_lab}")')

    # 4.5 plain-terms lines must stay jargon-free (CLAUDE.md: 说人话 bans HR/RR/OR/CI)
    plain = labels[lang][1]
    for idx, l in enumerate(tl, 1):
        if l.lstrip().startswith("- " + plain):
            hits = re.findall(r"\b(?:HR|RR|OR|CI)\b", l)
            if hits:
                warns.append(f"line {idx}: jargon in '{plain}' line: {', '.join(sorted(set(hits)))}")

    # 5. numbers ----------------------------------------------------------------
    cn_nums = norm_numbers("\n".join(cn_body))
    tr_nums = norm_numbers("\n".join(tr_body), ru=(lang == "ru"))
    from collections import Counter
    missing = Counter(cn_nums) - Counter(tr_nums)   # in CN, not in translation
    extra = Counter(tr_nums) - Counter(cn_nums)     # added by translation/localization
    # two-tier: value present but rarer (prose economy, «2023 年第 19 号、2023 年
    # 第 1 号» -> «№ 19 и № 1 2023 года») is a warning; value absent entirely
    # (a number dropped by the translation) is a failure.
    lost_hard = {v: c for v, c in missing.items() if v not in tr_nums}
    lost_soft = {v: c for v, c in missing.items() if v in tr_nums}
    if lost_soft:
        top = ", ".join(f"{v}×{c}" for v, c in sorted(lost_soft.items(),
                         key=lambda x: -x[1])[:10])
        warns.append(f"numbers less frequent (prose economy, check): {top}")
    if lost_hard:
        top = ", ".join(f"{v}×{c}" for v, c in sorted(lost_hard.items(),
                        key=lambda x: -x[1])[:12])
        fails.append(f"numbers absent from translation: {top}")
    if extra:
        top = ", ".join(f"{v}×{c}" for v, c in extra.most_common(12))
        warns.append(f"numbers added (check they are marked inserts): {top}")

    # 6. CJK / fullwidth outside allowed zones ---------------------------------
    zh_lines = []
    in_note = False
    for idx, l in enumerate(tl, 1):
        # translator's note block (TRANSLATION.md insertion convention) is allowed
        # to mention CJK terms — track the whole "> …" block after its marker
        if l.startswith("> Примечание переводчика"):
            in_note = True
        elif not l.startswith(">"):
            in_note = False
        if idx <= 4 or in_note or l.startswith(SRC_LABEL[lang]) or "成本标签" in l:
            continue
        s = re.sub(r"\[[^\]]*\]\([^)]*\)", "[]( )", l)           # whole md links (paths may be CJK)
        s = re.sub(r"\([^)]*[\u4e00-\u9fff][^)]*\)", "(gloss)", s)  # paren glosses
        s = re.sub(r"[«\"「][^»\"」]*[»\"」]", "«»", s)           # quoted spans (contract chars)
        if CJK.search(s):
            zh_lines.append((idx, l.strip()[:70]))
        elif FULLWIDTH.search(s):
            warns.append(f"line {idx}: fullwidth punctuation: {l.strip()[:60]}")
    if zh_lines:
        fails.append(f"CJK outside allowed zones: {len(zh_lines)} line(s), " +
                     "; ".join(f"L{i}:{t}" for i, t in zh_lines[:5]))

    # 7. banned calques (stems from language pack) -------------------------------
    if banned:
        alltr = "\n".join(tl).lower()
        for stem in banned:
            cnt = len(re.findall(stem, alltr))
            if cnt > 1:
                fails.append(f'banned calque "{stem}": {cnt} occurrences (max 1, first-use gloss)')
            elif cnt == 1:
                warns.append(f'calque stem "{stem}" occurs once — must be a parenthetical first-use gloss')

    # report --------------------------------------------------------------------
    print(f"verify {os.path.basename(tr_path)} vs {srcs[0]}")
    for w in warns:
        print("  WARN:", w)
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"OK: headings={len(th)} tags={tt} sources={len(ts)} "
          f"numbers={len(cn_nums)} (lost=0, extra={sum(extra.values())})")
    os.makedirs(os.path.join(root, "tools", ".status"), exist_ok=True)
    mark = os.path.join(root, "tools", ".status", f"{n}-{lang}.ok")
    json.dump({"chapter": n, "lang": lang, "file": os.path.basename(tr_path),
               "ts": time.time(), "nums": len(cn_nums)},
              open(mark, "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
