#!/usr/bin/env python3
"""Integrity gate for one translated chapter (RU or EN) against the Chinese original.

Usage:
  python3 tools/verify.py <NN> --lang ru          # book/ru/NN-*.md
  python3 tools/verify.py <NN> --lang en          # book/en/NN-*.md
  python3 tools/verify.py <NN> --lang ru --file /tmp/candidate.md
  python3 tools/verify.py <NN> --lang ru --file /tmp/candidate.md --json
    # --json: after human lines, emit one JSON object on stdout (also on FAIL,
    # before sys.exit(1)) for tools/llm/repair_wave.py

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
    "es": ["Costo", "En términos sencillos", "Beneficio", "Nivel de evidencia", "Notas"],
}
SRC_LABEL = {"cn": "- 来源：", "ru": "- Источники:", "en": "- Sources:", "es": "- Fuentes:"}
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
    # Range + hundreds compounds — «一两百元» ≈ «одна-две сотни юаней» ≈ «one to
    # two hundred yuan». Expand BOTH endpoints ×100 so the multisets match.
    # MUST precede every bare-numeral rule («две» alone would otherwise fire
    # on «две-три сотни» before the compound is seen — regex alternation is
    # first-match-wins across the whole list, not longest-match).
    (r"(?<!几)[一二两三四五六七八九十][一二两三四五六七八九十万亿千百零]*"
     r"[万亿千百][一二两三四五六七八九十万亿千百零]*",
     lambda raw: _cn_compound(raw)),
    # RU tens-chain × scale: «тридцати шести ... тысячам» = 36×1000 = 36000 —
    # one value, matching CN 三万六千. Chain of 1-2 spelled tens/units + тысяч.
    # Bare scale after «до/несколько»: «до тысячи с лишним» = 1000+ — single
    # scale word with no numeral head still yields the scale value.
    (r"(?:одной|одна|одного|одну|две|два|три|четыре|пять|шесть|семь|восемь|девять|десять|"
     r"сто|ста|сот|двести|двухсот|двест|триста|тр[её]хсот|четыреста|четыр[её]хсот|"
     r"четырехсот|пятьсот|пятисот|шестьсот|шестисот|семьсот|семисот|восемьсот|"
     r"восьмисот|девятьсот|девятисот|двадцат\w*|тридцат\w*|сорока|пятидесят\w*|"
     r"шестьдесят\w*|семидесят\w*|восьмидесят\w*|девяносто)"
     r"(?:[\s-]+(?:одн[ао]го?|два|две|двух|три|тр[её]х|четыре|четыр[её]х|пяти|пять|"
     r"шести|шесть|семи|семь|восьми|восемь|девяти|девять|десять|сто|ста|сорока|"
     r"девяносто|двадцат\w*|тридцат\w*|пятидесят\w*|шестьдесят\w*|семидесят\w*|"
     r"восьмидесят\w*))*"
     r"(?:\s+(?:с\s+лишним|с\s+половиной))?\s*"
     r"(?:тысяч\w*|миллион\w*|млн)",
     lambda raw: _ru_numeral_chain(raw)),
    # «полторы тысячи» = 1500, «полутора миллионами» = 1500000.
    # Clausal ellipsis: «на двух тысячах …, другой на трёх» — the second
    # clause's bare numeral inherits the scale word of the first (mirrors
    # CN 两千…三千). fires when the SAME spelled unit digit reappears
    # with «на/в» + bare numeral up to 60 chars after a «N тысячах».
    (r"(?:на|в)\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)\s*"
     r"тысяч\w*(?:(?:\s+\w+){0,6}),?\s+(?:а\s+)?(?:другой|вторая|второй|"
     r"другие)?\s*(?:на|в)?\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)\b(?!\s*тысяч)",
     lambda raw: (lambda g1, g2: str(_RU_UNITS.get(g1, _RU_TENS.get(g1, 0)) * 1000)
               + " " + str(_RU_UNITS.get(g2, _RU_TENS.get(g2, 0)) * 1000))(
         re.search(r"(?:на|в)\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)\s*тысяч", raw).group(1),
         re.search(r"(?:на|в)?\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)$", raw).group(1))),
    (r"полторы(?:\s*(?:тысяч\w*|миллион\w*|млн))?"
     r"|полутора(?:\s*(?:тысяч\w*|миллион\w*|млн))?",
     lambda raw: "1500" if "тысяч" in raw.lower() else
                 "1500000" if ("миллион" in raw.lower() or "млн" in raw.lower()) else "1.5"),
    # Range ellipsis: «от 2 до 20 тысяч» — the scale attaches to BOTH ends
    # (2 тыс и 20 тыс); fold head digit too when a range до/–/or precedes.
    (r"(\d+(?:[.,]\d+)?)\s*(?:до|—|–|-|или|or)\s*(\d+(?:[.,]\d+)?)\s*"
     r"(тысяч\w*|миллион\w*|млн)",
     lambda raw: _ru_range_scale(raw)),
    (r"(\d+(?:[.,]\d+)?)\s*(?:тысяч\w*|миллион\w*|млн)",
     lambda raw: str(round(float(re.match(r"[\d.,]+", raw.replace(",", ".")).group(0)
                             .rstrip(".")) * (1000000 if ("миллион" in raw or "млн" in raw) else 1000)))),
    (r"(?<![\d,.])тысяч(?:и|а|е|ам|ами|ах)?(?=\s+(?:с\s+)?(?:лишним|половиной)|\s*$|[,.])",
     "1000"),
    (r"(?:одна|два|две|три|четыре|пять|шесть|семь|восемь|девять)\s*[–—-]\s*"
     r"(?:одна|два|две|три|четыре|пять|шесть|семь|восемь|девять)\s*сот\w*",
     lambda raw: _hundred_pair(_RU_NUM, raw)),
    (r"(?:one|two|three|four|five|six|seven|eight|nine)\s+(?:to|or|-)\s+"
     r"(?:two|three|four|five|six|seven|eight|nine)\s+hundred\b",
     lambda raw: _hundred_pair(_EN_NUM, raw)),
    # RU dozens/hundreds («в течение тридцати дней», «двести-триста юаней») —
    # mirror the CN digit-less 数词+百/千/万 shapes («两三百元», «三万多人»).
    # Stem with (?!\w) guard: «сто» must not fire inside «стоимость» etc.
    (r"двести(?!\w)", "200"), (r"триста(?!\w)", "300"),
    (r"четыреста(?!\w)", "400"), (r"пятьсот(?!\w)", "500"),
    (r"шестьсот(?!\w)", "600"), (r"семьсот(?!\w)", "700"),
    (r"восемьсот(?!\w)", "800"), (r"девятьсот(?!\w)", "900"),
    (r"столетн\w*", "100"),  # «столетней давности» == 一百年前
    # genitive plural after «более/около»: «более восьмисот» == 八百多
    (r"двухсот(?!\w)", "200"), (r"трёхсот|трехсот(?!\w)", "300"),
    (r"четырёхсот|четырехсот(?!\w)", "400"), (r"пятисот(?!\w)", "500"),
    (r"шестисот(?!\w)", "600"), (r"семисот(?!\w)", "700"),
    (r"восьмисот(?!\w)", "800"), (r"девятисот(?!\w)", "900"),
    (r"тридцат(?:и|ь|е)(?!\w)", "30"), (r"пятидесят(?:и|ь|е)(?!\w)", "50"),
    # months (stems) — «11 月 1 日» legitimately becomes «1 ноября».
    # Boundary rules: a bare month stem must never match inside a longer word
    # («маяк» is not «мая»), so every stem carries a trailing (?!\w). The RU
    # genitive «мая» additionally requires a digit date context («1 мая») —
    # «мая» is a highly productive word-ending in RU prose («видимая»,
    # «самая», «в начале мая»), and only genuine digit dates pair with the
    # CN «5 月 …» original. EN month names get the same (?!\w) word-end guard.
    (r"январ\w*", "1"), (r"феврал\w*", "2"), (r"март\w*", "3"), (r"апрел\w*", "4"),
    (r"(?<=\d\s)мая(?!\w)", "5"), (r"июн\w*", "6"), (r"июл\w*", "7"), (r"август\w*", "8"),
    (r"сентябр\w*", "9"), (r"октябр\w*", "10"), (r"ноябр\w*", "11"), (r"декабр\w*", "12"),
    (r"january(?!\w)", "1"), (r"february(?!\w)", "2"), (r"march(?!\w)", "3"),
    (r"april(?!\w)", "4"), (r"june(?!\w)", "6"), (r"july(?!\w)", "7"),
    (r"august(?!\w)", "8"), (r"september(?!\w)", "9"), (r"october(?!\w)", "10"),
    (r"november(?!\w)", "11"), (r"december(?!\w)", "12"),
    # EN hundreds: «two to three hundred» == CN «两三百» == RU «двести-триста».
    # Compound BEFORE bare 'two'/'three' so the bare rules don't fire first.
    (r"two[\s-]hundred(?!\w)", "200"), (r"three[\s-]hundred(?!\w)", "300"),
    (r"four[\s-]hundred(?!\w)", "400"), (r"five[\s-]hundred(?!\w)", "500"),
    # spelled-out numerals the translations legitimately use in prose
    (r"одиннадцат\w*", "11"), (r"двенадцат\w*", "12"),
    (r"один(?!\w)", "1"), (r"одна(?!\w)", "1"), (r"одного", "1"), (r"одной", "1"),
    (r"одну", "1"), (r"два(?!\w)", "2"), (r"две(?!\w)", "2"), (r"двух", "2"),
    (r"двум", "2"), (r"обеих", "2"), (r"обоих", "2"), (r"трёх", "3"), (r"трем", "3"),
    (r"четырёх", "4"), (r"четыре(?!\w)", "4"), (r"пяти", "5"), (r"пять(?!\w)", "5"),
    (r"шести", "6"), (r"семи", "7"), (r"восьми", "8"), (r"девяти", "9"),
    (r"полтора", "1.5"), (r"полторы(?!\w)", "1.5"),
    (r"сто шестьдесят пять(?!\w)", "165"),
    (r"сто шестьдесят пят(?:ой|ая|ый|ом)(?!\w)", "165"),
    (r"двести шестьдесят шесть(?!\w)", "266"),
    (r"сто шестьдесят(?!\w)", "160"),
    (r"нулю|ноль", "0"),
    # CN digit-less 数词+scale — corpus census: 三万多人, 一两百元, 两三百元,
    # 两万人的随机, 一万步, 几百元→(几 not folded: 'несколько сотен' stays blind
    # on ALL sides). Compounds before bare; guard (?!\w) so 三百元 keeps 百
    # available for the scale fold? No — 数词 folds to digits, then the scale
    # regex folds «3 百» → 300 via the normal scale path.
    # 几十/几百万 = vague 'tens/hundreds of' — blind on all sides; (?<!几) keeps
    # 几十万 from becoming a phantom 100000.
    # 千卡/千克 are UNITS (kcal/kg), not scale: 两百多千卡 = 200+ kcal — guard
    # (?<!几) sides and exclude unit-composites via lookahead on the digit rule.
    (r"(?<!几)十(?=[万亿千百])", "10"), (r"两(?=[万亿千百](?![卡克瓦赫]))", "2"),
    (r"(?<!几)一(?=[万亿千百](?![卡克瓦赫]))", "1"), (r"(?<!几)二(?=[万亿千百](?![卡克瓦赫]))", "2"),
    (r"(?<!几)三(?=[万亿千百](?![卡克瓦赫]))", "3"), (r"(?<!几)四(?=[万亿千百](?![卡克瓦赫]))", "4"),
    (r"(?<!几)五(?=[万亿千百](?![卡克瓦赫]))", "5"), (r"(?<!几)六(?=[万亿千百](?![卡克瓦赫]))", "6"),
    (r"(?<!几)七(?=[万亿千百](?![卡克瓦赫]))", "7"), (r"(?<!几)八(?=[万亿千百](?![卡克瓦赫]))", "8"),
    (r"(?<!几)九(?=[万亿千百](?![卡克瓦赫]))", "9"),
    (r"\bzero\b", "0"),
    (r"\bone\b", "1"), (r"\btwo\b", "2"), (r"\bthree\b", "3"), (r"\bfour\b", "4"),
    (r"\bfive\b", "5"), (r"\bsix\b", "6"), (r"\bseven\b", "7"), (r"\beight\b", "8"),
    (r"\bnine\b", "9"), (r"\bten\b", "10"), (r"\beleven\b", "11"), (r"\btwelve\b", "12"),
]
WORD_RX = re.compile("|".join(f"(?P<w{i}>{p})" for i, (p, _) in enumerate(WORD_VALUES)),
                     flags=re.I)


_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_EN_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
           "six": 6, "seven": 7, "eight": 8, "nine": 9}
_RU_NUM = {"одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
           "шесть": 6, "семь": 7, "восемь": 8, "девять": 9}


def _hundred_pair(table, raw):
    """«一两百» / «две-три сотни» / «two to three hundred» → '200 300'."""
    nums = []
    for w in re.findall(r"[一二两三四五六七八九十]|[a-zA-Zа-яА-Я]+", raw):
        key = w if w in table else w.lower()
        if key in table:
            nums.append(int(table[key]))
    return " ".join(str(n * 100) for n in nums[:2])


_CN_DIG = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9}


def _ru_range_scale(raw):
    """«от 2 до 20 тысяч» → '2000 20000' (range ellipsis: scale applies to both)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*.{1,3}?\s*(\d+(?:[.,]\d+)?)\s*"
                  r"(тысяч|миллион|млн)", raw)
    lo, hi = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
    scale = 1000000 if m.group(3).startswith(("миллион", "млн")) else 1000
    return f"{round(lo * scale)} {round(hi * scale)}"


def _cn_compound(raw):
    """CN compound numeral run → one value: 一百二十=120, 一千二百五十四=1254,
    一百零三=103, 三万六千=36000. Standard positional parsing of 千/百/十.
    Exception: bare «X两三百»-shape (two plain digits + 百, no 万/千) is the
    approx-range reading → pair (200, 300)."""
    if re.fullmatch(r"[一二两三四五六七八九十][一二两三四五六七八九十]百", raw):
        return _hundred_pair(_CN_NUM, raw[:-1])
    total, section, cur = 0, 0, 0
    prev_scale = None
    for idx, ch in enumerate(raw):
        if ch in _CN_DIG:
            nxt = raw[idx + 1:]
            if prev_scale is not None and (not nxt or nxt[0] not in "十百千万亿零"):
                # Colloquial ellipsis: 一千八 = 1800, 一百五 = 150 — digit right
                # after a scale, at end of the run, means the next-lower scale.
                section += _CN_DIG[ch] * (prev_scale // 10)
            else:
                cur = _CN_DIG[ch]
        elif ch == "十":
            section += (cur or 1) * 10
            cur = 0
            prev_scale = 10
        elif ch == "百":
            section += (cur or 1) * 100
            cur = 0
            prev_scale = 100
        elif ch == "千":
            section += (cur or 1) * 1000
            cur = 0
            prev_scale = 1000
        elif ch == "万":
            total = (total + section + cur) * 10000
            section, cur = 0, 0
            prev_scale = 10000
        elif ch == "亿":
            total = (total + section + cur) * 100000000
            section, cur = 0, 0
            prev_scale = 100000000
        else:
            prev_scale = None  # 零 / trailing units reset ellipsis mode
    return str(total + section + cur)


_RU_TENS = {"двадцати": 20, "двадцать": 20, "тридцати": 30, "тридцать": 30,
            "сорока": 40, "пятидесяти": 50, "пятьдесят": 50,
            "шестидесяти": 60, "шестьдесят": 60, "семидесяти": 70,
            "семьдесят": 70, "восьмидесяти": 80, "восемьдесят": 80,
            "девяносто": 90, "одной": 1, "одна": 1, "двух": 2, "двум": 2,
            "две": 2, "трёх": 3, "трех": 3, "трём": 3, "четырёх": 4,
            "четырех": 4, "четырём": 4, "пяти": 5, "шести": 6, "семи": 7,
            "восьми": 8, "девяти": 9}


def _ru_tens_scale(raw):
    """«тридцати шести тысячам» → 36×1000 = '36000' (spelled tens+units chain
    sharing one scale word)."""
    nums = [_RU_TENS[w.lower()] for w in re.findall(r"[а-яА-ЯёЁ]+", raw)
            if w.lower() in _RU_TENS]
    return str(sum(nums) * 1000)


_RU_UNITS = {"один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3,
             "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8,
             "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12,
             "тринадцать": 13, "четырнадцать": 14, "четырнадцать": 14,
             "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
             "восемнадцать": 18, "девятнадцать": 19}


_RU_HUNDREDS = {"сто": 100, "ста": 100, "сот": 100, "двести": 200,
                "двухсот": 200, "двест": 200, "триста": 300, "трёхсот": 300,
                "трехсот": 300, "четыреста": 400, "четырёхсот": 400,
                "четырехсот": 400, "пятьсот": 500, "пятисот": 500,
                "шестьсот": 600, "шестисот": 600, "семьсот": 700,
                "семисот": 700, "восемьсот": 800, "восьмисот": 800,
                "девятьсот": 900, "девятисот": 900}


def _ru_numeral_chain(raw):
    """Full RU spelled chain + scale: «сто шестьдесят пять тысяч» = 165000,
    «шесть тысяч» = 6000, «тридцати шести с лишним тысячам» = 36000,
    «двести тысяч» = 200000."""
    words = [w.lower() for w in re.findall(r"[а-яА-ЯёЁ]+", raw)]
    scale = 1
    if any(w.startswith("тысяч") for w in words):
        scale = 1000
    elif any(w.startswith("миллион") or w == "млн" for w in words):
        scale = 1000000
    seen = set()
    nums = []
    for w in words:
        if w in seen:
            continue
        v = _RU_TENS.get(w)
        if v is None:
            v = _RU_UNITS.get(w)
        if v is None:
            v = _RU_HUNDREDS.get(w)
        if v is not None:
            nums.append(v)
            seen.add(w)
    # Additive semantics for corpus shapes: сто+шестьдесят+пять=165,
    # тридцати+шести=36; hundreds×scale handled by the multiply below.
    return str(sum(nums) * scale)


def fold_words(text):
    """Replace spelled-out numerals / month names with their digit values so the
    value-space comparison treats «1 ноября» == «11 月 1 日» == «November 1»."""
    def rep(m):
        idx = next(i for i in range(len(WORD_VALUES)) if m.group(f"w{i}") is not None)
        val = WORD_VALUES[idx][1]
        if callable(val):
            return f" {val(m.group(f'w{idx}'))} "
        return f" {val} "
    return WORD_RX.sub(rep, text)


def norm_numbers(text, ru=False, es=False):
    """Multiset of ABSOLUTE numeric values: scale-words (万/亿/тыс./млн/млрд/
    thousand/million/billion/mil/millones) are folded into the value, so «65.4 万»
    == «654 тыс.» == «654,000» == «654 000». Comma handling is language-dependent:
    RU/ES use the comma as the decimal separator and a space as the thousands
    separator; CN/EN use the dot as decimal and the comma as thousands separator."""
    text = text.replace("\u00a0", " ")
    text = text.replace("\u202f", " ")   # ES narrow no-break space thousands
    if ru:
        # «4,257 млрд» — a comma directly before a scale word is DECIMAL
        text = re.sub(r"(\d),(\d{3})(?=\s*(?:тыс|млн|млрд|трлн|триллион|миллион|"
                      r"миллиард|thousand|million|billion|trillion)\b)",
                      r"\1.\2", text, flags=re.I)
        # EN-style comma thousands may survive in RU prose («25,871 человек»).
        # A comma after a LONE leading zero starts a decimal («0,001»),
        # but «100,000» / «112,000» are thousands even though the group
        # before the comma ends in 0 — so anchor the zero rule to the
        # number's first digit, not to any digit before the comma.
        # thousands-strip: a comma followed by exactly 3 digits is thousands
        # UNLESS the whole number is a lone leading zero («0,891» is decimal)
        # OR the comma-group sits in a ratio/CI context: «отношение рисков —
        # 1,134», «95% CI 1,065–1,207» — HR values < 10 with 3-digit decimal
        # tails. Discriminators for decimal (not thousands): a dot-notation
        # twin nearby («1.134»), a CI dash between two comma-groups of the
        # same shape, or a «(95% CI» / «рисков» cue within ~40 chars.
        # «100,000»/«112,000» strip even though the group ends in 0.
        text = re.sub(r"(?<![\d.])0,(?=\d{3}(?!\d))", lambda m: "0\x00", text)  # mark decimal comma
        _hr = re.compile(r"(?<![\d.,])([1-9]\d?),(\d{3})(?!\d)")
        _marks = []  # collect first, then apply right-to-left (offsets stay valid)
        for m in _hr.finditer(text):
            ctx = text[max(0, m.start() - 60):m.end() + 60]
            if (re.search(r"[\d.],\d{3}\s*(?:[–—-]|до\b|to\b|and\b)\s*[\d.]*,?\d{3}", ctx)
                    or re.search(r"(?:95\s*%\s*CI|риско|CI\s|доверительн)", ctx, re.I)):
                _marks.append((m.start(), m.end(), m.group(1) + "\x00" + m.group(2)))
        for a, b, rep in reversed(_marks):
            text = text[:a] + rep + text[b:]
        text = re.sub(r",(?=\d{3}(?!\d))", "", text)                 # strip thousands commas
        text = text.replace("\x00", ".")                             # restore decimal
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)          # RU decimal comma
        text = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", text)  # RU space thousands
    elif es:
        # ES: space thousands «25 871», decimal comma «0,001»; a comma before
        # a scale word is decimal («4,257 millones»)
        text = re.sub(r"(\d),(\d{3})(?=\s*(?:mil(?:|es)\b|millones|millón\b|"
                      r"mil millones|billones|trillones))", r"\1.\2", text, flags=re.I)
        # ES: comma is DECIMAL in body prose (ratios «1,134», «0,891»); thousands
        # use space («25 871»). Comma-thousands occur only inside «- Fuentes:»
        # quote blocks, which check 5 excludes from number counting — so no
        # thousands-strip here (unlike RU, where body comma-groups are
        # thousands: «1,040 человек», «44,573»).
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)          # ES decimal comma
        text = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", text)  # ES space thousands
    else:
        text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)  # EN/CN comma thousands
    text = fold_words(text)
    # distributive scale: «от 81 до 138 тыс.» == «8.1 万 到 13.8 万» — the scale
    # word applies to BOTH endpoints in Russian prose; duplicate it backwards.
    # ONLY when the endpoints are magnitude-compatible (same order, ratio
    # 1e-3..1e3): «100,000 to 1 million» is NOT distributive (the first
    # endpoint carries its own full value) — cloning the scale there creates a
    # phantom 1e11. Mixed magnitudes keep the scale on the last endpoint only.
    _distrib = re.compile(
        r"(\d+(?:\.\d+)?)((?:\s+(?:до|and|to|a|de)\s*|\s*[–—-]\s*)\d+(?:\.\d+)?)"
        r"\s*(тыс\.?|млн\.?|млрд\.?|трлн\.?|thousand|million|billion|тысяч|"
        r"миллион|миллиард|триллион|trillion|millones|millón|billones|mil)\b",
        flags=re.I)

    def _distribute(m: "re.Match") -> str:
        first, mid, scale = m.group(1), m.group(2), m.group(3)
        second = re.search(r"\d+(?:\.\d+)?", mid).group(0)
        key = scale.lower().rstrip(".")
        factor = {"тыс": 1e3, "тысяч": 1e3, "млн": 1e6, "миллион": 1e6,
                  "млрд": 1e9, "миллиард": 1e9, "трлн": 1e12, "триллион": 1e12,
                  "thousand": 1e3, "million": 1e6, "billion": 1e9,
                  "trillion": 1e12, "mil": 1e3}.get(key, 1)
        # Distributive ONLY when the two BARE endpoints are magnitude peers
        # (ratio 1e-2..1e2): «от 81 до 138 тыс.», «de 2 a 3 millones» — the
        # scale word naturally reads onto both ends. «100,000 to 1 million»
        # (first is a complete value on its own) and «от 2000 до 10 тыс»
        # (first is absolute) must NOT clone — the scale stays on the last
        # endpoint only.
        a, b = float(first), float(second)
        if a > 0 and b > 0 and 1e-2 <= (a / b) <= 1e2:
            return f"{first} {scale}{mid} {scale}"
        return m.group(0)   # mixed magnitudes: leave as-is (no phantom clone)

    text = _distrib.sub(_distribute, text)
    # scale list: order matters — next() takes the FIRST key the captured
    # token startswith(), so longer/compound keys must precede their prefixes
    # («mil millones» before «mil », «千万» before «千», «миллиард» before «млн»-
    # family). Compound «mil millones» (=1e9) must also be one regex token,
    # else «mil» (1e3) and the orphaned «millones» get counted separately.
    scale = [("mil millones", 1e9), ("mil millón", 1e9), ("mil millon", 1e9),
             ("тысяч", 1e3), ("тыс", 1e3), ("миллион", 1e6), ("млн", 1e6),
             ("миллиард", 1e9), ("млрд", 1e9), ("трлн", 1e12), ("триллион", 1e12),
             ("trillion", 1e12), ("万亿", 1e12), ("千万", 1e7), ("百万", 1e6),
             ("万", 1e4), ("亿", 1e8), ("千", 1e3), ("百", 1e2),
             ("thousand", 1e3), ("million", 1e6), ("billion", 1e9),
             ("millones", 1e6), ("millón", 1e6), ("millon", 1e6), ("mil", 1e3),
             ("billones", 1e12), ("billón", 1e12), ("trillones", 1e12)]
    out = []
    for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*[多余]?\s*(万亿|千万|百万|万|亿|千(?![卡克瓦赫])|百)\s*[多余]?|"
            r"(\d+(?:\.\d+)?)\s*(万亿|千万|百万|万|亿|千(?![卡克瓦赫])|百|тысяч\w*|тыс\.?|миллион\w*|млн|"
            r"миллиард\w*|млрд|трлн|триллион\w*|trillion|thousand|million|billion|"
            r"mil\s+millones|mil\s+millón|mil\s+millon|millones|millón\b|"
            r"billones|billón\b|trillones|mil\b)?",
            text, flags=re.I):
        g_num, g_scale = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        v = float(g_num)
        if g_scale:
            key = g_scale.lower().rstrip(".")
            v *= next((f for k, f in scale if key.startswith(k)), 1)
        # kill float dust (65,4 тыс. -> 65400.00000000001) WITHOUT truncating
        # meaningful small decimals (p-value 0.0093 must stay 0.0093);
        # round(v, 3) here broke it to 0.009. Trailing-9/0 run cleanup:
        # a ≥6-digit junk tail (dust) collapses to 15 significant digits.
        s = f"{v:.15g}"
        if re.search(r"\.(\d*?)((?:0{6}|9{6})\d*)$", s):
            s = f"{round(v, 10 - (len(str(int(v))) if v >= 1 else 0))!r}"
            if s.endswith(".0"):
                s = s[:-2]
        out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter")
    ap.add_argument("--lang", required=True, choices=["ru", "en", "es"])
    ap.add_argument("--file", help="explicit translated-file path (default: book/<lang>/NN-*)")
    ap.add_argument(
        "--json",
        action="store_true",
        help="emit machine JSON report on stdout (before exit on FAIL)",
    )
    args = ap.parse_args()
    n, lang = args.chapter, args.lang

    srcs = [f for f in os.listdir(os.path.join(root, "book"))
            if re.match(rf"{n}-", f) and f.endswith(".md")]
    if not srcs:
        sys.exit(f"chapter {n} not found in book/")
    src_path = os.path.join(root, "book", srcs[0])
    if args.file:
        tr_path = args.file
        explicit_file = True
    else:
        cand = glob.glob(os.path.join(root, "book", lang, f"{n}-*.md"))
        if len(cand) != 1:
            sys.exit(f"expected exactly 1 book/{lang}/{n}-*.md, got {len(cand)}")
        tr_path = cand[0]
        explicit_file = False
    if not os.path.exists(tr_path):
        sys.exit(f"translated file not found: {tr_path}")

    sl = open(src_path, encoding="utf-8").read().splitlines()
    tl = open(tr_path, encoding="utf-8").read().splitlines()

    src_labels = ("- 来源：", "- Sources:", "- Fuentes:", "- Источники:")

    def body(lines, src_label):
        return [l for l in lines
                if not any(l.startswith(s) for s in src_labels)
                and "成本标签" not in l]

    fails, warns = [], []
    fail_objs, warn_objs = [], []

    def add_fail(msg, obj):
        fails.append(msg)
        fail_objs.append(obj)

    def add_warn(msg, obj):
        warns.append(msg)
        warn_objs.append(obj)

    # 1. headings ------------------------------------------------------------
    sh = [x for x in sl if x.startswith("### ")]
    th = [x for x in tl if x.startswith("### ")]
    if len(sh) != len(th):
        add_fail(
            f"headings {len(sh)} != {len(th)}",
            {"kind": "headings_mismatch", "got": len(th), "want": len(sh)},
        )

    # 2. cost tags -------------------------------------------------------------
    st = sum(1 for x in sl if "成本标签" in x)
    tt = sum(1 for x in tl if "成本标签" in x)
    if st != tt:
        add_fail(
            f"cost tags {st} != {tt}",
            {"kind": "cost_tags_mismatch", "got": tt, "want": st},
        )

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
        add_fail(
            f"sources {len(ss)} != {len(ts)}",
            {"kind": "sources_mismatch", "got": len(ts), "want": len(ss)},
        )
    else:
        for a, b in zip(ss, ts):
            if a != b:
                add_fail(
                    "source line mismatch: " + a[:60],
                    {"kind": "source_line_mismatch", "preview": a[:60]},
                )

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
    if not banned:
        # maintainer signal, NOT a translation-quality WARN: an empty calque
        # list makes check 7 a silent no-op for this language. Goes to stderr
        # so the --json stdout contract (parse_verify_json scans stdout only)
        # stays safe.
        print(f"  (note: no banned_calques configured for lang={lang} — "
              f"calque check is a no-op for this run)", file=sys.stderr)
    for i, cn_lab in enumerate(labels["cn"]):
        want = sum(1 for x in cn_body if x.lstrip().startswith("- " + cn_lab))
        got = sum(1 for x in tr_body if x.lstrip().startswith("- " + labels[lang][i]))
        if want != got:
            add_fail(
                f'field {labels[lang][i]}: {got} != {want} ("- {cn_lab}")',
                {
                    "kind": "field_count",
                    "label": labels[lang][i],
                    "got": got,
                    "want": want,
                    "cn_label": cn_lab,
                },
            )

    # 4.5 plain-terms lines must stay jargon-free (CLAUDE.md: 说人话 bans HR/RR/OR/CI)
    plain = labels[lang][1]
    for idx, l in enumerate(tl, 1):
        if l.lstrip().startswith("- " + plain):
            hits = re.findall(r"\b(?:HR|RR|OR|CI)\b", l)
            if hits:
                add_warn(
                    f"line {idx}: jargon in '{plain}' line: {', '.join(sorted(set(hits)))}",
                    {
                        "kind": "jargon_in_plain",
                        "line": idx,
                        "hits": sorted(set(hits)),
                    },
                )

    # 5. numbers ----------------------------------------------------------------
    cn_nums = norm_numbers("\n".join(cn_body))
    tr_nums = norm_numbers("\n".join(tr_body), ru=(lang == "ru"), es=(lang == "es"))
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
        for v, c in lost_soft.items():
            warn_objs.append(
                {"kind": "number_less_frequent", "value": str(v), "count": int(c)}
            )
    if lost_hard:
        top = ", ".join(f"{v}×{c}" for v, c in sorted(lost_hard.items(),
                        key=lambda x: -x[1])[:12])
        fails.append(f"numbers absent from translation: {top}")
        for v, c in lost_hard.items():
            fail_objs.append(
                {"kind": "number_absent", "value": str(v), "count": int(c)}
            )
    if extra:
        top = ", ".join(f"{v}×{c}" for v, c in extra.most_common(12))
        warns.append(f"numbers added (check they are marked inserts): {top}")
        for v, c in extra.items():
            warn_objs.append(
                {"kind": "number_added", "value": str(v), "count": int(c)}
            )

    # 6. CJK / fullwidth outside allowed zones ---------------------------------
    zh_lines = []
    in_note = False
    for idx, l in enumerate(tl, 1):
        # translator's note block (TRANSLATION.md insertion convention) is allowed
        # to mention CJK terms — track the whole "> …" block after its marker
        if l.startswith("> Примечание переводчика") or l.startswith("> Translator's note") or l.startswith("> Nota del traductor"):
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
            add_warn(
                f"line {idx}: fullwidth punctuation: {l.strip()[:60]}",
                {"kind": "fullwidth", "line": idx},
            )
    if zh_lines:
        add_fail(
            f"CJK outside allowed zones: {len(zh_lines)} line(s), " +
            "; ".join(f"L{i}:{t}" for i, t in zh_lines[:5]),
            {
                "kind": "cjk_outside",
                "count": len(zh_lines),
                "samples": [{"line": i, "text": t} for i, t in zh_lines[:5]],
            },
        )

    # 7. banned calques (stems from language pack) -------------------------------
    if banned:
        alltr = "\n".join(tl).lower()
        for stem in banned:
            cnt = len(re.findall(stem, alltr))
            if cnt > 1:
                add_fail(
                    f'banned calque "{stem}": {cnt} occurrences (max 1, first-use gloss)',
                    {"kind": "banned_calque", "stem": stem, "count": cnt},
                )
            elif cnt == 1:
                add_warn(
                    f'calque stem "{stem}" occurs once — must be a parenthetical first-use gloss',
                    {"kind": "calque_once", "stem": stem, "count": 1},
                )

    # report --------------------------------------------------------------------
    print(f"verify {os.path.basename(tr_path)} vs {srcs[0]}")
    for w in warns:
        print("  WARN:", w)
    report = {
        "ok": not fails,
        "chapter": n,
        "lang": lang,
        "file": tr_path,
        "fails": fail_objs,
        "warns": warn_objs,
    }
    # JSON must be the LAST stdout line (also on FAIL) so consumers can parse
    # `stdout[stdout.rfind("{"):]` without hitting "Extra data" from human text.
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    if fails:
        sys.exit(1)
    print(f"OK: headings={len(th)} tags={tt} sources={len(ts)} "
          f"numbers={len(cn_nums)} (lost=0, extra={sum(extra.values())})")
    os.makedirs(os.path.join(root, "tools", ".status"), exist_ok=True)
    if explicit_file:
        # a candidate file is not the committed book: do not refresh the
        # chapter's freshness stamp (mutation harness/tests pass --file)
        print("stamp skipped (--file mode)")
        return
    mark = os.path.join(root, "tools", ".status", f"{n}-{lang}.ok")
    json.dump({"chapter": n, "lang": lang, "file": os.path.basename(tr_path),
               "ts": time.time(), "nums": len(cn_nums)},
              open(mark, "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
