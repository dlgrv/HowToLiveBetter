#!/usr/bin/env python3
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.pipeline.paths import active_run_dir, tr_chapter_path  # noqa: E402

SCRIPTS = {"ru": "assemble.py", "en": "assemble.py", "es": "assemble.py"}


def workdir(lang, nn):
    return active_run_dir(REPO, lang, nn)


def main(chapters):
    rows, fails = [], 0
    py = sys.executable
    for nn in chapters:
        for lang in ("ru", "en", "es"):
            try:
                out = tr_chapter_path(REPO, nn, lang)
            except FileNotFoundError as e:
                rows.append((lang, nn, f"ASSEMBLE FAIL: {e}"))
                fails += 1
                continue
            bk = os.path.basename(out)
            wd = workdir(lang, nn)
            if not os.path.isdir(os.path.join(wd, "units")):
                rows.append((lang, nn, f"ASSEMBLE FAIL: missing {wd}/units"))
                fails += 1
                continue
            r = subprocess.run(
                [py, f"tools/{SCRIPTS[lang]}", nn, wd, out, lang],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            )
            asm = (r.stdout.strip().splitlines() or ["ERR: " + r.stderr[-120:]])[-1]
            if not asm.startswith("OK"):
                rows.append((lang, nn, "ASSEMBLE FAIL: " + asm[:70]))
                fails += 1
                continue
            v = subprocess.run(
                [
                    py,
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
                check=False,
            )
            ok = any(ln.startswith("OK") for ln in v.stdout.splitlines())
            detail = next(
                (ln for ln in v.stdout.splitlines() if ln.startswith(("OK", "FAIL"))),
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
