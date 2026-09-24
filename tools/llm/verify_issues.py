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
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.verify import norm_numbers  # noqa: E402

REPAIRABLE_KINDS = frozenset({"number_absent", "banned_calque"})


def _num_counter(text: str, lang: str) -> Counter:
    """Counter of absolute numeric values (norm_numbers-folded) in text."""
    return Counter(norm_numbers(text, ru=(lang == "ru"), es=(lang == "es")))


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

    cn_counters: dict[str, Counter] = {}
    for u in digest_units:
        cn_counters[u] = _num_counter(cn_texts[u], "cn")
    tr_counters: dict[str, Counter] = {}
    for u in tr_units:
        tr_counters[u] = _num_counter(tr_texts[u], lang)

    located: dict[str, list[dict]] = {}
    for fail in fails:
        kind = fail.get("kind")
        if kind not in REPAIRABLE_KINDS:
            continue
        if kind == "number_absent":
            value = str(fail["value"])
            # Counter diff (same semantics as verify.py's Counter-subtraction
            # counting): a unit is dirty when ITS OWN cn count exceeds its tr
            # count — a partially-fixed duplicate («61万» ×2 in CN, «610 000»
            # ×1 in TR) is a real per-unit deficit and must not be swallowed
            # by set-membership checks (review A1 false-UNLOCATED bug).
            matched = [u for u in digest_units
                       if cn_counters[u][value] > tr_counters.get(u, Counter())[value]]
            if not matched and not any(c[value] for c in tr_counters.values()):
                # real chapter-wide absence: repair every CN unit containing
                # the value (TR may hold a wrong-scale sibling in each)
                matched = [u for u in digest_units if cn_counters[u][value]]
            if not matched and not any(c[value] for c in tr_counters.values()):
                # value absent chapter-wide and no CN unit maps it → unlocatable
                located.setdefault("_unlocated", []).append(fail)
            for u in matched:
                located.setdefault(u, []).append(fail)
        else:  # banned_calque
            stem = fail["stem"]
            # attach only to units whose OWN tr text carries the stem more
            # than once (that unit is itself an offender); a unit with a
            # single occurrence is at most a legit first-use gloss (F7
            # calque over-attach). Chapter-wide fallback to any unit
            # containing the stem only when the fail came in with count > 1
            # and no unit exceeds 1 (stem spread across units).
            hits = [u for u in tr_units
                    if len(re.findall(stem, tr_texts[u], re.I)) > 1]
            if not hits and int(fail.get("count", 0) or 0) > 1:
                hits = [u for u in tr_units if re.search(stem, tr_texts[u], re.I)]
            if not hits:
                located.setdefault("_unlocated", []).append(fail)
            for u in hits:
                located.setdefault(u, []).append(fail)
    return located


def issues_still_present(unit_tr_text: str, issues: list[dict], lang: str) -> list[str]:
    """Post-repair assert: the specific instance was fixed. Returns leftovers.

    ASYMMETRY with locate_issues (by design, not a bug): the assert only sees
    the repaired TR text — no CN side — so it cannot do a full cn-vs-tr
    deficit diff. It checks the weaker, conservative condition: the required
    value is present at all, and the banned stem is down to ≤1 occurrence
    (one first-use gloss is allowed). The locator's job is to FIND the dirty
    unit (full deficit diff); the assert's job is to CONFIRM the specific
    repair landed. Conservative here means erring toward "still dirty" on a
    partial fix, never toward a false clear.
    """
    counts = _num_counter(unit_tr_text, lang)
    leftovers: list[str] = []
    for iss in issues:
        kind = iss.get("kind")
        if kind == "number_absent" and str(iss["value"]) not in counts:
            leftovers.append(f"number {iss['value']} still absent")
        if kind == "banned_calque":
            n = len(re.findall(iss["stem"], unit_tr_text, re.I))
            if n > 1:
                leftovers.append(f"stem «{iss['stem']}» still {n}x")
    return leftovers


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
