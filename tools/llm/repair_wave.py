#!/usr/bin/env python3
"""Repair wave orchestrator: assemble → verify --json → locate → repair → loop.

Drives verify.py HARD fails of kinds number_absent / banned_calque to green:
per round, assemble the candidate, run verify --json, locate failing units,
repair each with repair_unit.py (fallback: full translate_unit.py after the
post-repair assert still fails), then re-assemble/re-verify. ≤ --max-rounds.

Exit codes: 0 = verify OK; 1 = exhausted rounds / unrepairable / unlocated;
2 = LLM/infra error.

Never writes under tools/digest/ (workdir is the run dir; digest units are
read-only inputs). No style/LT/factcheck inside the loop.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.llm.verify_issues import REPAIRABLE_KINDS, locate_issues, parse_verify_json  # noqa: E402
from tools.verify import norm_numbers  # noqa: E402

DIRTY_UNIT_CAP = 8  # locked: ≤8 dirty units repaired per round


def _run(cmd: list, **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def assemble_cmd(nn: str, lang: str, workdir: Path, assembled: Path) -> list:
    script = {
        "ru": "tools/assemble.py",
        "en": "tools/assemble_en.py",
        "es": "tools/assemble_es.py",
    }[lang]
    return [sys.executable, _ROOT / script, nn, workdir, assembled]


def run_verify_json(nn: str, lang: str, assembled: Path) -> tuple[int, dict]:
    r = _run([sys.executable, _ROOT / "tools" / "verify.py", nn,
              "--lang", lang, "--file", assembled, "--json"])
    report = parse_verify_json(r.stdout)
    return r.returncode, report


def unit_still_needs(unit: str, issues: list[dict], tr_path: Path, lang: str) -> bool:
    """Post-repair assert: does the unit text still miss a value / carry the stem?"""
    text = tr_path.read_text(encoding="utf-8")
    vals = set(norm_numbers(text, ru=(lang == "ru"), es=(lang == "es")))
    for iss in issues:
        if iss["kind"] == "number_absent" and str(iss["value"]) not in vals:
            return True
        if iss["kind"] == "banned_calque" and len(re.findall(iss["stem"], text, re.I)) > 1:
            return True
    return False


def repair_unit(nn: str, unit: str, lang: str, workdir: Path,
                issues: list[dict]) -> int:
    r = _run([
        sys.executable, _ROOT / "tools" / "llm" / "repair_unit.py",
        "--nn", nn, "--unit", unit, "--lang", lang,
        "--out-dir", workdir,
        "--issues-json", json.dumps(issues, ensure_ascii=False),
    ])
    sys.stderr.write(r.stdout + r.stderr)
    return r.returncode


def translate_unit(nn: str, unit: str, lang: str, workdir: Path) -> int:
    r = _run([
        sys.executable, _ROOT / "tools" / "llm" / "translate_unit.py",
        "--nn", nn, "--unit", unit, "--lang", lang,
        "--out-dir", workdir,
    ])
    sys.stderr.write(r.stdout + r.stderr)
    return r.returncode


def dry_locate(nn: str, lang: str, workdir: Path, assembled: Path) -> int:
    code, report = run_verify_json(nn, lang, assembled)
    located = locate_issues(
        root=_ROOT, nn=nn, lang=lang,
        digest_units_dir=_ROOT / "tools" / "digest" / nn / "units",
        tr_units_dir=workdir / "units",
        fails=[f for f in report.get("fails", [])
               if f.get("kind") in REPAIRABLE_KINDS],
    )
    print(json.dumps(located, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="assemble→verify→repair loop.")
    p.add_argument("--nn", required=True)
    p.add_argument("--lang", required=True, choices=["ru", "en", "es"])
    p.add_argument("--workdir", required=True, help="run dir (parent of units/)")
    p.add_argument("--assembled", required=True)
    p.add_argument("--max-rounds", type=int, default=3)
    p.add_argument("--fallback-retranslate", dest="fallback", action="store_true",
                   default=True, help="retranslate unit when post-repair assert fails (default ON)")
    p.add_argument("--no-fallback-retranslate", dest="fallback", action="store_false")
    p.add_argument("--dry-locate", action="store_true",
                   help="only verify once and print the located map (no LLM)")
    args = p.parse_args(argv)

    workdir = Path(args.workdir).resolve()
    assembled = Path(args.assembled).resolve()
    nn = f"{int(args.nn):02d}"
    lang = args.lang

    if args.dry_locate:
        return dry_locate(nn, lang, workdir, assembled)

    if str(workdir).startswith(str(_ROOT / "tools" / "digest")):
        raise SystemExit("refusing workdir under tools/digest/")

    for round_no in range(1, args.max_rounds + 1):
        a = _run(assemble_cmd(nn, lang, workdir, assembled))
        if a.returncode != 0:
            sys.stderr.write(a.stdout + a.stderr)
            print("ASSEMBLE_FAILED", file=sys.stderr)
            return 1
        code, report = run_verify_json(nn, lang, assembled)
        if report.get("ok"):
            print(f"VERIFY_OK round={round_no}")
            return 0
        unrepairable = [f for f in report["fails"]
                        if f.get("kind") not in REPAIRABLE_KINDS]
        if unrepairable:
            print("UNREPAIRABLE " + json.dumps(unrepairable, ensure_ascii=False))
            return 1
        located = locate_issues(
            root=_ROOT, nn=nn, lang=lang,
            digest_units_dir=_ROOT / "tools" / "digest" / nn / "units",
            tr_units_dir=workdir / "units",
            fails=report["fails"],
        )
        if located.get("_unlocated") or (report["fails"] and not located):
            print("UNLOCATED " + json.dumps(located.get("_unlocated", []), ensure_ascii=False))
            return 1
        dirty = sorted(located)
        deferred = dirty[DIRTY_UNIT_CAP:]
        if deferred:
            print(f"DIRTY_CAP deferred to next round: {', '.join(deferred)}",
                  file=sys.stderr)
        for unit in dirty[:DIRTY_UNIT_CAP]:
            issues = located[unit]
            print(f"round={round_no} repair unit={unit} issues={issues}")
            rc = repair_unit(nn, unit, lang, workdir, issues)
            tr_path = workdir / "units" / f"{unit}.md"
            still = (rc == 0 and tr_path.is_file()
                     and unit_still_needs(unit, issues, tr_path, lang))
            if rc != 0 or still:
                if still and rc == 0:
                    print(f"round={round_no} post-repair assert FAILED unit={unit} "
                          "→ fallback retranslate", file=sys.stderr)
                if not args.fallback:
                    if rc != 0:
                        return 2
                    print("FALLBACK_DISABLED and assert failed", file=sys.stderr)
                    return 1
                rc = translate_unit(nn, unit, lang, workdir)
                if rc != 0:
                    return 2
        # else: loop back to assemble + verify
    print("EXHAUSTED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
