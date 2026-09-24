# Verify auto-repair wave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After assemble, automatically fix `verify.py` HARD failures of kinds `number_absent` and `banned_calque` by repairing only the dirty digest units, then re-assemble and re-verify until green or max rounds.

**Architecture:** Extend `verify.py` with machine-readable JSON. Add a deterministic locator that maps each absent value / calque stem to `tools/digest/<NN>/units/*.md` and the matching TR unit. Add `repair_unit.py` (LLM, constrained prompt) plus `repair_wave.py` orchestrator: locate → repair → assemble → verify, ≤ R rounds, with fallback to full `translate_unit.py` if a number is still missing after one repair. Never write `book/`.

**Tech Stack:** Python 3 stdlib + existing `tools/llm/client.py`, `tools/assemble.py`, `tools/verify.py`, `tools/llm/translate_unit.py` (inject/validate helpers).

**Spec:** [docs/superpowers/specs/2026-09-24-verify-auto-repair-design.md](../specs/2026-09-24-verify-auto-repair-design.md)

## Global Constraints

- Unit-by-unit only; never paste whole `book/*.md` into the LLM
- Workdir = `tools/runs/active/<lang>/<NN>/` (parent of `units/`); refuse writes under `tools/digest/`
- Local Hy Q8: sequential repairs (`-np 1`); one repair call at a time
- `verify` HARD before factcheck/style/LT; repair loop must not call style/LT
- Scale rules: `万`→×10⁴, `亿`→×10⁸; do not map `亿` to Russian «миллиард» (×10⁹)
- Reuse `inject_mechanical_markers` / `validate_unit` from `tools/llm/translate_unit.py`
- Exit codes: repair_wave `0` = verify OK; `1` = exhausted rounds / unrepairable; `2` = LLM/infra error

## File map

| Path | Responsibility |
|------|----------------|
| `tools/verify.py` | Add `--json` stdout report; keep human text + exit codes |
| `tools/llm/verify_issues.py` | Parse JSON / locate issues → per-unit issue lists |
| `tools/llm/repair_unit.py` | One-unit LLM repair CLI |
| `tools/llm/repair_wave.py` | Orchestrate assemble→verify→repair loop |
| `tools/prompts/repair-unit.md` | System prompt for repair |
| `tools/llm/tests/test_verify_issues.py` | Locator + JSON shape tests |
| `tools/llm/tests/test_repair_unit_structure.py` | Post-repair structural gate (no LLM) |
| `tools/llm/README.md` + `docs/translation-playbook.md` | Document repair wave |

```text
                    ┌─────────────┐
   units/*.md  ───► │ assemble.py │ ───► assembled.md
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  verify.py  │──json──► issues[]
                    └─────────────┘
                           │ FAIL
                           ▼
                    ┌─────────────┐
                    │  locator    │──► {unit: [issues]}
                    └─────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ repair_unit / translate│  (per dirty unit)
              └────────────────────────┘
                           │
                           └────── loop ≤ R ──► verify OK or STOP
```

---

### Task 1: `verify.py --json` report

**Files:**
- Modify: `tools/verify.py`
- Test: `tools/llm/tests/test_verify_json.py`

**Interfaces:**
- Produces: on `--json`, last stdout block is a single JSON object:
  ```json
  {
    "ok": false,
    "chapter": "01",
    "lang": "ru",
    "file": "…/assembled.md",
    "fails": [
      {"kind": "number_absent", "value": "610000", "count": 1},
      {"kind": "banned_calque", "stem": "популяц", "count": 2}
    ],
    "warns": [{"kind": "number_less_frequent", "value": "65", "count": 2}]
  }
  ```
- `kind` for number hard-miss: `"number_absent"`; calque over max: `"banned_calque"`; other existing fails keep string kinds (`"headings_mismatch"`, `"sources_mismatch"`, `"cjk_outside"`, `"field_count"`, `"source_line_mismatch"`, `"leftover"` etc.) — map clearly in code comments
- Consumes: existing `fails` / `warns` lists built in `main()`

- [ ] **Step 1: Write the failing test**

```python
# tools/llm/tests/test_verify_json.py
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

class VerifyJson(unittest.TestCase):
    def test_json_flag_emits_object_with_fails(self):
        # Use existing ch01 candidate if present; else skip
        cand = ROOT / "tools/runs/active/ru/01/assembled.md"
        if not cand.is_file():
            self.skipTest("no assembled candidate")
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools/verify.py"), "01",
             "--lang", "ru", "--file", str(cand), "--json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        # May be exit 0 or 1; JSON must parse from last '{' line or full stdout
        text = r.stdout
        start = text.rfind("{")
        self.assertGreaterEqual(start, 0, text[:500])
        data = json.loads(text[start:])
        self.assertIn("ok", data)
        self.assertIn("fails", data)
        self.assertIsInstance(data["fails"], list)
        if data["fails"]:
            self.assertIn("kind", data["fails"][0])
```

- [ ] **Step 2: Run test — expect fail (no `--json`)**

```bash
python3 -m unittest tools.llm.tests.test_verify_json -v
```

Expected: FAIL (unknown arg or no JSON)

- [ ] **Step 3: Implement `--json`**

In `tools/verify.py` `main()`:
- `ap.add_argument("--json", action="store_true")`
- Build structured `fail_objs` / `warn_objs` when appending to `fails`/`warns` (or parse at end with small helpers)
- Minimal helper for number line:

```python
def fail_number_absent(lost_hard: dict) -> dict:
    # emit one fail entry per value OR one entry with values list —
    # prefer one object per value for locator simplicity:
    return [{"kind": "number_absent", "value": str(v), "count": int(c)}
            for v, c in lost_hard.items()]
```

At end of `main()`, **always** build `report = {"ok": not fails, ...}` first.

```python
if args.json:
    print(json.dumps(report, ensure_ascii=False))
if fails:
    print("FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)
```

**Critical (eng review):** emit JSON **before** `sys.exit(1)`. Regression test: FAIL + `--json` still yields parseable JSON on stdout.

- [ ] **Step 4: Re-run test — PASS**

Also add tempfile-based test (no live `assembled.md` required) that runs verify on a tiny synthetic pair if feasible; otherwise keep candidate test + add unit test that only checks argparse accepts `--json` and a mocked report helper.

```bash
python3 -m unittest tools.llm.tests.test_verify_json -v
```

- [ ] **Step 5: Commit**

```bash
git add tools/verify.py tools/llm/tests/test_verify_json.py
git commit -m "feat(verify): emit --json machine report for repair wave"
```

---

### Task 2: Locator — map issues → unit IDs

**Files:**
- Create: `tools/llm/verify_issues.py`
- Test: `tools/llm/tests/test_verify_issues.py`

**Interfaces:**
- Consumes: `norm_numbers` from `tools.verify` (import carefully — prefer moving `norm_numbers` usage via):

```python
# tools/llm/verify_issues.py
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import re
import sys

# Import norm_numbers from verify without running main
def _load_norm():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "htlb_verify", Path(__file__).resolve().parents[1] / "verify.py")
    mod = importlib.util.module_from_spec(spec)
    # Prevent argparse main: only exec module body — verify.py currently runs main at import?
```

**Important:** Today `tools/verify.py` ends with `if __name__ == "__main__": main()`. Import is safe. Use:

```python
from tools.verify import norm_numbers  # may fail if tools/ not a package
```

If `from tools.verify import norm_numbers` fails under unittest path, use `importlib` loading `tools/verify.py` as above **without** calling `main`.

- Produces:

```python
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
    Skips kinds not in REPAIRABLE = {"number_absent", "banned_calque"}.
    """
```

Logic for `number_absent`:
1. For each digest unit `00`..`N` (skip `00` for numbers unless value appears there — usually items only): compute `cn_vals = set(norm_numbers(text))`, `tr_vals = set(norm_numbers(tr, ru=(lang=="ru"), es=(lang=="es")))`.
2. If `value in cn_vals` and `value not in tr_vals` → attach issue to that unit.
3. If no unit matches CN, attach to `"_unlocated"` (wave will STOP on those).

Logic for `banned_calque`:
1. Grep `stem` case-insensitive in each TR unit body; if count>0, attach (wave repairs all units that contain the stem when chapter count >1).

- [ ] **Step 1: Failing tests**

```python
# tools/llm/tests/test_verify_issues.py
import tempfile, unittest
from pathlib import Path
from tools.llm.verify_issues import locate_issues

class Locate(unittest.TestCase):
    def test_maps_610000_to_unit_with_61_wan(self):
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir(); tr.mkdir()
            (dig / "07.md").write_text(
                "### 7. x\n- 收益：把 123 项试验、61 万余人合起来\n", encoding="utf-8")
            (tr / "07.md").write_text(
                "### 7. x\n- Эффект: 123 испытаний, более 61 тысячи человек\n",
                encoding="utf-8")
            # also need empty siblings? locator should glob [0-9][0-9].md
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "610000", "count": 1}],
            )
            self.assertIn("07", located)
            self.assertEqual(located["07"][0]["value"], "610000")

    def test_calque_stem_to_units(self):
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"; tr = Path(d) / "tr"
            dig.mkdir(); tr.mkdir()
            (dig / "14.md").write_text("### 14.\n", encoding="utf-8")
            (tr / "14.md").write_text("в популяции вирус\n", encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "banned_calque", "stem": "популяц", "count": 2}],
            )
            self.assertIn("14", located)
```

- [ ] **Step 2: Run — FAIL (module missing)**

```bash
python3 -m unittest tools.llm.tests.test_verify_issues -v
```

- [ ] **Step 3: Implement `verify_issues.py`**

Include `REPAIRABLE_KINDS = frozenset({"number_absent", "banned_calque"})` and `parse_verify_json(stdout: str) -> dict` that finds last JSON object in stdout.

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit**

```bash
git add tools/llm/verify_issues.py tools/llm/tests/test_verify_issues.py
git commit -m "feat(llm): locate verify number/calque fails to units"
```

---

### Task 3: Prompt + `repair_unit.py`

**Files:**
- Create: `tools/prompts/repair-unit.md`
- Create: `tools/llm/repair_unit.py`
- Test: `tools/llm/tests/test_repair_unit_structure.py` (structure only; mock no LLM)
- Modify: `tools/llm/translate_unit.py` — export helpers already present (`inject_mechanical_markers`, `validate_unit`, `strip_mechanical_markers`); import them from repair_unit

**Interfaces:**
- CLI:

```bash
python3 tools/llm/repair_unit.py \
  --nn 01 --unit 07 --lang ru \
  --out-dir tools/runs/active/ru/01 \
  --issues-json '[{"kind":"number_absent","value":"610000","count":1}]'
```

- Exit: `0` ok; `2` structural fail after retries; `1` LLM error
- After LLM: `inject_mechanical_markers` + `validate_unit` (same as translate)

**Prompt rules (`repair-unit.md`):**
- Fix only listed issues; do not rewrite unrelated fields unless needed for grammar
- Restore missing absolute numeric values; show CN span + required absolute value
- `万` / `亿` scale table
- Calque: replace stem using glossary alternatives; at most one glossed first use chapter-wide is verify's rule — prefer zero stem if easy
- Output full unit markdown; no fences; no inventing numbers not in ZH

- [ ] **Step 1: Structure tests** — repair output must pass `validate_unit` after inject; bold fields fail

```python
from tools.llm.translate_unit import inject_mechanical_markers, validate_unit

def test_repaired_item_shape():
    body = "### 7. Title\n- Стоимость: 0\n- Простыми словами: a\n- Эффект: 610 000 человек\n- Уровень доказательности: A\n- Примечания: z\n"
    got = inject_mechanical_markers(body, "07")
    assert validate_unit(got, "07", "ru") == []
```

- [ ] **Step 2: Implement prompt + CLI** (mirror `translate_unit.py` message build + retries=2)

Include in user message a block:

```text
Issues to fix (machine):
- number_absent: must include absolute value 610000 somewhere (CN used 61 万)
```

- [ ] **Step 3: Dry-run without server optional** — if no server, skip live smoke in CI; document manual:

```bash
# requires llama-server
python3 tools/llm/repair_unit.py --nn 01 --unit 07 --lang ru \
  --out-dir tools/runs/active/ru/01 \
  --issues-json '[{"kind":"number_absent","value":"610000","count":1}]'
```

- [ ] **Step 4: Commit**

```bash
git add tools/prompts/repair-unit.md tools/llm/repair_unit.py tools/llm/tests/test_repair_unit_structure.py
git commit -m "feat(llm): repair_unit CLI for verify number/calque fixes"
```

---

### Task 4: `repair_wave.py` orchestrator

**Files:**
- Create: `tools/llm/repair_wave.py`
- Modify: `tools/llm/README.md`
- Modify: `docs/translation-playbook.md` (insert step after verify FAIL)

**Interfaces:**

```bash
python3 tools/llm/repair_wave.py \
  --nn 01 --lang ru \
  --workdir tools/runs/active/ru/01 \
  --assembled tools/runs/active/ru/01/assembled.md \
  --max-rounds 3 \
  --fallback-retranslate
```

Algorithm:

```python
def unit_still_needs(unit, issues, tr_path, lang):
    text = tr_path.read_text(encoding="utf-8")
    for iss in issues:
        if iss["kind"] == "number_absent":
            vals = set(norm_numbers(text, ru=(lang == "ru"), es=(lang == "es")))
            if iss["value"] not in vals:
                return True
        if iss["kind"] == "banned_calque":
            if re.search(iss["stem"], text, re.I):
                return True
    return False

def main():
    for round in range(1, max_rounds + 1):
        run assemble → cand
        code, stdout = run verify --json   # JSON printed even on exit 1
        report = parse_verify_json(stdout)
        if report["ok"]:
            print(f"VERIFY_OK round={round}"); return 0
        unrepairable = [f for f in report["fails"] if f["kind"] not in REPAIRABLE]
        if unrepairable:
            print("UNREPAIRABLE", unrepairable); return 1
        located = locate_issues(..., fails=report["fails"])
        if located.get("_unlocated") or (report["fails"] and not located):
            print("UNLOCATED", ...); return 1
        # optional: dirty-unit cap — see UNRESOLVED DECISIONS
        for unit, issues in sorted(located.items()):
            rc = repair_unit(... issues ...)
            if rc != 0:
                if not fallback_retranslate:
                    return 2
                rc = translate_unit(...)
                if rc != 0:
                    return 2
            elif fallback_retranslate and unit_still_needs(unit, issues, ...):
                # Critical: structural OK but number/calque still wrong → one retranslate
                rc = translate_unit(...)
                if rc != 0:
                    return 2
    print("EXHAUSTED"); return 1
```

**Critical (eng review):** fallback is triggered by **post-repair assert** (`value ∉ norm_numbers`), not only by `repair_unit` RC≠0.
Assemble command: `python3 tools/assemble.py {nn} {workdir} {assembled}`  
(lang-specific: if `lang==en` use `assemble_en.py`, `es` → `assemble_es.py`).

- [ ] **Step 1: Implement CLI with `--dry-locate`** that only prints located map from last verify JSON file (no LLM) — for testing orchestrator glue

```bash
python3 tools/llm/repair_wave.py --nn 01 --lang ru \
  --workdir tools/runs/active/ru/01 \
  --assembled tools/runs/active/ru/01/assembled.md \
  --dry-locate
```

Expected: prints unit→issues for current failing candidate.

- [ ] **Step 2: Wire full loop**

- [ ] **Step 3: Manual integration on ch01 candidate** (human/agent):

```bash
python3 tools/llm/repair_wave.py --nn 01 --lang ru \
  --workdir tools/runs/active/ru/01 \
  --assembled tools/runs/active/ru/01/assembled.md \
  --max-rounds 3 --fallback-retranslate
python3 tools/verify.py 01 --lang ru --file tools/runs/active/ru/01/assembled.md
```

Expected: verify exit 0, or remaining fails listed.

- [ ] **Step 4: Docs** — playbook §2 after step 4:

```text
4b. On verify FAIL (numbers/calques): 
    python3 tools/llm/repair_wave.py --nn <NN> --lang <lang> \
      --workdir tools/runs/active/<lang>/<NN> \
      --assembled <cand.md> --max-rounds 3 --fallback-retranslate
    Then re-run verify (HARD). Do not start style/LT until OK.
```

- [ ] **Step 5: Commit**

```bash
git add tools/llm/repair_wave.py tools/llm/README.md docs/translation-playbook.md
git commit -m "feat(llm): repair_wave loop assemble→verify→repair"
```

---

### Task 5: Acceptance on ch01 RU candidate

**Files:** none new (ops)

- [ ] **Step 1:** Ensure llama-server `-c 16384` up; `.env` loaded

- [ ] **Step 2:** Run `repair_wave` on `tools/runs/active/ru/01`

- [ ] **Step 3:** Confirm `verify` exit 0

- [ ] **Step 4:** Spot-check formerly bad units `07` (610000), `31` (99.99), `34` (亿 scale), `36` (129), calque-free `популяц`

- [ ] **Step 5:** Do **not** copy to `book/ru` unless user asks; commit tooling only if Tasks 1–4 not yet committed

---

## Self-review (author)

1. **Spec coverage:** JSON verify, locator, repair_unit, wave loop, fallback retranslate, no book/ writes, scale rules — all tasked.
2. **Placeholders:** none intentional.
3. **Types:** `fails: list[dict]` with `kind`/`value`/`stem`/`count` consistent across Tasks 1–4.

## Out of scope (explicit)

- Auto-fix `headings_mismatch` / `sources_mismatch` / cost-tag count
- Factcheck live judge wiring inside repair_wave
- Parallel repair on Q8
- ES/EN smoke beyond shared code paths (implement lang switches in assemble selection)

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ISSUES | 8 issues, 1 critical gap (fallback vs post-repair) |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** APPROVE_WITH_CHANGES — eng review required before implement (fix Critical/Important rows below).

| Severity | Section | Issue | Recommendation |
|----------|---------|-------|----------------|
| Critical | Architecture | Design says fallback when number still missing after one repair; Task 4 only falls back on `repair_unit` RC≠0. Structural OK + wrong scale → silent loop thrash until EXHAUSTED. | After each successful repair write, assert `value ∈ norm_numbers(tr_unit)` (and calque stem count↓); if still missing, call `translate_unit` once for that unit before next assemble. |
| Critical | Code quality | `verify.py` today `sys.exit(1)` on FAIL (`~258–307`) before any trailing JSON can emit. | Emit JSON (or build report dict) **before** `sys.exit`; single `return code` path. Add regression test that FAIL+`--json` still parses. |
| Important | Architecture | Locator attaches every CN unit containing absent value; no handling when same absolute appears in N units (repair N LLM calls) or when TR has wrong-scale sibling that doesn't clear chapter Counter until all fixed. | Document; optionally repair only units where `value in cn_vals and value not in tr_vals` (already) and sort by unit id; cap dirty units per round (e.g. 8) with report of remainder. |
| Important | Code quality | Dual fail representation risk: human strings vs structured objs can drift; plan still sketches importlib panic for `norm_numbers` though `from tools.verify import norm_numbers` works (same as `test_translate_unit_structure`). | Build structured objs at fail site; derive human line from objs (or vice versa once). Import like existing tests (`sys.path` root). Reuse `refuse_digest_outdir` / `atomic_write` / retries from `translate_unit`. |
| Important | Tests | Task 1 skips without live `assembled.md`; no fixtures for `61万→610000`, `亿≠миллиард`, `99.99↔0,01`. Structure test only checks inject/validate, not repair prompt contract. | Tempfile digest+TR fixtures in `test_verify_issues` / `test_verify_json` (synthetic chapter fragments); assert locator+JSON kinds. Add one pure function test: repaired body must contain absolute string for issue value. |
| Important | Performance | `--fallback-retranslate` full-unit rewrite can reintroduce calques/drop other numbers → multi-round oscillation on Q8 (sequential, expensive). | Default `--fallback-retranslate` on but only after failed post-repair number assert; never retranslate units that already cleared their issues this round; log per-unit tokens/time. |
| Minor | Architecture | File map ~10 paths (smell ≥8); two CLIs + locator module justified but docs edits can ride Task 4. | Keep 3 Python modules; do not add a 4th service; merge playbook/README into Task 4 commit. |
| Minor | Performance | `max-rounds 3` × all dirty units with no early stop when only unrepairable kinds remain mixed with repairable. | Order: if any non-REPAIRABLE in report → STOP immediately (plan has this); also STOP if located map empty but fails nonempty. |

**Outside voice (3am operator):** First break is `verify --json` exit-before-print (wave thinks parse failed → exit 2 / empty issues). Second is “repair wrote OK, number still 61 тысячи” with no fallback. Third is fallback retranslate nuking a fixed unit and flipping calque counts.

APPROVE_WITH_CHANGES

**UNRESOLVED DECISIONS:**
- ~~Per-round dirty-unit cap~~ → **locked:** hard cap **≤8** dirty units per round; remainder reported and deferred to next round / EXHAUSTED.
- ~~`--fallback-retranslate` default~~ → **locked:** **ON by default**; still only after failed post-repair assert (not on structural RC alone). Opt-out via `--no-fallback-retranslate`.

NO UNRESOLVED DECISIONS

