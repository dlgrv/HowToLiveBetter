#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from translate.laya.plain import exit_code_for_cards, plain_terms_lines, score_lines
from translate.lib.config import default_root, translation_langs
from translate.steps.repair.repair_wave import DIRTY_UNIT_CAP, _run, assemble_cmd, run_verify_json

ROOT = Path(default_root())


def simplify_unit(nn: str, unit: str, lang: str, workdir: Path) -> int:
    r = _run(
        [
            sys.executable,
            ROOT / "translate" / "steps" / "polish" / "simplify_unit.py",
            "--nn",
            nn,
            "--unit",
            unit,
            "--lang",
            lang,
            "--out-dir",
            workdir,
        ]
    )
    sys.stderr.write(r.stdout + r.stderr)
    return r.returncode


def score_units(workdir: Path, lang: str) -> tuple[list[str], list[dict], int]:
    units_dir = workdir / "units"
    dirty: list[str] = []
    all_cards: list[dict] = []
    if not units_dir.is_dir():
        return dirty, all_cards, 0
    for path in sorted(units_dir.glob("*.md")):
        uu = path.stem
        if uu == "00":
            continue
        text = path.read_text(encoding="utf-8")
        rows = plain_terms_lines(text, lang)
        if not rows:
            continue
        cards = score_lines(rows)
        for c in cards:
            entry = dict(c)
            entry["unit"] = uu
            all_cards.append(entry)
        if any(c.get("verdict") == "непонятно" for c in cards):
            dirty.append(uu)
    return dirty, all_cards, exit_code_for_cards(all_cards)


def dry_score(nn: str, lang: str, workdir: Path) -> int:
    dirty, all_cards, code = score_units(workdir, lang)
    print(
        json.dumps(
            {"nn": nn, "lang": lang, "dirty": dirty, "cards": all_cards, "exit": code},
            ensure_ascii=False,
            indent=2,
        )
    )
    return code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="clarity→simplify→assemble→verify loop.")
    p.add_argument("--nn", required=True)
    p.add_argument("--lang", required=True, choices=translation_langs())
    p.add_argument("--workdir", required=True, help="run dir (parent of units/)")
    p.add_argument("--assembled", required=True)
    p.add_argument("--max-rounds", type=int, default=3)
    p.add_argument(
        "--max-dirty",
        type=int,
        default=DIRTY_UNIT_CAP,
        help="max dirty units simplified per round (default 8)",
    )
    p.add_argument(
        "--dry-score",
        action="store_true",
        help="score units once and print JSON (no LLM simplify)",
    )
    args = p.parse_args(argv)

    workdir = Path(args.workdir).resolve()
    assembled = Path(args.assembled).resolve()
    nn = f"{int(args.nn):02d}"
    lang = args.lang

    if args.dry_score:
        return dry_score(nn, lang, workdir)

    if str(workdir).startswith(str(ROOT / "translate" / "digest")):
        raise SystemExit("refusing workdir under translate/digest/")

    for round_no in range(1, args.max_rounds + 1):
        dirty, _cards, score_exit = score_units(workdir, lang)
        if score_exit == 2:
            print("LAYA_DOWN", file=sys.stderr)
            return 2
        if not dirty:
            print(f"CLARITY_OK round={round_no}")
            return 0
        deferred = dirty[args.max_dirty :]
        if deferred:
            print(f"DIRTY_CAP deferred to next round: {', '.join(deferred)}", file=sys.stderr)
        for unit in dirty[: args.max_dirty]:
            print(f"round={round_no} simplify unit={unit}")
            rc = simplify_unit(nn, unit, lang, workdir)
            if rc != 0:
                return 2
        a = _run(assemble_cmd(nn, lang, workdir, assembled))
        if a.returncode != 0:
            sys.stderr.write(a.stdout + a.stderr)
            print("ASSEMBLE_FAILED", file=sys.stderr)
            return 1
        _code, report = run_verify_json(nn, lang, assembled)
        if not report.get("ok"):
            print("RUN_REPAIR", file=sys.stderr)
            print(json.dumps(report.get("fails", []), ensure_ascii=False))
            return 1
    dirty, _cards, score_exit = score_units(workdir, lang)
    if score_exit == 2:
        print("LAYA_DOWN", file=sys.stderr)
        return 2
    if dirty:
        print("LEFTOVER " + json.dumps(dirty, ensure_ascii=False))
    else:
        print("CLARITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
