#!/usr/bin/env python3
"""Build a translation-READY digest for one chapter.

Splits the Chinese original into per-item work units:
  - translatable text (title/body lines) with §SRC§/§TAG§ placeholders
  - byte-faithful blocks (tag + sources) stored separately, NEVER shown to the LLM

Usage:
  python3 tools/make_digest.py 16          # -> tools/digest/16/units/*.md + blocks.json
"""

import json
import os
import sys

from tools.pipeline.config import default_root, unit_dir
from tools.pipeline.paths import _nn, cn_chapter_path

root = default_root()

n = _nn(sys.argv[1])
try:
    path = cn_chapter_path(root, n)
except FileNotFoundError as e:
    sys.exit(str(e))
lines = open(path, encoding="utf-8").read().splitlines()

head, items, cur = [], [], None
for ln in lines:
    if ln.startswith("### "):
        cur = {"title": ln, "tag": "", "src": [], "body": []}
        items.append(cur)
    elif cur is None:
        head.append(ln)
    elif ln.startswith("<!-- 成本标签"):
        cur["tag"] = ln
    elif ln.startswith("- 来源："):
        cur["src"].append(ln)
    else:
        cur["body"].append(ln)

d = os.path.dirname(unit_dir(root, "cn", n))
os.makedirs(os.path.join(d, "units"), exist_ok=True)

open(os.path.join(d, "units", "00.md"), "w", encoding="utf-8").write(
    "\n".join(head).rstrip() + "\n"
)

blocks = {}
for i, it in enumerate(items, 1):
    unit = [it["title"], "§TAG§"] + it["body"] + ["§SRC§", ""]
    open(os.path.join(d, "units", f"{i:02d}.md"), "w", encoding="utf-8").write("\n".join(unit))
    blocks[str(i)] = {"tag": it["tag"], "src": it["src"]}

gloss_path = os.path.join(root, "tools", "glossary.json")
gloss = (
    json.load(open(gloss_path, encoding="utf-8"))
    if os.path.exists(gloss_path)
    else {"terms": [], "style_rules": {}}
)


def gloss_rows(text, only_present=True):
    return [
        f"{t['cn']} → RU: {t.get('ru', '?')} / EN: {t.get('en', '?')}"
        for t in gloss.get("terms", [])
        if not only_present or t["cn"] in text
    ]


for i in range(len(items) + 1):
    if i == 0:
        chapter_text = (
            "\n".join(head) + "\n" + "\n".join(it["title"] + "\n".join(it["body"]) for it in items)
        )
        rows = gloss_rows(chapter_text, only_present=False)
    else:
        it = items[i - 1]
        rows = gloss_rows(it["title"] + "\n" + "\n".join(it["body"]))
    style = []
    if i == 0:
        for lang in ("ru", "en"):
            style += [
                f"[STYLE {lang.upper()}] " + r for r in gloss.get("style_rules", {}).get(lang, [])
            ]
    if rows or style:
        g = [
            "[СПРАВКА — НЕ переводить этот блок и НЕ вставлять в текст юнита.",
            " Используй закреплённые эквиваленты; глосс (иероглифы — пояснение) —",
            " при ПЕРВОМ употреблении термина в файле]",
            "",
        ]
        g += rows
        if style:
            g += ["", *style]
        open(os.path.join(d, "units", f"{i:02d}.gloss.md"), "w", encoding="utf-8").write(
            "\n".join(g) + "\n"
        )

json.dump(
    {
        "chapter": n,
        "file": os.path.basename(path),
        "head": head,
        "items": len(items),
        "blocks": blocks,
    },
    open(os.path.join(d, "blocks.json"), "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)
print(f"ch.{n}: {len(items)} units -> tools/digest/{n}/units/, blocks.json")
