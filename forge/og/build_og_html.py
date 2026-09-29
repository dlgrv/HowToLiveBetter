#!/usr/bin/env python3
"""Render forge/og/{en,ru,es,zh}.html from forge/og/_template.html.

Usage (from repo root):
  python3 forge/og/build_og_html.py
"""

from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "_template.html")

# Shared stats (keep in sync with site badges / README until a stats sync lands).
TIPS_N = "630"
GRADE_A_N = "420"
LINKS_N = "1341"

LATIN_SERIF = 'Georgia,"Times New Roman","Noto Serif",serif'
CJK_SERIF = (
    'Georgia,"Songti SC","STSong",SimSun,"PingFang SC","Microsoft YaHei",'
    '"Noto Serif SC","Source Han Serif SC","Times New Roman",serif'
)

LOCALES = {
    "en": {
        "font_family": LATIN_SERIF,
        "h1_size": "56",
        "brand": "HowToLiveBetter: The Best-Value Life Guide",
        "h1_line1": "Less time, effort, and expense —",
        "h1_line2": "more life, freedom, and money",
        "topics": "Longevity | First aid | Money | Law | Safety net | Family | Skills",
        "tips_label": "tips",
        "grade_a_label": "Grade-A evidence",
        "grade_a_suffix": "",
        "links_label": "primary-source links",
        "filter_label": "Filter by value-for-effort",
    },
    "ru": {
        "font_family": LATIN_SERIF,
        "h1_size": "52",
        "brand": "Гид по жизни с лучшим соотношением цены и результата",
        "h1_line1": "Меньше времени, сил и расходов —",
        "h1_line2": "больше жизни, свободы и денег",
        "topics": "Долголетие | Первая помощь | Деньги | Право | Семья | Навыки",
        "tips_label": "советов",
        "grade_a_label": "Доказательства класса A",
        "grade_a_suffix": "",
        "links_label": "ссылок на первоисточники",
        "filter_label": "Фильтр по выгодности",
    },
    "es": {
        "font_family": LATIN_SERIF,
        "h1_size": "52",
        "brand": "HowToLiveBetter: Guía de la vida al mejor precio",
        "h1_line1": "Menos tiempo, esfuerzo y gasto —",
        "h1_line2": "más vida, libertad y dinero",
        "topics": "Longevidad | Primeros auxilios | Dinero | Leyes | Familia | Habilidades",
        "tips_label": "consejos",
        "grade_a_label": "Evidencia de grado A",
        "grade_a_suffix": "",
        "links_label": "enlaces a fuentes primarias",
        "filter_label": "Filtro por relación valor-precio",
    },
    "zh": {
        "font_family": CJK_SERIF,
        "h1_size": "52",
        "brand": "高性价比人生指南",
        "h1_line1": "用最少的钱、时间和精力，",
        "h1_line2": "换回寿命、金钱和自由",
        "topics": "长寿防病 | 急救 | 省钱理财 | 法律红线 | 失业兜底 | 家庭 | 技能",
        "tips_label": "条建议",
        "grade_a_label": "A 级证据",
        "grade_a_suffix": " 条",
        "links_label": "条原始文献链接",
        "filter_label": "可按性价比筛选",
    },
}


def render(template: str, values: dict[str, str]) -> str:
    out = template

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key not in values:
            raise SystemExit(f"unknown placeholder: {{{{{key}}}}}")
        return values[key]

    out = re.sub(r"\{\{\s*([a-z0-9_]+)\s*\}\}", repl, out)
    leftover = re.findall(r"\{\{[^}]+\}\}", out)
    if leftover:
        raise SystemExit(f"unreplaced placeholders: {leftover}")
    return out


def main() -> None:
    template = open(TEMPLATE, encoding="utf-8").read()
    for code, loc in LOCALES.items():
        values = {
            **loc,
            "tips_n": TIPS_N,
            "grade_a_n": GRADE_A_N,
            "links_n": LINKS_N,
        }
        path = os.path.join(HERE, f"{code}.html")
        open(path, "w", encoding="utf-8").write(render(template, values))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
