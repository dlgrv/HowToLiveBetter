#!/usr/bin/env python3
"""Quality dashboard — single view of all pipeline metrics.

North Star: перевод безумно понятным для носителя.
Prints a table with readability, bureaucratese, chapter parity,
OG preview coverage, and test status for each language.
"""

import json
import os
import subprocess
import sys

from tools.pipeline.config import default_root, load_langs, translation_langs

ROOT = default_root()


def run(argv):
    """Run argv with this interpreter; return (returncode, stdout+stderr)."""
    r = subprocess.run(
        [sys.executable, *argv],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=ROOT,
        check=False,
        env={**os.environ, "PYTHONPATH": ROOT},
    )
    return r.returncode, (r.stdout + r.stderr)


def count_chapters(lang_dir):
    d = os.path.join(ROOT, lang_dir)
    if not os.path.isdir(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith(".md")])


def main():
    langs = translation_langs(ROOT)

    rows = []
    issues = 0

    for lang in langs:
        lang_dir = f"book/{lang}"
        n_ch = count_chapters(lang_dir)

        rc, out = run(["tools/readability.py", lang, "--json"])
        readability = {"score": "N/A", "below_target": 0}
        if rc == 0 and out.strip():
            try:
                data = json.loads(out)
                scores = [r["score"] for r in data if "score" in r]
                if scores:
                    readability["score"] = f"{sum(scores) / len(scores):.0f}"
                    readability["below_target"] = sum(1 for s in scores if s < 60)
            except json.JSONDecodeError:
                pass
        if readability["below_target"] > 0:
            issues += 1

        rc, out = run(["tools/bureaucratese.py", lang, "--json"])
        bur_hits = 0
        if out.strip():
            try:
                data = json.loads(out)
                bur_hits = sum(len(v) for v in data.values())
            except json.JSONDecodeError:
                if rc != 0:
                    bur_hits = 1
        if bur_hits > 0:
            issues += 1

        # One OG preview per language: authored HTML + rendered PNG.
        og_html = os.path.join(ROOT, "tools", "og", f"{lang}.html")
        og_png = os.path.join(ROOT, "site", "assets", "og", f"{lang}.png")
        og_have = [
            name for name, path in (("html", og_html), ("png", og_png)) if os.path.isfile(path)
        ]
        og_status = "OK" if len(og_have) == 2 else ("+".join(og_have) or "MISSING")
        if og_status != "OK":
            issues += 1

        rm_file = next(
            (e["readme"] for e in load_langs(ROOT) if e.get("code") == lang),
            f"README.{lang}.md",
        )
        rm_path = os.path.join(ROOT, rm_file)
        rm_ok = "OK" if os.path.isfile(rm_path) else "MISSING"
        if rm_ok == "MISSING":
            issues += 1

        rows.append(
            {
                "lang": lang.upper(),
                "chapters": n_ch,
                "readability": f"{readability['score']}",
                "below60": readability["below_target"],
                "bureaucratese": bur_hits,
                "og": og_status,
                "readme": rm_ok,
            }
        )

    header = f"{'Lang':>6} {'Ch':>3} {'Read':>5} {'<60':>4} {'Bur':>5} {'OG':>8} {'README':>8}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in rows:
        bur_flag = f"⚠{r['bureaucratese']}" if r["bureaucratese"] > 100 else str(r["bureaucratese"])
        readme_flag = f"⚠ {r['readme']}" if r["readme"] != "OK" else r["readme"]
        og_flag = f"⚠ {r['og']}" if r["og"] != "OK" else r["og"]
        print(
            f"{r['lang']:>6} {r['chapters']:>3} {r['readability']:>5} "
            f"{r['below60']:>4} {bur_flag:>5} {og_flag:>8} {readme_flag:>8}"
        )
    print(sep)

    total_ch = sum(r["chapters"] for r in rows)
    total_below = sum(r["below60"] for r in rows)
    print(f"\n{total_ch} chapters × {len(langs)} languages")
    print(
        f"Readability target (≥60): {total_ch * len(langs) - total_below}/{total_ch * len(langs)} pass "
        f"({total_below} below)"
    )

    rc, out = run(["-m", "pytest", "tools/validate/tests/", "tools/llm/tests/", "--tb=no", "-q"])
    tests_ok = rc == 0
    if tests_ok:
        for line in out.splitlines():
            if "passed" in line and "failed" not in line:
                passed = line.strip()
                break
        else:
            passed = "OK"
        print(f"Tests: {passed}")
    else:
        issues += 1
        for line in out.splitlines():
            if "failed" in line:
                print(f"Tests: {line.strip()}")
                break
        else:
            print("Tests: FAIL")

    if issues == 0:
        print("\n✓ All quality gates pass.")
        sys.exit(0)
    else:
        print(f"\n⚠ {issues} quality gate(s) need attention.")
        sys.exit(1)


if __name__ == "__main__":
    main()
