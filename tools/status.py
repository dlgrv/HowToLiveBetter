#!/usr/bin/env python3
"""Wave dashboard: per-chapter translation pipeline status in one shot.

Usage:
  python3 tools/status.py            # all chapters 01..31
  python3 tools/status.py 11 12 13   # subset

Shows, per chapter: item count, RU/EN file presence, verify stamp
(fresh = OK, stale = file changed after last verify), and unit progress
for active workdirs under /root/htlb-run/ (a unit counts as translated when
its ### title line no longer contains CJK).
"""
import glob, json, os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r"[\u4e00-\u9fff]")


def chapter_nums(argv):
    have = sorted({f[:2] for f in os.listdir(os.path.join(root, "book"))
                   if re.match(r"\d\d-", f) and f.endswith(".md")})
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
    done = sum(1 for f in units
               if not CJK.search(open(f, encoding="utf-8").readline()))
    return done, len(units)


def pass_columns(n, lang):
    """Quality-pipeline pass states for one chapter-language (plan Task 10).

    Order fixed by plan: verify -> factcheck (E) -> style (A) -> QE -> judge.
    Any not-yet-run pass shows SKIPPED explicitly (never silently absent).
    """
    states = {}
    # factcheck verdicts live in tools/validate/results/factcheck/<n>-<lang>.json
    fc_path = os.path.join(root, "tools", "validate", "results", "factcheck",
                           f"{n}-{lang}.json")
    if os.path.exists(fc_path):
        try:
            d = json.load(open(fc_path, encoding="utf-8"))
            g = (d.get("gate") or
                 ("fail" if d.get("grounding", {}).get("dropped") else "pass"))
            states["fc"] = g.upper() if g != "pass" else "ok"
        except (ValueError, OSError):
            states["fc"] = "?"
    else:
        states["fc"] = "SKIP"
    # style warnings are advisory (WARN-only, style_check.py)
    states["style"] = "SKIP"  # filled by wave runner after style_check pass
    # QE deltas require the Mac venv; absent cache -> SKIPPED
    qe_path = os.path.join(root, "tools", ".qe", f"{n}-{lang}.json")
    states["qe"] = "ok" if os.path.exists(qe_path) else "SKIP"
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
        row["run"] = unit_progress(f"/root/htlb-run/{n}/units")
        rows.append(row)

    print(f"{'ch':<4}{'items':<7}{'RU':<34}{'EN':<34}{'workdir':<12}"
          f"{'RU passes':<28}{'EN passes':<28}")
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
            return f"fc:{p['fc']} sty:{p['style']} qe:{p['qe']}"
        print(f"{r['n']:<4}{r['cn']:<7}{cell('ru'):<34}{cell('en'):<34}{w:<12}"
              f"{passes('ru'):<28}{passes('en'):<28}")

    ru_ok = sum(1 for r in rows if r["ru"][0] != "—")
    en_ok = sum(1 for r in rows if r["en"][0] != "—")
    stale = sum(1 for r in rows if r["ru"][1] == "изм." or r["en"][1] == "изм.")
    active = [(r["n"], r["run"]) for r in rows if r["run"] and r["run"][0] < r["run"][1]]
    print(f"\nRU: {ru_ok}/{len(rows)} файлов | EN: {en_ok}/{len(rows)} | "
          f"протухших verify-маркеров: {stale}")
    if active:
        print("активные волны: " + ", ".join(f"ch{n} {d}/{t}" for n, (d, t) in active))


if __name__ == "__main__":
    import time
    main()
