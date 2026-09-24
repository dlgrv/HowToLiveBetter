# Plain-language pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax. **Do not edit `book/` until the user explicitly says to apply a pilot line.** No mass chapter rewrite in this plan.

**Goal:** Quality pack (plain language + grammar + meaning) with **free self-hosted LanguageTool**, proven on ch01 §33 v3 — correct command order, no invented parallel linters.

**Architecture:** ZH → each locale (EN = tone reference only). Prevention in prompts → assemble → verify HARD → optional simplify → re-verify → **factcheck** → **style WARN** (extended `style_check`) → LanguageTool → plainness → human. Mass rewrite out of scope. Parity + status-line WARN deferred to a follow-up plan.

**Tech Stack:** `make_digest` / `assemble.py` | `assemble_en.py` | `assemble_es.py` / `verify` / `factcheck` / `style_check` / `plainness`; `glossary.json`; Docker LanguageTool ($0); `lt_check.py`.

**Spec:** [docs/superpowers/specs/2026-09-23-plain-language-pipeline-design.md](../specs/2026-09-23-plain-language-pipeline-design.md)

**Pilot gold:** [docs/superpowers/pilots/2026-09-23-plain-01-item33.md](../pilots/2026-09-23-plain-01-item33.md) **v3**

**Review lock-in (2026-09-23):** factcheck before style; extend `style_check` (no new `style_plain_lint`); cut parity/status-line tasks to follow-up.

---

## CORRECT PIPELINE ORDER (commands)

### A) New chapter / new translation

```text
1. python3 tools/make_digest.py <NN>

2. LLM translate units          # ZH→ru|en|es + quality pack + name_forms
                                # write units with §TAG§ / §SRC§

3. Assemble (pick ONE — names are not symmetric):
     RU: python3 tools/assemble.py <NN> <workdir> book/ru/<slug>.md
     EN: python3 tools/assemble_en.py <NN> <workdir> book/en/<slug>.md
     ES: python3 tools/assemble_es.py <NN> <workdir> book/es/<slug>.md

4. python3 tools/verify.py <NN> --lang <ru|en|es>
                                # HARD — stop if FAIL

5. [optional] simplify plain-terms only (LLM + tools/prompts/simplify-plain.md)

6. python3 tools/verify.py <NN> --lang <lang>
                                # MUST re-run after any plain rewrite

7. Factcheck vs ZH (pass E) — AFTER re-verify, BEFORE style/LT
     # Live judge often unavailable; for smoke/tests use --stdin-verdict mock.
     # No --stdin-verdict → exit 2 (judge_unavailable).
     # gate=fail|error or grounded=false → exit 1.
     # --lang choices today: ru|en only (es: N/A until factcheck extended).
     python3 tools/validate/factcheck.py \
       --chapter <NN> --lang ru \
       --cn-unit <path-to-cn-unit.md> \
       --tr-unit <path-to-tr-unit.md> \
       --stdin-verdict '{"unit":"…","assertions":[],"issues":[]}'

8. Style WARN (extended style_check — plain-terms focus + glossary markers)
     python3 tools/style_check.py book/<lang>/<file>.md --lang <ru|en>
     # es: add tools/rules/es.json in a later task if needed; until then skip or WARN skip

9. LanguageTool (self-host) — AFTER factcheck
     python3 tools/lt_check.py --file book/<lang>/<file>.md --lang <lang>
     # server down → WARN skip, never FAIL the chapter

10. Plainness length WARN (ru|en only today; no ES field yet)
     python3 -m tools.validate.plainness <NN> --lang <ru|en>

11. Human pass — sensitive tone; skim titles/Cost; ES parity by eye until follow-up tooling
```

### B) Simplify-only (existing book, e.g. §33)

```text
1. Patch plain-terms only
2. python3 tools/verify.py <NN> --lang <lang>
3. factcheck.py … (ru|en; mock if no judge)
4. style_check.py <file> --lang <lang>
5. lt_check.py --file <file> --lang <lang>
6. python3 -m tools.validate.plainness <NN> --lang <ru|en>
7. human
```

### Why this order

| Step | Why here |
|------|----------|
| assemble before verify | sources must be injected |
| verify before polish | don’t grammar-fix a failing chapter |
| simplify before factcheck/LT | don’t check text you will rewrite |
| verify again after simplify | numbers in plain can drift |
| **factcheck before style/LT** | aligns `factcheck.py` (“after verify, before style/QE”); don’t polish flipped negation |
| LT after factcheck | grammar on meaning-stable text |
| human last | sensitive topics, taste |

### Forbidden

- `assemble_ru.py` / `assemble_<lang>.py` for RU (does not exist)
- LT or plainness before first verify
- LT or style before factcheck after a simplify pass
- EN as structural master for RU/ES
- Claiming live factcheck chapter gate without judge / without `--stdin-verdict`
- New parallel `style_plain_lint.py` (extend `style_check` instead)

---

## Global Constraints

- CN is source of truth; never invent numbers; plain digits ⊆ Benefit (`43,2`↔`43.2`).
- Never alter Sources / DOIs / URLs / cost-tag comments.
- No mass rewrite. Apply §33 to `book/` only on explicit user OK.
- Commits only when user asks.
- No paid LanguageTool Premium — Docker self-host only.
- RU/ES from ZH; EN = tone only.

---

## Quality pack

### Locked (pilot)

1. Neighbor test.  
2. Chemical gloss + (term); no *гербицид* / bare *paraquat* / bare *herbicida*.  
3. Procedures → Benefit.  
4. Cases / no EN calque (*в Бангладеше*).  
5. Readable 2–3 sentences > brutal ≤25 if sense breaks.  
6. Dual-topic: one sentence each + optional takeaway.  
7. No HR/RR/OR/CI in plain-terms.

### High (in this plan)

8. Units/abbreviations gloss on first use in plain (or drop to Benefit).  
9. Calque ban-list per lang (extend `rules/*.json` + glossary).  
10. Factcheck after simplify (`reversed_logic` / `invented` / `dropped_condition` / `hardened_claim`).  
11. Cross-locale parity — **follow-up plan** (manual eye-check for now).

### Medium (in this plan as prompts / docs)

12. Titles + Cost: neighbor-test in prompts; no mass rewrite.  
13. Sensitive topics: simplify without how-to detail.  
14. Upstream drift checklist in playbook.  
15. Status line / China-disclaimer WARN — **follow-up plan**.  
16. ES decimal comma consistency in prompts.

---

## Out of scope / follow-up plan

- Mass rewrite; HR→verify FAIL; wave_pipeline `/root`; judge-plainness hard CI  
- **Task deferred:** `parity_plain.py`, status-line checker  
- `rules/es.json` + factcheck `--lang es` + plainness ES label  
- LanguageTool Premium  

---

### Task 1: Pilot (DONE)

- [x] ch01 §33 → **v3** gold (pilot file title must say v3)

---

### Task 2: Prompts + glossary

**Files:**
- Create: `tools/prompts/translate-unit.md`
- Create: `tools/prompts/simplify-plain.md`
- Modify: `tools/glossary.json` — extend `style_rules` (ru/en/**es**); add `name_forms`, `banned_calques`, `abbrev_gloss_examples`
- Create: `tools/validate/tests/test_glossary_style_rules.py`
- Create: `tools/validate/tests/test_glossary_name_forms.py`

**`name_forms` starter:**

```json
"name_forms": [
  {"lemma": "Бангладеш", "lang": "ru", "gov": "в+prep", "form": "в Бангладеше"},
  {"lemma": "Бангладеш", "lang": "ru", "gov": "gen", "form": "Бангладеша"},
  {"lemma": "Китай", "lang": "ru", "gov": "в+prep", "form": "в Китае"}
]
```

- [ ] **Step 1: Write failing tests**

```python
# tools/validate/tests/test_glossary_style_rules.py
import json, os, unittest
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLOSS = os.path.join(REPO, "tools", "glossary.json")

class TestGlossaryStyleRules(unittest.TestCase):
    def test_langs_have_distinctive_contract(self):
        rules = json.load(open(GLOSS, encoding="utf-8"))["style_rules"]
        for lang, needles in {
            "ru": ("падеж", "сорняков", "кальк"),
            "en": ("weedkiller", "neighbor", "bare"),
            "es": ("malas hierbas", "veneno"),
        }.items():
            self.assertIn(lang, rules)
            blob = "\n".join(rules[lang]).lower()
            self.assertTrue(any(n in blob for n in needles), lang)

    def test_banned_calques_ru_nonempty(self):
        data = json.load(open(GLOSS, encoding="utf-8"))
        self.assertTrue(data.get("banned_calques", {}).get("ru"))
```

```python
# tools/validate/tests/test_glossary_name_forms.py
import json, os, unittest
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLOSS = os.path.join(REPO, "tools", "glossary.json")

class TestNameForms(unittest.TestCase):
    def test_bangladesh_prep(self):
        forms = json.load(open(GLOSS, encoding="utf-8"))["name_forms"]
        hit = [f for f in forms if f.get("form") == "в Бангладеше"]
        self.assertTrue(hit)
```

- [ ] **Step 2:** `python3 -m unittest tools.validate.tests.test_glossary_style_rules tools.validate.tests.test_glossary_name_forms -v` → FAIL  
- [ ] **Step 3:** Write prompts (quality pack + v3 few-shot + ZH-only + this pipeline order) + update glossary  
- [ ] **Step 4:** Same unittest → PASS  
- [ ] **Step 5:** Commit only if user asks  

---

### Task 3: Extend `style_check` (not a new script)

**Files:**
- Modify: `tools/style_check.py` — optional `--plain-only` to scan only plain-terms lines; load extra markers from `glossary.json` `banned_calques` + `name_forms` anti-patterns (e.g. flag `в Бангладеш` without `е`)  
- Modify: `tools/rules/ru.json` (and en) — add calque markers as needed  
- Modify: `tools/validate/tests/test_style_check.py` — new cases  

CLI stays: `python3 tools/style_check.py <file.md> --lang ru [--plain-only]`  
Exit always 0 (WARN).

- [ ] **Step 1: Failing test** — fixture line `- Простыми словами: … в Бангладеш …` with `--plain-only` yields WARN containing `Бангладеш`  
- [ ] **Step 2:** Run existing + new test → FAIL on new case  
- [ ] **Step 3:** Implement `--plain-only` + glossary-driven markers  
- [ ] **Step 4:** PASS  
- [ ] **Step 5:** Commit only if user asks  

---

### Task 4: Playbook + factcheck honesty

**Files:**
- Modify: `docs/translation-playbook.md` — replace pipeline diagram with CORRECT ORDER (assemble names fixed; factcheck before style)  
- Modify: spec — same  
- Note in playbook: factcheck `--lang` ∈ {ru,en}; es N/A; without `--stdin-verdict` prints `judge_unavailable` and exits **2**; `gate=fail|error` or `grounded=false` → exit **1**  

Mock smoke:

```bash
python3 tools/validate/factcheck.py \
  --chapter 01 --lang ru \
  --cn-unit /path/unit_cn.md --tr-unit /path/unit_ru.md \
  --stdin-verdict '{"unit":"33","assertions":[],"issues":[]}'
```

- [ ] **Step 1:** Edit playbook + spec  
- [ ] **Step 2:** Run mock command once; paste example output into playbook  
- [ ] **Step 3:** Commit only if user asks  

---

### Task 5: LanguageTool self-host + `lt_check.py`

**Files:**
- Create: `tools/languagetool/README.md` (pin image tag, e.g. `erikvl87/languagetool:latest` or a digest)  
- Create: `tools/lt_check.py`  
- Create: `tools/validate/tests/test_lt_check_parse.py`  
- Create: `tools/validate/tests/fixtures/lt_response_sample.json`  

```python
# test_lt_check_parse.py (sketch)
def test_parse_matches_nonempty():
    from tools.lt_check import parse_response
    data = json.load(open(FIXTURE, encoding="utf-8"))
    hits = parse_response(data)
    self.assertTrue(isinstance(hits, list))

def test_server_down_returns_skip(self):
    # check_text with bad base_url → [{"status":"skip","reason":"server_down"}]
    ...
```

```bash
docker run --rm -d --name htlb-lt -p 8010:8010 erikvl87/languagetool
python3 tools/lt_check.py --file book/ru/01-Не-умирайте-рано.md --lang ru
# server down → WARN skip, exit 0
```

Lang map: `ru`→`ru-RU`, `en`→`en-US`, `es`→`es`.

- [ ] **Step 1:** Failing unittest (parse + server_down)  
- [ ] **Step 2:** FAIL  
- [ ] **Step 3:** Implement `lt_check.py` + README  
- [ ] **Step 4:** PASS unittests; optional Docker smoke  
- [ ] **Step 5:** Commit only if user asks  

---

### Task 6: Upstream drift checklist (medium §14)

**Files:** `docs/translation-playbook.md` and/or `docs/upstream-sync.md`

- [ ] **Step 1:** After CN sync: list changed `book/NN-*.md` → queue en/ru/es catch-up using pipeline order A/B  
- [ ] **Step 2:** Commit only if user asks  

---

### Task 7 (optional, user gate): Apply §33 v3 into `book/`

**Only after user says yes.** Use order **B**:

```bash
# patch plain-terms in:
#   book/en/01-Do-Not-Die-Early.md
#   book/ru/01-Не-умирайте-рано.md
#   book/es/01-No-Mueras-Temprano.md
# (translate/simplify still unit-scoped via digest — never whole chapter to LLM)

python3 tools/verify.py 01 --lang en
python3 tools/verify.py 01 --lang ru
python3 tools/verify.py 01 --lang es

# factcheck BEFORE style/LT (ru|en). Exit 1 on gate=fail|error.
python3 tools/validate/factcheck.py \
  --chapter 01 --lang ru \
  --cn-unit tools/digest/01/units/33.md \
  --tr-unit /path/to/ru-unit-33.md \
  --stdin-verdict '{"unit":"33","assertions":[],"issues":[]}'
python3 tools/validate/factcheck.py \
  --chapter 01 --lang en \
  --cn-unit tools/digest/01/units/33.md \
  --tr-unit /path/to/en-unit-33.md \
  --stdin-verdict '{"unit":"33","assertions":[],"issues":[]}'

python3 tools/style_check.py book/ru/01-Не-умирайте-рано.md --lang ru --plain-only
python3 tools/style_check.py book/en/01-Do-Not-Die-Early.md --lang en --plain-only
# es: skip until rules/es.json (CLI soft-skips)

python3 tools/lt_check.py --file book/ru/01-Не-умирайте-рано.md --lang ru
python3 tools/lt_check.py --file book/en/01-Do-Not-Die-Early.md --lang en
python3 tools/lt_check.py --file book/es/01-No-Mueras-Temprano.md --lang es

python3 -m tools.validate.plainness 01 --lang ru
python3 -m tools.validate.plainness 01 --lang en
# human: sensitive tone + ES eye parity
```

- [ ] **Step 1:** Patches from pilot v3  
- [ ] **Step 2:** Run B-order  
- [ ] **Step 3:** Commit only if user asks  

---

## Follow-up plan (not this PR)

- `parity_plain.py` (cross-locale numbers/density)  
- Status-line + China-disclaimer WARN  
- `rules/es.json`, factcheck `es`, plainness ES `En términos sencillos`  

---

## Self-review

| Review ask | Done? |
|------------|--------|
| RU = `assemble.py` | Yes |
| factcheck before style | Yes |
| Extend style_check, no new lint script | Yes |
| Cut parity/status-line | Follow-up |
| Concrete tests Tasks 2/3/5 | Yes |
| factcheck CLI + es N/A + mock | Yes |
| plainness exact invoke | Yes |
| LT server-down skip | Yes |
| Pilot title v3 | Fix in same edit |

---

## Execution handoff

Execute **Task 2 → 3 → 4 → 5 → 6**; Task 7 only on your OK for §33 in `book/`.

**1. Subagent-Driven** | **2. Inline**
