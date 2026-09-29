#!/usr/bin/env python3
import os
import subprocess
import sys

from translate.lib.config import default_root, translation_langs, unit_dir
from translate.lib.paths import tr_chapter_path

REPO = default_root()


def main(chapters):
    rows, fails = [], 0
    py = sys.executable
    for nn in chapters:
        for lang in translation_langs(REPO):
            try:
                out = tr_chapter_path(REPO, nn, lang)
            except FileNotFoundError as e:
                rows.append((lang, nn, f"ASSEMBLE FAIL: {e}"))
                fails += 1
                continue
            bk = os.path.basename(out)
            wd = os.path.dirname(unit_dir(REPO, lang, nn))
            if not os.path.isdir(os.path.join(wd, "units")):
                rows.append((lang, nn, f"ASSEMBLE FAIL: missing {wd}/units"))
                fails += 1
                continue
            r = subprocess.run(
                [py, "translate/steps/assemble/assemble.py", nn, wd, out, lang],
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
                    "translate/steps/verify/verify.py",
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
