# Verify auto-repair wave — Design

**Date:** 2026-09-24  
**Status:** approved direction (variant A) — awaiting eng plan review  
**Repo:** dlgrv/HowToLiveBetter (English-primary fork)

## Problem

After unit-by-unit Hy-MT2 translation, `assemble.py` succeeds but `verify.py` HARD-fails on:

- **number absent** — dropped or wrong-scale values (`61 万` → «61 тысячи»; `亿` → «миллиард»; `99.99` rewritten as `0,01`)
- **banned calque** — e.g. stem `популяц` more than once

Playbook rule: verify FAIL = STOP before style/LT. Today repair is manual. We need the wave to **locate → repair units → reassemble → re-verify** in a bounded loop.

## Non-goals

- Do not auto-fix headings/tags/sources count mismatches (assemble/blocks bugs)
- Do not write into `book/` — only `tools/runs/…`
- Do not run style/LT until verify is green
- Do not feed whole chapters to the LLM

## Chosen approach (A)

```text
assemble → verify(--json)
    │
    ├─ OK → factcheck → style → LT → plainness
    │
    └─ FAIL (repairable kinds only)
           → locate units (deterministic)
           → repair_unit LLM (or fallback full translate_unit)
           → assemble → verify
           → repeat ≤ R rounds, then STOP + report
```

## Constraints (from TRANSLATION.md / playbook)

- Numbers are identifiers; `万`=×10⁴, `亿`=×10⁸
- Unit-by-unit only; sequential on local Q8 (`-np 1`)
- Structural gate already in `translate_unit.py` (markers, fields, intro)

## Success

Ch01 candidate under `tools/runs/active/ru/01/` reaches `verify` exit 0 via repair wave without hand-editing `book/ru`.
