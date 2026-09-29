#!/usr/bin/env python3
"""Integrity gate for one translated chapter (RU or EN) against the Chinese original.

Usage:
  python3 translate/steps/verify/verify.py <NN> --lang ru          # book/ru/NN-*.md
  python3 translate/steps/verify/verify.py <NN> --lang en          # book/en/NN-*.md
  python3 translate/steps/verify/verify.py <NN> --lang ru --file /tmp/candidate.md
  python3 translate/steps/verify/verify.py <NN> --lang ru --file /tmp/candidate.md --json
    # --json: after human lines, emit one JSON object on stdout (also on FAIL,
    # before sys.exit(1)) for translate/steps/repair/repair_wave.py

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

On success writes translate/.status/<NN>-<lang>.ok (mtime-stamped) for status.py.
"""

import argparse
import json
import os
import re
import sys
import time

from translate.lib import labels
from translate.lib.config import default_root, translation_langs
from translate.lib.paths import cn_chapter_path, tr_chapter_path

root = default_root()

CJK = re.compile(r"[\u4e00-\u9fff]")
FULLWIDTH = re.compile(r"[，。：；！？「」『』（）]")

WORD_VALUES = [
    (r"двадцать[\s-]?четыре", "24"),
    (r"twenty-four", "24"),
    (r"круглосуточн\w*", "24"),
    (r"(a?round|around)-the-clock", "24"),
    (
        r"(?<!几)[一二两三四五六七八九十][一二两三四五六七八九十万亿千百零]*"
        r"[万亿千百][一二两三四五六七八九十万亿千百零]*",
        lambda raw: _cn_compound(raw),
    ),
    (
        r"(?:одной|одна|одного|одну|две|два|три|четыре|пять|шесть|семь|восемь|девять|десять|"
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
        lambda raw: _ru_numeral_chain(raw),
    ),
    (
        r"(?:на|в)\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)\s*"
        r"тысяч\w*(?:(?:\s+\w+){0,6}),?\s+(?:а\s+)?(?:другой|вторая|второй|"
        r"другие)?\s*(?:на|в)?\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)\b(?!\s*тысяч)",
        lambda raw: (
            lambda g1, g2: (
                str(_RU_UNITS.get(g1, _RU_TENS.get(g1, 0)) * 1000)
                + " "
                + str(_RU_UNITS.get(g2, _RU_TENS.get(g2, 0)) * 1000)
            )
        )(
            re.search(
                r"(?:на|в)\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)\s*тысяч", raw
            ).group(1),
            re.search(
                r"(?:на|в)?\s+(два|две|двух|три|тр[её]х|четыре|четыр[её]х|пять|пяти)$", raw
            ).group(1),
        ),
    ),
    (
        r"полторы(?:\s*(?:тысяч\w*|миллион\w*|млн))?"
        r"|полутора(?:\s*(?:тысяч\w*|миллион\w*|млн))?",
        lambda raw: (
            "1500"
            if "тысяч" in raw.lower()
            else "1500000"
            if ("миллион" in raw.lower() or "млн" in raw.lower())
            else "1.5"
        ),
    ),
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:до|—|–|-|или|or)\s*(\d+(?:[.,]\d+)?)\s*"
        r"(тысяч\w*|миллион\w*|млн)",
        lambda raw: _ru_range_scale(raw),
    ),
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:тысяч\w*|миллион\w*|млн)",
        lambda raw: str(
            round(
                float(re.match(r"[\d.,]+", raw.replace(",", ".")).group(0).rstrip("."))
                * (1000000 if ("миллион" in raw or "млн" in raw) else 1000)
            )
        ),
    ),
    (r"(?<![\d,.])тысяч(?:и|а|е|ам|ами|ах)?(?=\s+(?:с\s+)?(?:лишним|половиной)|\s*$|[,.])", "1000"),
    (
        r"(?:одна|два|две|три|четыре|пять|шесть|семь|восемь|девять)\s*[–—-]\s*"
        r"(?:одна|два|две|три|четыре|пять|шесть|семь|восемь|девять)\s*сот\w*",
        lambda raw: _hundred_pair(_RU_NUM, raw),
    ),
    (
        r"(?:one|two|three|four|five|six|seven|eight|nine)\s+(?:to|or|-)\s+"
        r"(?:two|three|four|five|six|seven|eight|nine)\s+hundred\b",
        lambda raw: _hundred_pair(_EN_NUM, raw),
    ),
    (r"двести(?!\w)", "200"),
    (r"триста(?!\w)", "300"),
    (r"четыреста(?!\w)", "400"),
    (r"пятьсот(?!\w)", "500"),
    (r"шестьсот(?!\w)", "600"),
    (r"семьсот(?!\w)", "700"),
    (r"восемьсот(?!\w)", "800"),
    (r"девятьсот(?!\w)", "900"),
    (r"столетн\w*", "100"),
    (r"двухсот(?!\w)", "200"),
    (r"трёхсот|трехсот(?!\w)", "300"),
    (r"четырёхсот|четырехсот(?!\w)", "400"),
    (r"пятисот(?!\w)", "500"),
    (r"шестисот(?!\w)", "600"),
    (r"семисот(?!\w)", "700"),
    (r"восьмисот(?!\w)", "800"),
    (r"девятисот(?!\w)", "900"),
    (r"тридцат(?:и|ь|е)(?!\w)", "30"),
    (r"пятидесят(?:и|ь|е)(?!\w)", "50"),
    (r"январ\w*", "1"),
    (r"феврал\w*", "2"),
    (r"март\w*", "3"),
    (r"апрел\w*", "4"),
    (r"(?<=\d\s)мая(?!\w)", "5"),
    (r"июн\w*", "6"),
    (r"июл\w*", "7"),
    (r"август\w*", "8"),
    (r"сентябр\w*", "9"),
    (r"октябр\w*", "10"),
    (r"ноябр\w*", "11"),
    (r"декабр\w*", "12"),
    (r"january(?!\w)", "1"),
    (r"february(?!\w)", "2"),
    (r"march(?!\w)", "3"),
    (r"april(?!\w)", "4"),
    (r"june(?!\w)", "6"),
    (r"july(?!\w)", "7"),
    (r"august(?!\w)", "8"),
    (r"september(?!\w)", "9"),
    (r"october(?!\w)", "10"),
    (r"november(?!\w)", "11"),
    (r"december(?!\w)", "12"),
    (r"two[\s-]hundred(?!\w)", "200"),
    (r"three[\s-]hundred(?!\w)", "300"),
    (r"four[\s-]hundred(?!\w)", "400"),
    (r"five[\s-]hundred(?!\w)", "500"),
    (r"одиннадцат\w*", "11"),
    (r"двенадцат\w*", "12"),
    (r"один(?!\w)", "1"),
    (r"одна(?!\w)", "1"),
    (r"одного", "1"),
    (r"одной", "1"),
    (r"одну", "1"),
    (r"два(?!\w)", "2"),
    (r"две(?!\w)", "2"),
    (r"двух", "2"),
    (r"двум", "2"),
    (r"обеих", "2"),
    (r"обоих", "2"),
    (r"трёх", "3"),
    (r"трем", "3"),
    (r"четырёх", "4"),
    (r"четыре(?!\w)", "4"),
    (r"пяти", "5"),
    (r"пять(?!\w)", "5"),
    (r"шести", "6"),
    (r"семи", "7"),
    (r"восьми", "8"),
    (r"девяти", "9"),
    (r"полтора", "1.5"),
    (r"полторы(?!\w)", "1.5"),
    (r"сто шестьдесят пять(?!\w)", "165"),
    (r"сто шестьдесят пят(?:ой|ая|ый|ом)(?!\w)", "165"),
    (r"двести шестьдесят шесть(?!\w)", "266"),
    (r"сто шестьдесят(?!\w)", "160"),
    (r"нулю|ноль", "0"),
    (r"(?<!几)十(?=[万亿千百])", "10"),
    (r"两(?=[万亿千百](?![卡克瓦赫]))", "2"),
    (r"(?<!几)一(?=[万亿千百](?![卡克瓦赫]))", "1"),
    (r"(?<!几)二(?=[万亿千百](?![卡克瓦赫]))", "2"),
    (r"(?<!几)三(?=[万亿千百](?![卡克瓦赫]))", "3"),
    (r"(?<!几)四(?=[万亿千百](?![卡克瓦赫]))", "4"),
    (r"(?<!几)五(?=[万亿千百](?![卡克瓦赫]))", "5"),
    (r"(?<!几)六(?=[万亿千百](?![卡克瓦赫]))", "6"),
    (r"(?<!几)七(?=[万亿千百](?![卡克瓦赫]))", "7"),
    (r"(?<!几)八(?=[万亿千百](?![卡克瓦赫]))", "8"),
    (r"(?<!几)九(?=[万亿千百](?![卡克瓦赫]))", "9"),
    (r"\bzero\b", "0"),
    (r"\bone\b", "1"),
    (r"\btwo\b", "2"),
    (r"\bthree\b", "3"),
    (r"\bfour\b", "4"),
    (r"\bfive\b", "5"),
    (r"\bsix\b", "6"),
    (r"\bseven\b", "7"),
    (r"\beight\b", "8"),
    (r"\bnine\b", "9"),
    (r"\bten\b", "10"),
    (r"\beleven\b", "11"),
    (r"\btwelve\b", "12"),
]
WORD_RX = re.compile(
    "|".join(f"(?P<w{i}>{p})" for i, (p, _) in enumerate(WORD_VALUES)), flags=re.IGNORECASE
)


_CN_NUM = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
_EN_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}
_RU_NUM = {
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
}


def _hundred_pair(table, raw):
    """«一两百» / «две-три сотни» / «two to three hundred» → '200 300'."""
    nums = []
    for w in re.findall(r"[一二两三四五六七八九十]|[a-zA-Zа-яА-Я]+", raw):
        key = w if w in table else w.lower()
        if key in table:
            nums.append(int(table[key]))
    return " ".join(str(n * 100) for n in nums[:2])


_CN_DIG = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _ru_range_scale(raw):
    """«от 2 до 20 тысяч» → '2000 20000' (range ellipsis: scale applies to both)."""
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*.{1,3}?\s*(\d+(?:[.,]\d+)?)\s*"
        r"(тысяч|миллион|млн)",
        raw,
    )
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
            nxt = raw[idx + 1 :]
            if prev_scale is not None and (not nxt or nxt[0] not in "十百千万亿零"):
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
            prev_scale = None
    return str(total + section + cur)


_RU_TENS = {
    "двадцати": 20,
    "двадцать": 20,
    "тридцати": 30,
    "тридцать": 30,
    "сорока": 40,
    "пятидесяти": 50,
    "пятьдесят": 50,
    "шестидесяти": 60,
    "шестьдесят": 60,
    "семидесяти": 70,
    "семьдесят": 70,
    "восьмидесяти": 80,
    "восемьдесят": 80,
    "девяносто": 90,
    "одной": 1,
    "одна": 1,
    "двух": 2,
    "двум": 2,
    "две": 2,
    "трёх": 3,
    "трех": 3,
    "трём": 3,
    "четырёх": 4,
    "четырех": 4,
    "четырём": 4,
    "пяти": 5,
    "шести": 6,
    "семи": 7,
    "восьми": 8,
    "девяти": 9,
}


_RU_UNITS = {
    "один": 1,
    "одна": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
}


_RU_HUNDREDS = {
    "сто": 100,
    "ста": 100,
    "сот": 100,
    "двести": 200,
    "двухсот": 200,
    "двест": 200,
    "триста": 300,
    "трёхсот": 300,
    "трехсот": 300,
    "четыреста": 400,
    "четырёхсот": 400,
    "четырехсот": 400,
    "пятьсот": 500,
    "пятисот": 500,
    "шестьсот": 600,
    "шестисот": 600,
    "семьсот": 700,
    "семисот": 700,
    "восемьсот": 800,
    "восьмисот": 800,
    "девятьсот": 900,
    "девятисот": 900,
}


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
    RU uses comma as decimal and space as thousands; ES also uses comma as decimal
    and space or dot as thousands («9.676» == «9 676» == «9676»); CN/EN use the
    dot as decimal and the comma as thousands separator."""
    text = text.replace("\u00a0", " ")
    text = text.replace("\u202f", " ")
    text = re.sub(r"(?<![\d.])\.(\d+)", r"0.\1", text)
    if ru:
        text = re.sub(
            r"(\d),(\d{3})(?=\s*(?:тыс|млн|млрд|трлн|триллион|миллион|"
            r"миллиард|thousand|million|billion|trillion)\b)",
            r"\1.\2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"(?<![\d.])0,(?=\d{3}(?!\d))", lambda _m: "0\x00", text)
        _hr = re.compile(r"(?<![\d.,])([1-9]\d?),(\d{3})(?!\d)")
        _marks = []
        for m in _hr.finditer(text):
            ctx = text[max(0, m.start() - 60) : m.end() + 60]
            if re.search(
                r"[\d.],\d{3}\s*(?:[–—-]|до\b|to\b|and\b)\s*[\d.]*,?\d{3}", ctx
            ) or re.search(r"(?:95\s*%\s*CI|риско|CI\s|доверительн)", ctx, re.IGNORECASE):
                _marks.append((m.start(), m.end(), m.group(1) + "\x00" + m.group(2)))
        for a, b, rep in reversed(_marks):
            text = text[:a] + rep + text[b:]
        text = re.sub(r",(?=\d{3}(?!\d))", "", text)
        text = text.replace("\x00", ".")
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
        text = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", text)
    elif es:
        # Fold thousands dots before commas become decimals. «9.676» / «1.234.567»
        # must not be read as 9.676 / 1.234 after the comma→dot pass (that would
        # turn «1,676» into the decimal 1.676, which is correct and distinct).
        text = re.sub(
            r"(?<![\d,])(\d{1,3}(?:\.\d{3})+)(?!\d)",
            lambda m: m.group(1).replace(".", ""),
            text,
        )
        text = re.sub(
            r"(\d),(\d{3})(?=\s*(?:mil(?:|es)\b|millones|millón\b|"
            r"mil millones|billones|trillones))",
            r"\1.\2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
        text = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", "", text)
    else:
        text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    text = fold_words(text)
    _distrib = re.compile(
        r"(\d+(?:\.\d+)?)((?:\s+(?:до|and|to|a|de)\s*|\s*[–—-]\s*)\d+(?:\.\d+)?)"
        r"\s*(тыс\.?|млн\.?|млрд\.?|трлн\.?|thousand|million|billion|тысяч|"
        r"миллион|миллиард|триллион|trillion|millones|millón|billones|mil)\b",
        flags=re.IGNORECASE,
    )

    def _distribute(m: "re.Match") -> str:
        first, mid, scale = m.group(1), m.group(2), m.group(3)
        second = re.search(r"\d+(?:\.\d+)?", mid).group(0)
        key = scale.lower().rstrip(".")
        _scale_map = {
            "тыс": 1e3,
            "тысяч": 1e3,
            "млн": 1e6,
            "миллион": 1e6,
            "млрд": 1e9,
            "миллиард": 1e9,
            "трлн": 1e12,
            "триллион": 1e12,
            "thousand": 1e3,
            "million": 1e6,
            "billion": 1e9,
            "trillion": 1e12,
            "mil": 1e3,
        }.get(key, 1)
        a, b = float(first), float(second)
        if a > 0 and b > 0 and 1e-2 <= (a / b) <= 1e2:
            return f"{first} {scale}{mid} {scale}"
        return m.group(0)

    text = _distrib.sub(_distribute, text)
    scale = [
        ("mil millones", 1e9),
        ("mil millón", 1e9),
        ("mil millon", 1e9),
        ("тысяч", 1e3),
        ("тыс", 1e3),
        ("миллион", 1e6),
        ("млн", 1e6),
        ("миллиард", 1e9),
        ("млрд", 1e9),
        ("трлн", 1e12),
        ("триллион", 1e12),
        ("trillion", 1e12),
        ("万亿", 1e12),
        ("千万", 1e7),
        ("百万", 1e6),
        ("万", 1e4),
        ("亿", 1e8),
        ("千", 1e3),
        ("百", 1e2),
        ("thousand", 1e3),
        ("million", 1e6),
        ("billion", 1e9),
        ("millones", 1e6),
        ("millón", 1e6),
        ("millon", 1e6),
        ("mil", 1e3),
        ("billones", 1e12),
        ("billón", 1e12),
        ("trillones", 1e12),
    ]
    out = []
    for m in re.finditer(
        r"(\d+(?:\.\d+)?)\s*[多余]?\s*(万亿|千万|百万|万|亿|千(?![卡克瓦赫])|百)\s*[多余]?|"
        r"(\d+(?:\.\d+)?)\s*(万亿|千万|百万|万|亿|千(?![卡克瓦赫])|百|тысяч\w*|тыс\.?|миллион\w*|млн|"
        r"миллиард\w*|млрд|трлн|триллион\w*|trillion|thousand|million|billion|"
        r"mil\s+millones|mil\s+millón|mil\s+millon|millones|millón\b|"
        r"billones|billón\b|trillones|mil\b)?",
        text,
        flags=re.IGNORECASE,
    ):
        g_num, g_scale = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        v = float(g_num)
        if g_scale:
            key = g_scale.lower().rstrip(".")
            v *= next((f for k, f in scale if key.startswith(k)), 1)
        s = f"{v:.15g}"
        if re.search(r"\.(\d*?)((?:0{6}|9{6})\d*)$", s):
            s = f"{round(v, 10 - (len(str(int(v))) if v >= 1 else 0))!r}"
            s = s.removesuffix(".0")
        out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter")
    ap.add_argument("--lang", required=True, choices=translation_langs())
    ap.add_argument("--file", help="explicit translated-file path (default: book/<lang>/NN-*)")
    ap.add_argument(
        "--json",
        action="store_true",
        help="emit machine JSON report on stdout (before exit on FAIL)",
    )
    args = ap.parse_args()
    n, lang = args.chapter, args.lang

    try:
        src_path = cn_chapter_path(root, n)
    except FileNotFoundError as e:
        sys.exit(str(e))
    if args.file:
        tr_path = args.file
        explicit_file = True
    else:
        try:
            tr_path = tr_chapter_path(root, n, lang)
        except FileNotFoundError as e:
            sys.exit(str(e))
        explicit_file = False
    if not os.path.exists(tr_path):
        sys.exit(f"translated file not found: {tr_path}")

    sl = open(src_path, encoding="utf-8").read().splitlines()
    tl = open(tr_path, encoding="utf-8").read().splitlines()

    src_labels = tuple(
        labels.source_bullet(code, root=root) for code in ("cn", *translation_langs(root))
    )

    def body(lines):
        return [
            ln
            for ln in lines
            if not any(ln.startswith(s) for s in src_labels) and "成本标签" not in ln
        ]

    fails, warns = [], []
    fail_objs, warn_objs = [], []

    def add_fail(msg, obj):
        fails.append(msg)
        fail_objs.append(obj)

    def add_warn(msg, obj):
        warns.append(msg)
        warn_objs.append(obj)

    sh = [x for x in sl if x.startswith("### ")]
    th = [x for x in tl if x.startswith("### ")]
    if len(sh) != len(th):
        add_fail(
            f"headings {len(sh)} != {len(th)}",
            {"kind": "headings_mismatch", "got": len(th), "want": len(sh)},
        )

    st = sum(1 for x in sl if "成本标签" in x)
    tt = sum(1 for x in tl if "成本标签" in x)
    if st != tt:
        add_fail(
            f"cost tags {st} != {tt}",
            {"kind": "cost_tags_mismatch", "got": tt, "want": st},
        )

    src_cn = labels.source_bullet("cn", root=root)
    src_tr = labels.source_bullet(lang, root=root)
    ss = [x.split("：", 1)[1].strip() for x in sl if x.startswith(src_cn)]
    ts = [x.split(":", 1)[1].strip() for x in tl if x.startswith(src_tr)]
    retrofit = re.compile(r"\s*\[(?:рус\.|eng\.)\s*[«\"](?:[^«»\"]|[«\"][^»\"]*[»\"])*[»\"]\]")
    ss = [retrofit.sub("", x) for x in ss]
    ts = [retrofit.sub("", x) for x in ts]
    if len(ss) != len(ts):
        add_fail(
            f"sources {len(ss)} != {len(ts)}",
            {"kind": "sources_mismatch", "got": len(ts), "want": len(ss)},
        )
    else:
        for a, b in zip(ss, ts, strict=True):
            if a != b:
                add_fail(
                    "source line mismatch: " + a[:60],
                    {"kind": "source_line_mismatch", "preview": a[:60]},
                )

    cn_body = body(sl)
    tr_body = body(tl)
    item_labels = {
        "cn": labels.field_labels("cn", root=root),
        lang: labels.field_labels(lang, root=root),
    }
    banned = labels.banned_calques(lang, root=root)
    if not banned:
        print(
            f"  (note: no banned_calques configured for lang={lang} — "
            f"calque check is a no-op for this run)",
            file=sys.stderr,
        )
    for i, cn_lab in enumerate(item_labels["cn"]):
        want = sum(1 for x in cn_body if x.lstrip().startswith("- " + cn_lab))
        got = sum(1 for x in tr_body if x.lstrip().startswith("- " + item_labels[lang][i]))
        if want != got:
            add_fail(
                f'field {item_labels[lang][i]}: {got} != {want} ("- {cn_lab}")',
                {
                    "kind": "field_count",
                    "label": item_labels[lang][i],
                    "got": got,
                    "want": want,
                    "cn_label": cn_lab,
                },
            )

    plain = item_labels[lang][1]
    for idx, ln in enumerate(tl, 1):
        if ln.lstrip().startswith("- " + plain):
            hits = re.findall(r"\b(?:HR|RR|OR|CI)\b", ln)
            if hits:
                add_warn(
                    f"line {idx}: jargon in '{plain}' line: {', '.join(sorted(set(hits)))}",
                    {
                        "kind": "jargon_in_plain",
                        "line": idx,
                        "hits": sorted(set(hits)),
                    },
                )

    cn_nums = norm_numbers("\n".join(cn_body))
    tr_nums = norm_numbers("\n".join(tr_body), ru=(lang == "ru"), es=(lang == "es"))
    from collections import Counter

    missing = Counter(cn_nums) - Counter(tr_nums)
    extra = Counter(tr_nums) - Counter(cn_nums)
    lost_hard = {v: c for v, c in missing.items() if v not in tr_nums}
    lost_soft = {v: c for v, c in missing.items() if v in tr_nums}
    if lost_soft:
        top = ", ".join(f"{v}×{c}" for v, c in sorted(lost_soft.items(), key=lambda x: -x[1])[:10])
        warns.append(f"numbers less frequent (prose economy, check): {top}")
        for v, c in lost_soft.items():
            warn_objs.append({"kind": "number_less_frequent", "value": str(v), "count": int(c)})
    if lost_hard:
        top = ", ".join(f"{v}×{c}" for v, c in sorted(lost_hard.items(), key=lambda x: -x[1])[:12])
        fails.append(f"numbers absent from translation: {top}")
        for v, c in lost_hard.items():
            fail_objs.append({"kind": "number_absent", "value": str(v), "count": int(c)})
    if extra:
        top = ", ".join(f"{v}×{c}" for v, c in extra.most_common(12))
        warns.append(f"numbers added (check they are marked inserts): {top}")
        for v, c in extra.items():
            warn_objs.append({"kind": "number_added", "value": str(v), "count": int(c)})

    zh_lines = []
    in_note = False
    for idx, ln in enumerate(tl, 1):
        if ln.startswith(
            ("> Примечание переводчика", "> Translator's note", "> Nota del traductor")
        ):
            in_note = True
        elif not ln.startswith(">"):
            in_note = False
        if idx <= 4 or in_note or ln.startswith(src_tr) or "成本标签" in ln:
            continue
        s = re.sub(r"\[[^\]]*\]\([^)]*\)", "[]( )", ln)
        s = re.sub(r"\([^)]*[\u4e00-\u9fff][^)]*\)", "(gloss)", s)
        s = re.sub(r"[«\"「][^»\"」]*[»\"」]", "«»", s)
        if CJK.search(s):
            zh_lines.append((idx, ln.strip()[:70]))
        elif FULLWIDTH.search(s):
            add_warn(
                f"line {idx}: fullwidth punctuation: {ln.strip()[:60]}",
                {"kind": "fullwidth", "line": idx},
            )
    if zh_lines:
        add_fail(
            f"CJK outside allowed zones: {len(zh_lines)} line(s), "
            + "; ".join(f"L{i}:{t}" for i, t in zh_lines[:5]),
            {
                "kind": "cjk_outside",
                "count": len(zh_lines),
                "samples": [{"line": i, "text": t} for i, t in zh_lines[:5]],
            },
        )

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

    print(f"verify {os.path.basename(tr_path)} vs {os.path.basename(src_path)}")
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
    if fails:
        print("FAIL")
        for f in fails:
            print("  -", f)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    if fails:
        sys.exit(1)
    print(
        f"OK: headings={len(th)} tags={tt} sources={len(ts)} "
        f"numbers={len(cn_nums)} (lost=0, extra={sum(extra.values())})"
    )
    os.makedirs(os.path.join(root, "translate", ".status"), exist_ok=True)
    if explicit_file:
        print("stamp skipped (--file mode)")
        return
    mark = os.path.join(root, "translate", ".status", f"{n}-{lang}.ok")
    json.dump(
        {
            "chapter": n,
            "lang": lang,
            "file": os.path.basename(tr_path),
            "ts": time.time(),
            "nums": len(cn_nums),
        },
        open(mark, "w", encoding="utf-8"),
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
