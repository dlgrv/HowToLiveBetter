#!/usr/bin/env python3
import glob
import json
import os
import re
import sys
import time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r"[\u4e00-\u9fff]")
RUNS = os.path.join(root, "tools", "runs")


def chapter_nums(argv):
    have = sorted(
        {
            f[:2]
            for f in os.listdir(os.path.join(root, "book"))
            if re.match(r"\d\d-", f) and f.endswith(".md")
        }
    )
    return have if not argv else [n for n in argv if n in have]


def verify_stamp(n, lang):
    mark = os.path.join(root, "tools", ".status", f"{n}-{lang}.ok")
    if not os.path.exists(mark):
        return "—", None
    files = glob.glob(os.path.join(root, "book", lang, f"{n}-*.md"))
    if not files:
        return "?", None
    d = json.load(open(mark, encoding="utf-8"))
    fresh = os.path.getmtime(files[0]) <= os.path.getmtime(mark)
    return ("OK" if fresh else "изм."), d.get("ts")


def unit_progress(units_dir):
    if not os.path.isdir(units_dir):
        return None
    units = [f for f in glob.glob(os.path.join(units_dir, "[0-9][0-9].md"))]
    if not units:
        return None
    done = sum(
        1
        for f in units
        if not CJK.search(open(f, encoding="utf-8").readline())
    )
    return done, len(units)


def run_units_dir(n, lang="ru"):
    preferred = os.path.join(RUNS, "active", lang, n, "units")
    if os.path.isdir(preferred):
        return preferred
    if not os.path.isdir(RUNS):
        return preferred
    matches = sorted(
        glob.glob(os.path.join(RUNS, "*", lang, n, "units"))
    )
    return matches[-1] if matches else preferred


def pass_columns(n, lang):
    states = {}
    fc_path = os.path.join(
        root, "tools", "validate", "results", "factcheck", f"{n}-{lang}.json"
    )
    if os.path.exists(fc_path):
        try:
            d = json.load(open(fc_path, encoding="utf-8"))
            g = d.get("gate") or "pass"
            states["fc"] = g.upper() if g not in ("pass",) else "ok"
        except (ValueError, OSError):
            states["fc"] = "?"
    else:
        states["fc"] = "SKIP"
    states["style"] = "SKIP"
    qe_path = os.path.join(root, "tools", ".qe", f"{n}-{lang}.json")
    states["qe"] = "ok" if os.path.exists(qe_path) else "SKIP"
    pl_path = os.path.join(
        root, "tools", "validate", "results", "plainness", f"{n}-{lang}.json"
    )
    if os.path.exists(pl_path):
        try:
            d = json.load(open(pl_path, encoding="utf-8"))
            w = sum(len(u["warns"]) for u in d.get("units", []))
            states["plain"] = "ok" if w == 0 else f"W{w}"
        except (ValueError, OSError, KeyError, TypeError):
            states["plain"] = "?"
    else:
        states["plain"] = "SKIP"
    return states


def main():
    nums = chapter_nums(sys.argv[1:])
    rows = []
    for n in nums:
        cn = len(glob.glob(os.path.join(root, "book", f"{n}-*.md")))
        row = {"n": n, "cn": cn}
        for lang in ("ru", "en"):
            f = glob.glob(os.path.join(root, "book", lang, f"{n}-*.md"))
            stamp, ts = verify_stamp(n, lang)
            row[lang] = (os.path.basename(f[0]) if f else "—", stamp, ts)
            row[lang + "-passes"] = pass_columns(n, lang)
        row["run"] = unit_progress(run_units_dir(n, "ru"))
        rows.append(row)

    print(
        f"{'ch':<4}{'items':<7}{'RU':<34}{'EN':<34}{'workdir':<12}"
        f"{'RU passes':<34}{'EN passes':<34}"
    )
    for r in rows:

        def cell(lang):
            name, stamp, ts = r[lang]
            if name == "—":
                return "—"
            day = time.strftime("%m-%d", time.localtime(ts)) if ts else "?"
            return f"{name[:24]} {stamp}({day})"

        w = f"{r['run'][0]}/{r['run'][1]}" if r["run"] else "—"

        def passes(lang):
            p = r[lang + "-passes"]
            return f"fc:{p['fc']} sty:{p['style']} qe:{p['qe']} pl:{p['plain']}"

        print(
            f"{r['n']:<4}{r['cn']:<7}{cell('ru'):<34}{cell('en'):<34}{w:<12}"
            f"{passes('ru'):<34}{passes('en'):<34}"
        )

    ru_ok = sum(1 for r in rows if r["ru"][0] != "—")
    en_ok = sum(1 for r in rows if r["en"][0] != "—")
    stale = sum(
        1 for r in rows if r["ru"][1] == "изм." or r["en"][1] == "изм."
    )
    active = [
        (r["n"], r["run"])
        for r in rows
        if r["run"] and r["run"][0] < r["run"][1]
    ]
    print(
        f"\nRU: {ru_ok}/{len(rows)} файлов | EN: {en_ok}/{len(rows)} | "
        f"протухших verify-маркеров: {stale}"
    )
    if active:
        print(
            "активные волны: "
            + ", ".join(f"ch{n} {d}/{t}" for n, (d, t) in active)
        )


if __name__ == "__main__":
    main()
