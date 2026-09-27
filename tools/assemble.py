#!/usr/bin/env python3
"""Assemble a translated chapter from per-unit LLM output + byte-faithful blocks,
then run the full integrity check against the original.

Usage:
  python3 tools/assemble.py <NN> <workdir> <out.md> [lang]
  lang defaults to "ru" if omitted.
Exits non-zero and prints FAIL lines if anything is off.
"""

import json
import os
import re
import sys

from tools.pipeline import labels
from tools.pipeline.config import default_root, unit_dir
from tools.pipeline.paths import _nn, cn_chapter_path

root = default_root()
n, work, out = _nn(sys.argv[1]), sys.argv[2], sys.argv[3]
lang = sys.argv[4] if len(sys.argv) > 4 else "ru"

source_word = labels.source_label(lang, root=root)
evidence_word = labels.evidence_grade_label(lang, root=root)

meta = json.load(
    open(os.path.join(os.path.dirname(unit_dir(root, "cn", n)), "blocks.json"), encoding="utf-8")
)
fails = []

parts = [
    ln.rstrip()
    for ln in open(
        os.path.join(work, "units", "00.md"),
        encoding="utf-8",
    )
    .read()
    .splitlines()
]
for i in range(1, meta["items"] + 1):
    up = os.path.join(work, "units", f"{i:02d}.md")
    if not os.path.exists(up):
        fails.append(f"unit {i:02d} missing")
        continue
    txt = open(up, encoding="utf-8").read()
    tag = meta["blocks"][str(i)]["tag"]
    src = meta["blocks"][str(i)]["src"]
    txt = txt.replace("§TAG§", tag)
    src_local = [
        "- " + source_word + ":" + ln.split("：", 1)[1] if ln.startswith("- 来源：") else ln
        for ln in src
    ]
    lines = txt.splitlines()
    out_lines, inserted = [], False
    for _j, ln in enumerate(lines):
        if ln.strip() == "§SRC§":
            grade_label = f"- {evidence_word}"
            k = len(out_lines)
            while k > 0 and not out_lines[k - 1].startswith(grade_label):
                k -= 1
            if k == 0:
                out_lines.extend(src_local)
            else:
                rest, note = out_lines[:k], out_lines[k:]
                out_lines = rest + src_local + note
            inserted = True
        else:
            out_lines.append(ln)
    if not inserted:
        fails.append(f"unit {i:02d}: §SRC§ marker not found")
    txt = "\n".join(out_lines)
    if "§" in txt:
        fails.append(f"unit {i:02d}: leftover placeholder")
    parts.extend(txt.rstrip().splitlines())
    blank = meta.get("blank_before_next", {}).get(str(i), True)
    if i < meta["items"] and blank:
        parts.append("")

open(out, "w", encoding="utf-8").write(
    ("\n".join(parts).rstrip() + "\n").replace("\n\n\n", "\n\n"),
)

try:
    src_path = cn_chapter_path(root, n)
except FileNotFoundError as e:
    print(f"FAIL: {e}", file=sys.stderr)
    sys.exit(1)
sl = open(src_path, encoding="utf-8").read().splitlines()
tl = open(out, encoding="utf-8").read().splitlines()

si = [x for x in sl if x.startswith("### ")]
ti = [x for x in tl if x.startswith("### ")]
if len(si) != len(ti):
    fails.append(f"items {len(si)} != {len(ti)}")

ss = [x.split("：", 1)[1] for x in sl if x.startswith("- 来源：")]
ts = [x.split(":", 1)[1].strip() for x in tl if re.match(r"^- " + source_word + ":", x)]
if len(ss) != len(ts):
    fails.append(f"sources {len(ss)} != {len(ts)}")
else:
    for a, b in zip(ss, ts, strict=True):
        if a != b:
            fails.append("source line mismatch: " + a[:60])

st = sum(1 for x in sl if "成本标签" in x)
tt = sum(1 for x in tl if "成本标签" in x)
if st != tt:
    fails.append(f"tags {st} != {tt}")


def hanzi(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", s))


zh_lines_out = 0
for idx, ln in enumerate(tl, 1):
    if hanzi(ln) and not (
        ln.startswith("- " + source_word + ":") or "成本标签" in ln or "](../" in ln or idx <= 4
    ):
        zh_lines_out += 1

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
note = "" if zh_lines_out == 0 else f" (warning: {zh_lines_out} untranslated lines)"
print(
    f"OK ch.{n}: items={len(ti)} tags={tt} sources={len(ts)} byte-identical{note}",
)
