#!/usr/bin/env python3
"""Assemble a translated chapter from per-unit LLM output + byte-faithful blocks,
then run the full integrity check against the original.

Usage:
  python3 tools/assemble.py <NN> <workdir> <out.md>
  # workdir contains units/NN.md overwritten by the translator (same filenames)
Exits non-zero and prints FAIL lines if anything is off.
"""
import json, os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n, work, out = sys.argv[1], sys.argv[2], sys.argv[3]

meta = json.load(open(os.path.join(root, "tools", "digest", n, "blocks.json"),
                      encoding="utf-8"))
fails = []

parts = [l.rstrip() for l in open(os.path.join(work, "units", "00.md"),
                                  encoding="utf-8").read().splitlines()]
for i in range(1, meta["items"] + 1):
    up = os.path.join(work, "units", f"{i:02d}.md")
    if not os.path.exists(up):
        fails.append(f"unit {i:02d} missing"); continue
    txt = open(up, encoding="utf-8").read()
    tag = meta["blocks"][str(i)]["tag"]
    src = meta["blocks"][str(i)]["src"]
    txt = txt.replace("§TAG§", tag)
    # Russian label + byte-identical content after the label
    src_ru = ["- Источники:" + l.split("：", 1)[1] if l.startswith("- 来源：") else l
              for l in src]
    # In the original, 来源 sits between 证据等级 and 备注 in most items;
    # splice each source line in at the position of its §SRC§ marker only if
    # the marker is the LAST content line; otherwise re-splice to match the
    # original field order (sources right after the grade line, before notes).
    lines = txt.splitlines()
    out_lines, inserted = [], False
    for j, l in enumerate(lines):
        if l.strip() == "§SRC§":
            # find where to insert: after the LAST '- Уровень доказательности'
            # already emitted, before a following '- Примечания' if present
            k = len(out_lines)
            while k > 0 and not out_lines[k-1].startswith("- Уровень доказательности"):
                k -= 1
            if k == 0:
                out_lines.extend(src_ru)
            else:
                rest, note = out_lines[:k], out_lines[k:]
                out_lines = rest + src_ru + note
            inserted = True
        else:
            out_lines.append(l)
    if not inserted:
        fails.append(f"unit {i:02d}: §SRC§ marker not found")
    txt = "\n".join(out_lines)
    if "§" in txt:
        fails.append(f"unit {i:02d}: leftover placeholder")
    parts.extend(txt.rstrip().splitlines())
    # separator: blank line between items exactly where the original has one
    blank = meta.get("blank_before_next", {}).get(str(i), True)
    if i < meta["items"] and blank:
        parts.append("")

open(out, "w", encoding="utf-8").write(
    ("\n".join(parts).rstrip() + "\n").replace("\n\n\n", "\n\n"))

# ---- integrity checks against the original -------------------------------
src = [f for f in os.listdir(os.path.join(root, "book"))
       if re.match(rf"{n}-", f) and f.endswith(".md")][0]
sl = open(os.path.join(root, "book", src), encoding="utf-8").read().splitlines()
tl = open(out, encoding="utf-8").read().splitlines()

si = [x for x in sl if x.startswith("### ")]
ti = [x for x in tl if x.startswith("### ")]
if len(si) != len(ti):
    fails.append(f"items {len(si)} != {len(ti)}")

ss = [x.split("：", 1)[1] for x in sl if x.startswith("- 来源：")]
ts = [x.split(":", 1)[1].strip() for x in tl if re.match(r"^- Источники:", x)]
if len(ss) != len(ts):
    fails.append(f"sources {len(ss)} != {len(ts)}")
else:
    for a, b in zip(ss, ts):
        if a != b:
            fails.append("source line mismatch: " + a[:60])

st = sum(1 for x in sl if "成本标签" in x)
tt = sum(1 for x in tl if "成本标签" in x)
if st != tt:
    fails.append(f"tags {st} != {tt}")

# hanzi allowed only: sources lines, tag lines, status-line link, and any line
# still in the ORIGINAL language (the test path: untranslated units).
# For a real translated chapter the translator-subagent contract says hanzi
# outside these zones = 0; assemble only enforces the mechanical zones.
def hanzi(s): return re.search(r"[\u4e00-\u9fff]", s)
zh_lines_out = 0
for idx, l in enumerate(tl, 1):
    if hanzi(l) and not (l.startswith("- Источники:") or "成本标签" in l
                         or "](../" in l or idx <= 4):
        zh_lines_out += 1

if fails:
    print("FAIL"); [print(" -", f) for f in fails]; sys.exit(1)
note = "" if zh_lines_out == 0 else f" (warning: {zh_lines_out} untranslated lines)"
print(f"OK ch.{n}: items={len(ti)} tags={tt} sources={len(ts)} byte-identical{note}")
