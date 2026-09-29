#!/usr/bin/env python3
import glob
import json
import os
import re
import sys
import time

from translate.lib.config import default_root, unit_dir
from translate.lib.paths import cn_chapter_path, tr_chapter_path

root = default_root()

CJK = re.compile(r"[\u4e00-\u9fff]")


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
    mark = os.path.join(root, "translate", ".status", f"{n}-{lang}.ok")
    if not os.path.exists(mark):
        return "—", None
    try:
        tr_path = tr_chapter_path(root, n, lang)
    except FileNotFoundError:
        return "?", None
    d = json.load(open(mark, encoding="utf-8"))
    fresh = os.path.getmtime(tr_path) <= os.path.getmtime(mark)
    return ("OK" if fresh else "изм."), d.get("ts")


def unit_progress(units_dir):
    if not os.path.isdir(units_dir):
        return None
    units = list(glob.glob(os.path.join(units_dir, "[0-9][0-9].md")))
    if not units:
        return None
    done = sum(1 for f in units if not CJK.search(open(f, encoding="utf-8").readline()))
    return done, len(units)


def main():
    nums = chapter_nums(sys.argv[1:])
    rows = []
    for n in nums:
        try:
            cn_chapter_path(root, n)
            cn = 1
        except FileNotFoundError:
            cn = 0
        row = {"n": n, "cn": cn}
        for lang in ("ru", "en"):
            stamp, ts = verify_stamp(n, lang)
            try:
                tr_name = os.path.basename(tr_chapter_path(root, n, lang))
            except FileNotFoundError:
                tr_name = "—"
            row[lang] = (tr_name, stamp, ts)
        row["run"] = unit_progress(unit_dir(root, "ru", n))
        rows.append(row)

    print(f"{'ch':<4}{'items':<7}{'RU':<34}{'EN':<34}{'workdir':<12}")
    for r in rows:

        def cell(lang, row=r):
            name, stamp, ts = row[lang]
            if name == "—":
                return "—"
            day = time.strftime("%m-%d", time.localtime(ts)) if ts else "?"
            return f"{name[:24]} {stamp}({day})"

        w = f"{r['run'][0]}/{r['run'][1]}" if r["run"] else "—"
        print(f"{r['n']:<4}{r['cn']:<7}{cell('ru'):<34}{cell('en'):<34}{w:<12}")

    ru_ok = sum(1 for r in rows if r["ru"][0] != "—")
    en_ok = sum(1 for r in rows if r["en"][0] != "—")
    stale = sum(1 for r in rows if r["ru"][1] == "изм." or r["en"][1] == "изм.")
    active = [(r["n"], r["run"]) for r in rows if r["run"] and r["run"][0] < r["run"][1]]
    print(
        f"\nRU: {ru_ok}/{len(rows)} файлов | EN: {en_ok}/{len(rows)} | "
        f"протухших verify-маркеров: {stale}"
    )
    if active:
        print("активные волны: " + ", ".join(f"ch{n} {d}/{t}" for n, (d, t) in active))


if __name__ == "__main__":
    main()
