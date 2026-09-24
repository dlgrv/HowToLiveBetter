#!/usr/bin/env python3
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = {"ru": "assemble.py", "en": "assemble_en.py", "es": "assemble_es.py"}
RUNS_ACTIVE = os.path.join(REPO, "tools", "runs", "active")


def fname(lang, nn):
    for f in os.listdir(os.path.join(REPO, "book", lang)):
        if f.startswith(nn + "-"):
            return f
    raise FileNotFoundError(f"{lang}/{nn}")


def workdir(lang, nn):
    return os.path.join(RUNS_ACTIVE, lang, nn)


def main(chapters):
    rows, fails = [], 0
    for nn in chapters:
        for lang in ("ru", "en", "es"):
            bk = fname(lang, nn)
            out = os.path.join(REPO, "book", lang, bk)
            wd = workdir(lang, nn)
            if not os.path.isdir(os.path.join(wd, "units")):
                rows.append((lang, nn, f"ASSEMBLE FAIL: missing {wd}/units"))
                fails += 1
                continue
            r = subprocess.run(
                ["python3", f"tools/{SCRIPTS[lang]}", nn, wd, out],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            asm = (r.stdout.strip().splitlines() or ["ERR: " + r.stderr[-120:]])[-1]
            if not asm.startswith("OK"):
                rows.append((lang, nn, "ASSEMBLE FAIL: " + asm[:70]))
                fails += 1
                continue
            v = subprocess.run(
                [
                    "python3",
                    "tools/verify.py",
                    nn,
                    "--lang",
                    lang,
                    "--file",
                    f"book/{lang}/{bk}",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            ok = any(l.startswith("OK") for l in v.stdout.splitlines())
            detail = next(
                (l for l in v.stdout.splitlines() if l.startswith(("OK", "FAIL"))),
                "",
            )[:60]
            rows.append((lang, nn, detail))
            if not ok:
                fails += 1
    for lang, nn, st in rows:
        print(f"{lang} ch{nn}: {st}")
    print("---")
    print("VERDICT:", "GREEN" if fails == 0 else f"{fails} FAIL(s)")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["02"]))
