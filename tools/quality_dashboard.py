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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd):
    """Run a command, return (returncode, stdout)."""
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                       cwd=ROOT, shell=True,
                       env={**os.environ, "PATH": f"{ROOT}/.venv/bin:{os.environ['PATH']}"})
    return r.returncode, (r.stdout + r.stderr)


def count_chapters(lang_dir):
    d = os.path.join(ROOT, lang_dir)
    if not os.path.isdir(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith(".md")])


def main():
    langs = ["ru", "en", "es"]

    rows = []
    issues = 0

    for lang in langs:
        lang_dir = f"book/{lang}"
        n_ch = count_chapters(lang_dir)

        # readability
        rc, out = run(f"python3 tools/readability.py {lang} --json")
        readability = {"score": "N/A", "below_target": 0}
        if rc == 0 and out.strip():
            try:
                data = json.loads(out)
                scores = [r["score"] for r in data if "score" in r]
                if scores:
                    readability["score"] = f"{sum(scores)/len(scores):.0f}"
                    readability["below_target"] = sum(1 for s in scores if s < 60)
            except json.JSONDecodeError:
                pass
        if readability["below_target"] > 0:
            issues += 1

        # bureaucratese
        rc, out = run(f"python3 tools/bureaucratese.py {lang} --json")
        bur_hits = 0
        if out.strip():
            try:
                data = json.loads(out)
                bur_hits = sum(len(v) for v in data.values())
            except json.JSONDecodeError:
                if rc != 0:
                    bur_hits = 1  # parse failed but tool found issues
        if bur_hits > 0:
            issues += 1

        # OG previews
        og_dir = os.path.join(ROOT, "og", lang)
        og_ok = n_ch
        og_missing = 0
        if os.path.isdir(og_dir):
            og_missing = n_ch - len([f for f in os.listdir(og_dir)
                                     if f.endswith(".png")])
            og_ok = n_ch - og_missing

        # README files
        readme_files = {
            "ru": "README.ru.md",
            "en": "README.md",
            "es": "README.es.md",
        }
        rm_file = readme_files.get(lang, f"README.{lang}.md")
        rm_path = os.path.join(ROOT, rm_file)
        rm_ok = "OK" if os.path.isfile(rm_path) else "MISSING"
        if rm_ok == "MISSING":
            issues += 1

        rows.append({
            "lang": lang.upper(),
            "chapters": n_ch,
            "readability": f"{readability['score']}",
            "below60": readability["below_target"],
            "bureaucratese": bur_hits,
            "og": f"{og_ok}/{n_ch}",
            "readme": rm_ok,
        })

    # Print table
    header = f"{'Lang':>6} {'Ch':>3} {'Read':>5} {'<60':>4} {'Bur':>5} {'OG':>8} {'README':>8}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in rows:
        bur_flag = f"⚠{r['bureaucratese']}" if r["bureaucratese"] > 100 else str(r["bureaucratese"])
        readme_flag = f"⚠ {r['readme']}" if r["readme"] != "OK" else r["readme"]
        print(f"{r['lang']:>6} {r['chapters']:>3} {r['readability']:>5} "
              f"{r['below60']:>4} {bur_flag:>5} {r['og']:>8} {readme_flag:>8}")
    print(sep)

    # Summarize
    total_ch = sum(r["chapters"] for r in rows)
    total_below = sum(r["below60"] for r in rows)
    print(f"\n{total_ch} chapters × {len(langs)} languages")
    print(f"Readability target (≥60): {total_ch * len(langs) - total_below}/{total_ch * len(langs)} pass "
          f"({total_below} below)")

    # Test check
    rc, out = run("python3 -m pytest tools/validate/tests/ tools/llm/tests/ --tb=no -q")
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
        # Extract failure summary
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