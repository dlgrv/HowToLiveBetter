#!/usr/bin/env python3
"""Build a translation-READY digest for one chapter.

Splits the Chinese original into per-item work units:
  - translatable text (title/body lines) with §SRC§/§TAG§ placeholders
  - byte-faithful blocks (tag + sources) stored separately, NEVER shown to the LLM

Usage:
  python3 tools/make_digest.py 16          # -> tools/digest/16/units/*.md + blocks.json
"""
import json, os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = sys.argv[1]
srcs = [f for f in os.listdir(os.path.join(root, "book"))
        if re.match(rf"{n}-", f) and f.endswith(".md")]
if not srcs:
    sys.exit(f"chapter {n} not found")
path = os.path.join(root, "book", srcs[0])
lines = open(path, encoding="utf-8").read().splitlines()

head, items, cur = [], [], None
for l in lines:
    if l.startswith("### "):
        cur = {"title": l, "tag": "", "src": [], "body": []}
        items.append(cur)
    elif cur is None:
        head.append(l)
    elif l.startswith("<!-- 成本标签"):
        cur["tag"] = l
    elif l.startswith("- 来源："):
        cur["src"].append(l)
    else:
        cur["body"].append(l)

d = os.path.join(root, "tools", "digest", n)
os.makedirs(os.path.join(d, "units"), exist_ok=True)

# unit 00 = chapter head (status line + title + intro) — translatable,
# with the original-file link that must survive byte-identical
open(os.path.join(d, "units", "00.md"), "w", encoding="utf-8").write(
    "\n".join(head).rstrip() + "\n")

blocks = {}   # unit -> faithful lines, injected by assemble.py verbatim
for i, it in enumerate(items, 1):
    # unit file: only what the LLM translates; placeholders mark faithful zones
    unit = [it["title"], "§TAG§"] + it["body"] + ["§SRC§", ""]
    open(os.path.join(d, "units", f"{i:02d}.md"), "w", encoding="utf-8").write(
        "\n".join(unit))
    blocks[str(i)] = {"tag": it["tag"], "src": it["src"]}

# Per-unit terminology injection: units/NN.gloss.md contains ONLY the glossary
# terms occurring in this unit (00 gets the chapter-wide union + style rules).
# assemble.py reads only NN.md, so gloss files never leak into the book; they
# are copied together with units and pasted into the translator-subagent task.
gloss_path = os.path.join(root, "tools", "glossary.json")
gloss = json.load(open(gloss_path, encoding="utf-8")) if os.path.exists(gloss_path) \
    else {"terms": [], "style_rules": {}}

def gloss_rows(text, only_present=True):
    rows = []
    for t in gloss.get("terms", []):
        if not only_present or t["cn"] in text:
            rows.append(f'{t["cn"]} → RU: {t.get("ru", "?")} / EN: {t.get("en", "?")}')
    return rows

for i in range(len(items) + 1):
    if i == 0:
        chapter_text = "\n".join(head) + "\n" + "\n".join(
            it["title"] + "\n".join(it["body"]) for it in items)
        rows = gloss_rows(chapter_text, only_present=False)
    else:
        it = items[i - 1]
        rows = gloss_rows(it["title"] + "\n" + "\n".join(it["body"]))
    style = []
    if i == 0:  # style rules once, in the chapter-overview unit
        for lang in ("ru", "en"):
            style += [f"[STYLE {lang.upper()}] " + r
                      for r in gloss.get("style_rules", {}).get(lang, [])]
    if rows or style:
        g = ["[СПРАВКА — НЕ переводить этот блок и НЕ вставлять в текст юнита.",
             " Используй закреплённые эквиваленты; глосс (иероглифы — пояснение) —",
             " при ПЕРВОМ употреблении термина в файле]",
             ""]
        g += rows
        if style:
            g += [""] + style
        open(os.path.join(d, "units", f"{i:02d}.gloss.md"), "w", encoding="utf-8").write(
            "\n".join(g) + "\n")

json.dump({"chapter": n, "file": srcs[0], "head": head,
           "items": len(items), "blocks": blocks},
          open(os.path.join(d, "blocks.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"ch.{n}: {len(items)} units -> tools/digest/{n}/units/, blocks.json")
