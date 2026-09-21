#!/usr/bin/env python3
"""Render a golden markup session as HTML with neutral diff highlighting.

Differing words get the SAME neutral highlight in both variants: the goal is
to show *where* the variants differ, never *which one is better* — the human
marker must stay blind to the key. Identical (decoy) pairs render with no
marks at all, which the marker is told to expect.

Usage:
  python3 tools/validate/render_markup.py \
      --subset tools/validate/results/golden_lite_subset.json \
      --out /root/htlb-markup-lite.html [--title "..."]
"""
import argparse
import html
import json
import os
import sys
from difflib import SequenceMatcher

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

LINE_RATIO_FLOOR = 0.3  # below this a line pair is marked wholesale (too noisy)


def _words(line):
    return line.split()


def _esc(s):
    return html.escape(s, quote=False)


def diff_words(l1, l2):
    """One line pair -> (html1, html2) with <mark> on differing words."""
    w1, w2 = _words(l1), _words(l2)
    sm = SequenceMatcher(None, w1, w2, autojunk=False)
    if sm.ratio() < LINE_RATIO_FLOOR:
        return f"<mark>{_esc(l1)}</mark>", f"<mark>{_esc(l2)}</mark>"
    out1, out2 = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        s1, s2 = " ".join(w1[i1:i2]), " ".join(w2[j1:j2])
        if op == "equal":
            if s1:
                out1.append(_esc(s1))
            if s2:
                out2.append(_esc(s2))
        else:
            if s1:
                out1.append(f"<mark>{_esc(s1)}</mark>")
            if s2:
                out2.append(f"<mark>{_esc(s2)}</mark>")
    return " ".join(out1), " ".join(out2)


def diff_texts(t1, t2):
    """Whole texts -> (html1, html2); line structure preserved."""
    lines1, lines2 = t1.split("\n"), t2.split("\n")
    sm = SequenceMatcher(None, lines1, lines2, autojunk=False)
    out1, out2 = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for ln in lines1[i1:i2]:
                out1.append(_esc(ln))
            for ln in lines2[j1:j2]:
                out2.append(_esc(ln))
        elif op == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                h1, h2 = diff_words(lines1[i1 + k], lines2[j1 + k])
                out1.append(h1)
                out2.append(h2)
            for ln in lines1[i1 + n:i2]:
                out1.append(f"<mark>{_esc(ln)}</mark>")
            for ln in lines2[j1 + n:j2]:
                out2.append(f"<mark>{_esc(ln)}</mark>")
        elif op == "delete":
            for ln in lines1[i1:i2]:
                out1.append(f"<mark>{_esc(ln)}</mark>")
        elif op == "insert":
            for ln in lines2[j1:j2]:
                out2.append(f"<mark>{_esc(ln)}</mark>")
    return "\n".join(out1), "\n".join(out2)


def diff_line_pairs(t1, t2):
    """Return [(html1|None, html2|None), ...] for differing lines only.

    Aligned line pairs from replace ops go through diff_words (marks on the
    changed words); pure insert/delete get a whole-line mark on one side and
    None on the other (rendered as an em-dash).
    """
    lines1, lines2 = t1.split("\n"), t2.split("\n")
    sm = SequenceMatcher(None, lines1, lines2, autojunk=False)
    pairs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        if op == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                l1 = lines1[i1 + k] if i1 + k < i2 else None
                l2 = lines2[j1 + k] if j1 + k < j2 else None
                if l1 is not None and l2 is not None:
                    pairs.append(diff_words(l1, l2))
                else:
                    pairs.append((f"<mark>{_esc(l1)}</mark>" if l1 else None,
                                  f"<mark>{_esc(l2)}</mark>" if l2 else None))
        elif op == "delete":
            for ln in lines1[i1:i2]:
                pairs.append((f"<mark>{_esc(ln)}</mark>", None))
        elif op == "insert":
            for ln in lines2[j1:j2]:
                pairs.append((None, f"<mark>{_esc(ln)}</mark>"))
    return pairs


def render(pair):
    a, b = pair["variant_a"], pair["variant_b"]
    first, second = (a, b) if pair["show_order"] == "AB" else (b, a)
    d1, d2 = diff_texts(first, second)
    return d1, d2


PAGE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:-apple-system,sans-serif;margin:0 auto;max-width:760px;padding:12px;line-height:1.5;color:#111}}
h2{{position:sticky;top:0;background:#fff;border-bottom:2px solid #333;padding:8px 0;margin:24px 0 12px}}
.pair{{border:1px solid #ddd;border-radius:10px;margin:14px 0;padding:10px}}
h3{{margin:0 0 8px;color:#0a58ca}}
.lab{{font-weight:700;background:#eee;display:inline-block;padding:2px 10px;border-radius:6px;margin-bottom:4px}}
.v2 .lab{{background:#e7f0ff}}
.txt{{white-space:pre-wrap;word-wrap:break-word;font-size:14px;margin:4px 0 0;background:#fafafa;padding:8px;border-radius:8px}}
mark{{background:#fff3bf;padding:0 1px;border-radius:2px}}
nav{{position:sticky;top:0;background:#fff;padding:6px 0;border-bottom:1px solid #ccc;font-size:15px;z-index:2}}
.note{{background:#fff8e1;border:1px solid #f0d060;border-radius:8px;padding:8px 12px;font-size:14px}}
.legend{{font-size:13px;color:#555;margin:8px 0 0}}
</style></head><body>
<nav>Батчи: {navlinks}</nav>
<h1>{title}</h1>
<div class="note"><b>Задача:</b> какой вариант написан <b>естественнее</b>? Цифры и смысл одинаковые — оцени только язык.<br>
<b>Ответ мне в чат:</b> <code>Батч 1: 1 2 = 2 1 1 = 2 1 1</code> — по числу на пару, в порядке пар.<br>
<b>1</b> = естественнее Вариант 1 · <b>2</b> = Вариант 2 · <b>=</b> = равно/одинаковые (пары-близнецы есть — это нормально).<br>
Не думай дольше ~10 секунд.</div>
<p class="legend">Жёлтым выделены фрагменты, которыми варианты различаются (одинаково в обоих).
Нет выделения — варианты идентичны.</p>
{cards}
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Золотой сет ЛАЙТ — 20 пар")
    ap.add_argument("--diff-only", action="store_true",
                    help="show only the differing lines (compact mode)")
    args = ap.parse_args()

    subset = json.load(open(args.subset, encoding="utf-8"))
    manifest = json.load(open(os.path.join(REPO, "tools/validate/results/golden_manifest.json"),
                              encoding="utf-8"))
    by_id = {p["id"]: p for p in manifest["pairs"]}
    pairs = [by_id[pid] for pid in subset["ids"]]

    def pair_card(p, compact):
        a, b = p["variant_a"], p["variant_b"]
        first, second = (a, b) if p["show_order"] == "AB" else (b, a)
        if compact:
            rows = diff_line_pairs(first, second)
            if not rows:  # decoy/identical pair
                rows = [("<i>(варианты идентичны)</i>",
                         "<i>(варианты идентичны)</i>")]
            body1, body2 = [], []
            for h1, h2 in rows:
                body1.append(h1 if h1 is not None else "<i>—</i>")
                body2.append(h2 if h2 is not None else "<i>—</i>")
            d1, d2 = "\n".join(body1), "\n".join(body2)
        else:
            d1, d2 = diff_texts(first, second)
        return f'''<div class="pair">
<h3>{p["id"]}</h3>
<div class="var"><div class="lab">ВАРИАНТ 1</div><div class="txt">{d1}</div></div>
<div class="var v2"><div class="lab">ВАРИАНТ 2</div><div class="txt">{d2}</div></div>
</div>'''

    batches = [pairs[:10], pairs[10:]]
    cards = []
    for bi, batch in enumerate(batches, 1):
        cards.append(f'<h2 id="b{bi}">Батч {bi} из {len(batches)}</h2>')
        for p in batch:
            cards.append(pair_card(p, args.diff_only))
    navlinks = " ".join(f'<a href="#b{i}">{i}</a>' for i in range(1, len(batches) + 1))
    doc = PAGE.format(title=html.escape(args.title), navlinks=navlinks,
                      cards="\n".join(cards))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)
    n_marked = sum(1 for p in pairs if "<mark>" in render(p)[0])
    print(json.dumps({"out": args.out, "pairs": len(pairs),
                      "pairs_with_diff": n_marked,
                      "identical": len(pairs) - n_marked}, ensure_ascii=False))


if __name__ == "__main__":
    main()
