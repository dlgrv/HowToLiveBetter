#!/usr/bin/env python3
"""Map verify.py --json HARD fails (number_absent / banned_calque) to unit IDs.

Repairable kinds only; everything else is skipped here (repair_wave stops on
unrepairable kinds itself). Digest units live under tools/digest/<NN>/units/
(READ-ONLY for the wave); translated units under the run workdir units/.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.verify import norm_numbers  # noqa: E402

REPAIRABLE_KINDS = frozenset({"number_absent", "banned_calque"})


def parse_verify_json(stdout: str) -> dict:
    """Find the last complete JSON object line in verify --json stdout.

    verify.py prints human lines first and the JSON object as the LAST line
    (even on FAIL), so scan lines backwards for one starting with '{'.
    """
    for line in reversed(stdout.splitlines()):
        s = line.strip()
        if s.startswith("{"):
            try:
                return json.loads(s)
            except ValueError:
                continue
    raise ValueError("no JSON object found in verify --json output")


def locate_issues(
    *,
    root: Path,
    nn: str,
    lang: str,
    digest_units_dir: Path,
    tr_units_dir: Path,
    fails: list[dict],
) -> dict[str, list[dict]]:
    """Return {unit_id: [issue, ...]} for repairable fails only.

    - number_absent: attach to the digest unit whose CN text contains the
      absolute value (via norm_numbers) while the TR unit does not. If no
      CN unit matches, attach to "_unlocated" (wave STOPs on those).
    - banned_calque: attach to every TR unit body containing the stem
      (case-insensitive) — repair all of them when count > 1.
    """
    digest_units = sorted(p.stem for p in digest_units_dir.glob("[0-9][0-9].md"))
    tr_units = sorted(p.stem for p in tr_units_dir.glob("[0-9][0-9].md"))

    cn_texts: dict[str, str] = {}
    for u in digest_units:
        cn_texts[u] = (digest_units_dir / f"{u}.md").read_text(encoding="utf-8")
    tr_texts: dict[str, str] = {}
    for u in tr_units:
        tr_texts[u] = (tr_units_dir / f"{u}.md").read_text(encoding="utf-8")

    cn_vals = {u: set(norm_numbers(t)) for u, t in cn_texts.items()}
    tr_vals = {
        u: set(norm_numbers(t, ru=(lang == "ru"), es=(lang == "es")))
        for u, t in tr_texts.items()
    }

    located: dict[str, list[dict]] = {}
    for fail in fails:
        kind = fail.get("kind")
        if kind not in REPAIRABLE_KINDS:
            continue
        if kind == "number_absent":
            value = str(fail["value"])
            matched = [
                u for u in digest_units
                if value in cn_vals[u] and value not in tr_vals.get(u, set())
            ]
            if not matched and not any(value in tv for tv in tr_vals.values()):
                # real chapter-wide absence: repair every CN unit containing
                # the value (TR may hold a wrong-scale sibling in each)
                matched = [u for u in digest_units if value in cn_vals[u]]
            if not matched and not any(value in tv for tv in tr_vals.values()):
                # value absent chapter-wide and no CN unit maps it → unlocatable
                located.setdefault("_unlocated", []).append(fail)
            for u in matched:
                located.setdefault(u, []).append(fail)
        else:  # banned_calque
            stem = fail["stem"]
            hits = [u for u in tr_units if re.search(stem, tr_texts[u], re.I)]
            if not hits:
                located.setdefault("_unlocated", []).append(fail)
            for u in hits:
                located.setdefault(u, []).append(fail)
    return located


if __name__ == "__main__":
    ap = __import__("argparse").ArgumentParser(
        description="Locate verify --json fails to digest/TR units")
    ap.add_argument("--nn", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--workdir", required=True, help="run workdir (parent of units/)")
    ap.add_argument("--json-file", help="verify --json stdout saved to file; "
                    "default: read stdin")
    args = ap.parse_args()
    workdir = Path(args.workdir)
    raw = Path(args.json_file).read_text(encoding="utf-8") if args.json_file else sys.stdin.read()
    report = parse_verify_json(raw)
    out = locate_issues(
        root=_ROOT, nn=args.nn, lang=args.lang,
        digest_units_dir=_ROOT / "tools" / "digest" / args.nn / "units",
        tr_units_dir=workdir / "units",
        fails=[f for f in report.get("fails", []) if f.get("kind") in REPAIRABLE_KINDS],
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
