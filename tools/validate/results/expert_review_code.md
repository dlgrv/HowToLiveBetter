# Expert code review — quality pipeline v2 (branch quality/pipeline-v2)

Reviewer: adversarial code review subagent. Date: 2026-09-19 (UTC).
Scope: tools/pipeline/{config,store,judges,qe}.py, tools/validate/*.py, tools/validate/tests/*, tools/style_check.py, tools/verify.py (_lang_pack + labels/banned), tools/status.py (pass columns), tools/rules/*.

Method: full read of all listed sources, execution of the unit test suite (`python3 -m unittest discover -s tools/validate/tests`), `golden_pairs.py validate`, and targeted Python repros for suspected logic bugs. No tracked file was modified.

Review-environment note (important for the caller): the repo moved UNDER me during review — commits `42e2815` (book/ru 07/16/24/29 calque fix + ru.json + golden manifest refresh + golden_collect FP fix) and `fad373a` (test key alignment) landed mid-review. Two issues I had staged (test asserting `v["n"]` while the collector emits `"answered"`; decoy FP rate returning `None` on all-ties) were fixed by those commits and are NOT re-reported. All findings below were re-verified against HEAD = `fad373a`. Suite state at HEAD: **Ran 94 tests ... OK** (the task brief said 79 tests — count drift, not a bug; see §Tests). Earlier in the review window the suite transiently showed 1 FAIL + 1 ERROR caused by that concurrent manifest refresh — a reminder that `results/*.json` artifacts, the manifest, and tests are rewritten in place without atomicity; anyone running the suite while a wave is committing gets spurious failures.

Severity scale: critical = data loss/security breach; major = wrong gate/metric results or contract violation that will bite in normal use; minor = robustness, consistency, dead code.

---

## Findings

### 1. MAJOR — `_line_of_collapsed` off-by-one: whitespace-drift path attributes spans to the WRONG line
**Evidence:** `tools/validate/factcheck.py:92-103` (function), `:67-83` (use inside `check_grounding`).
**Verified repro** (run at HEAD):
```
cn = "первая строка\nвторая строка\nтретья\n"
pos = _norm(cn).find("вторая")   # = 12, the START of line 2
_line_of_collapsed(cn, pos)      # -> 0  (the PREVIOUS line)
```
The loop tests `seen >= collapsed_pos` *before* consuming character `i`; when the collapsed offset lands exactly on a line start, the function returns the previous line's start. In `check_grounding`, the whitespace-drift fallback (`pos < 0` branch, lines 69-75) uses this mapping to decide whether the span sits on a service line (来源/§SRC§/成本标签/证据等级, lines 78-83). A span that begins exactly at a service line boundary is therefore checked against the *body line above it*; combined with the final gate (line 85: `_norm(span)` accepted if present anywhere in the normalized body — e.g. repeated boilerplate that also occurs in body text), an assertion grounded on a meaningless service line can be **kept** instead of dropped. Additionally, the extracted "line" (line 78) is only up to the next `\n`, so multi-line spans are context-checked on their first line only.
**Fix:** increment `seen` before the boundary test (`if seen >= collapsed_pos` → check after consuming the char, or return `line_start` only when `seen > collapsed_pos`); better, drop the positional heuristic entirely: in the drift path, scan all lines whose normalized form contains `_norm(span)` and drop if *any* of them is a service line.

### 2. MAJOR — `verify.py --file` success overwrites the chapter's verify stamp: mutation harness and tests corrupt `.status` freshness state
**Evidence:** `tools/verify.py:296-300` (mark written unconditionally on success, with `"file": os.path.basename(tr_path)`), `tools/validate/mutation_test.py:67-87` (`run_verify(..., file_text=...)` passes each mutant via `--file`), `:156-179` (`build_cases` runs 30 mutants), `tools/validate/tests/test_mutation_spec.py:80-87`.
Any mutant that passes verify (which is exactly the harness's goal — "verify-safe cases") refreshes `tools/.status/<NN>-<lang>.ok` with `ts = time.time()` and the bogus filename `mut_*.md`. `status.py:25-34` then reports the chapter as freshly verified (`os.path.getmtime(book) <= os.path.getmtime(mark)`), masking a stale/contaminated book file. The unit tests trigger the same rewrite on every suite run (test_clean_chapter_passes_wrapper). `.status/` is transient, but its whole purpose — "fresh = OK, stale = file changed after last verify" — is silently defeated.
**Fix:** in `verify.py`, skip the stamp write when `--file` is given (a candidate file is not the committed book), or write the stamp only when `tr_path` resolves to `book/<lang>/<NN>-*.md`.

### 3. MAJOR — .gitignore gaps: verdict files and the style-FP session are committable, violating the transient/committed contract
**Evidence:** `.gitignore:8-11` ignores `tools/judge/`, `tools/.qe/`, `results/_batch*.json` (plus session artifacts at lines 21-24) — but NOT:
- `tools/validate/results/factcheck/` — this is `factcheck.py`'s **default outdir** (`tools/validate/factcheck.py:163`), which persists full judge verdicts (`write_result`, lines 132-149) including raw model output and grounding payloads;
- `tools/validate/results/style_fp_session.json` — currently sitting untracked in the worktree (`git status`), i.e. one `git add -A` away from being committed, while its sibling markup sessions (`golden_session/`, `golden_verdicts_batch*.json`) were deliberately ignored in a99d401 as transient.
Contract per the protocol: results with seeds (manifest, mutations_seed42, summaries) are committed; verdicts and labeling sessions are machine-local. Today the default factcheck path writes verdicts into a tracked-by-default location.
**Fix:** add `tools/validate/results/factcheck/` and `tools/validate/results/style_fp_session.json` (or a `style_fp_session*.json` glob) to `.gitignore`.

### 4. MAJOR — broken/empty judge verdicts are treated as a clean pass by the gate
**Evidence:** `tools/validate/judge.py:72-75` — unparseable judge reply becomes `verdict = {"raw_reply": reply}`; `tools/validate/factcheck.py:114-129` (`gate_major`) iterates `verdict.get("assertions", [])` → an `{"raw_reply": ...}` or empty-assertions verdict yields `gate: "pass"`; `factcheck.py:106-111` (`grounded_rate`) — a verdict with no assertions is vacuously `grounded=True` (`not dropped` on an empty drop list).
Failure mode: a judge reply truncated by `max_tokens=2048` (`tools/pipeline/judges.py:61` default) or returning prose around the JSON is persisted and silently counted as a PASS in `retro_e_report.py:60-73` totals. A quality gate that cannot distinguish "judge says clean" from "judge output unusable" overstates pass-E coverage.
**Fix:** in `judge.py`, keep the reply but mark the verdict (e.g. `{"parse_error": true, ...}`); in `gate_major`/`grounded_rate`, treat missing/unparseable assertions as `gate: "error"` (or at minimum exclude them from pass counts and surface a counter in `retro_e_report` totals).

### 5. MINOR — locale-dependent subprocess I/O: CN payloads can crash the QE runner and verify wrapper under non-UTF-8 locales
**Evidence:** `tools/pipeline/qe.py:74-76` — `subprocess.run([exe, "-c", src], input=payload, text=True, ...)` with no `encoding=`. `payload` contains CN source and RU/EN MT segments; under `LC_ALL=C` (common in cron/CI) `text=True` encodes with the ANSI locale and raises `UnicodeEncodeError` instead of the designed `QeUnavailable` → the "explicit SKIPPED" degradation (`qe.py:57-66`) never happens and the pipeline hard-crashes. Same pattern in `tools/validate/mutation_test.py:82`: `run_verify` decodes `verify.py` stdout, which contains the CN book filename (`verify.py:286`), with the locale codec.
**Fix:** pass `encoding="utf-8"` (and `errors="replace"` for the wrapper's captured output) to both `subprocess.run` calls.

### 6. MINOR — decoy FP rate conflates "no decoy answers" with "all ties" (post-42e2815 semantics)
**Evidence:** `tools/validate/golden_collect.py:34-50` — `_rate` now returns `0.0` whenever `answered == 0`. Correct for all-decoys-tied, but a lost/empty batch (data error) also reports `decoy_fp_rate: 0.0` — the perfect-looking FP floor a consumer checks against the 10% gate. The commit message/docs only justified the all-ties case.
**Fix:** keep `rate: 0.0` for genuine ties but expose `answered` (already present) as the authoritative denominator in the gate check, or return `null` when `answered == 0` AND the decoy answer keys are entirely absent from `answers`.

### 7. MINOR — `status.py` pass-columns fc fallback mislabels discarded (unverifiable) assertions as FAIL
**Evidence:** `tools/status.py:58-65` — `g = d.get("gate") or ("fail" if d.get("grounding", {}).get("dropped") else "pass")`. Per the factcheck protocol (factcheck.py docstring lines 6-8: ungrounded assertions are *discarded*; the chapter gate is `gate_major` on what remains), `dropped` is not a failure signal — a unit whose judge hallucinated one span out of five clean assertions shows `fc:FAIL` on the dashboard, while the persisted `gate` from `gate_major` would be `pass`. Also the fallback duplicates gate logic that `retro_e_report`/`gate_major` already own.
**Fix:** `write_result` should persist `gate_major(verdict)["gate"]` (it already computes `grounding`), and `status.py` should read only that field.

### 8. MINOR — `judge_metrics.decode` silently truncates on length mismatch; `nativeness_rate` doesn't do what its docstring says
**Evidence:** `tools/validate/judge_metrics.py:101-111` — `zip(session["pairs"], marks)` truncates to the shorter list; misaligned/short answer files produce metrics over a silently smaller sample instead of an error (contrast `cohens_kappa`, line 26-27, which raises). `:74-82` — `nativeness_rate` docstring claims "decoys excluded" but the function never filters them; exclusion is left to unseen callers.
**Fix:** assert `len(marks) == len(session["pairs"])` in `decode`; rename/parametrize the decoy exclusion in `nativeness_rate`.

### 9. MINOR — `gen_ref` does not pin golden-set selection: regeneration after any book edit silently produces a different 60-pair set
**Evidence:** `tools/validate/golden_pairs.py:10-13` (docstring claims determinism from seed=42), `:116-117` — `gen_ref = sha256({chapters, recipes})` only; the actual pair list depends on `excerpt_pool()` over the *current* book text, which changed in 42e2815 (forcing a manifest refresh). Anyone re-running `select` after a book edit gets a different set with the *same* documented seed, invalidating comparability of earlier markup/verdict batches.
**Fix:** include a hash of the selected excerpts (or of the pools) in `gen_ref`, and have `validate` fail if the committed manifest's `gen_ref` doesn't match the committed pairs.

### 10. MINOR — `qe.check_model_license` is dead code: the NC-model guard is never enforced
**Evidence:** `tools/pipeline/qe.py:108-114`; `grep -rn check_model_license tools/` shows no caller and no test. The Apache-2.0-only policy (project.yaml:24 comment) is enforced by nothing: editing `qe_config.json` to a `cometkiwi` model runs undetected.
**Fix:** call it in `run_scores` (raise `QeUnavailable`/`ValueError` on banned names) and add a unit test.

### 11. MINOR — `store.write_verdict` uses a fixed `.tmp` name: concurrent writers of the same unit can interleave
**Evidence:** `tools/pipeline/store.py:52-62` — `tmp = path + ".tmp"`. Two wave-runner processes writing the same `<NN>/<lang>/<unit>.json` open the same tmp path concurrently (interleaved writes) before `os.replace`, producing a corrupt committed verdict. Cross-process atomicity of `replace` doesn't help when both writers share the tmp file.
**Fix:** `tmp = f"{path}.{os.getpid()}.tmp"` (or `tempfile.mkstemp(dir=d)`), then `os.replace`.

### 12. MINOR — `verify._lang_pack` silently falls back to built-ins on a *corrupt* language pack
**Evidence:** `tools/verify.py:43-57` — `except (OSError, ValueError): return None` swallows `json.JSONDecodeError`. A syntax error introduced into `tools/rules/ru.json` silently reverts verify to the hardcoded `LABELS`/`BANNED_RU` (lines 207-214) with zero warning — a behavior change exactly where the new pack mechanism is supposed to take over.
**Fix:** distinguish FileNotFoundError (fallback OK, per the Task-10b contract) from ValueError (print a WARN and exit non-zero, or at least warn loudly on stderr).

### 13. MINOR — QE config drift: two sources of truth for model/accelerator; `accelerator` and `max_tokens_per_segment` are unused
**Evidence:** `tools/rules/project.yaml:23-25` (`accelerator: mps`) vs `tools/validate/qe_config.json` (`"accelerator": "cpu"`, `"max_tokens_per_segment": 512`); `tools/pipeline/qe.py:43-54` — the inline runner hardcodes `gpus=0` and ignores both keys. The Mac will run CPU-only while the config claims MPS; test `test_project_yaml_backend_matches` (test_qe_parsing.py:58-61) pins only the model name.
**Fix:** make project.yaml the single source (qe_config.json holds only venv path/timeout), or read `accelerator` in the runner and map it to `gpus`/device.

### 14. MINOR — `retro_e_report`: totals span all chapters while `per_chapter` shows only the pinned five; verdict schema in files doesn't match the module that reads similar files
**Evidence:** `tools/validate/retro_e_report.py:47` globs every `tools/judge/factcheck/*-ru-*.json` but `per_chapter` is built from `CHAPTERS = ["10","11","13","28","30"]` (line 26, 75-80) — verdicts from any other chapter inflate `totals` and vanish from the breakdown. The on-disk verdict files (e.g. `tools/judge/factcheck/11-ru-10.json`) have `assertions` at top level and **no** `verdict` key, while `factcheck.write_result` (factcheck.py:136-145) and `store.build_payload` (store.py:39-49) produce a `{"verdict": {...}}` envelope — two different persisted shapes, only one of which the docstring of `retro_e_report` describes.
**Fix:** filter the glob to `CHAPTERS` (or include all chapters in `per_chapter`), and pick one verdict envelope (or document both) across wave-runner files and `write_result`.

### 15. MINOR — `style_check.check_text` re-loads and re-compiles the language pack on every call
**Evidence:** `tools/style_check.py:25-35` — `load_markers` does `json.load` + `re.compile` per invocation; `tools/validate/style_fp_audit.py:48,74,89,91` calls `check_text` once per fragment → thousands of redundant file reads/regex compiles per session build/report.
**Fix:** cache per `(lang, root)` with `functools.lru_cache` (return copies or treat markers as read-only) or hoist loading in the audit loops.

### 16. MINOR — `status.py` imports `time` inside the `__main__` guard: unusable as a module
**Evidence:** `tools/status.py:116-118` — `if __name__ == "__main__": import time; main()`. Any import of `status` followed by `main()` (the natural path for tests or a wave-runner dashboard call) raises `NameError: name 'time' is not defined` in `cell()` (line 97). Also `pass_columns` hardcodes `states["style"] = "SKIP"` (line 69) with a promise that "the wave runner fills it" — no such writer exists in the repo.
**Fix:** move `import time` to the top; wire the style column to `style_check` output files or drop the placeholder.

### 17. MINOR — `mutation_test.build_cases` trusts the spec without re-validating: unescaped `nn` interpolated into a regex
**Evidence:** `tools/validate/mutation_test.py:156-179` reads `mutations_seed42.json` and calls `book_path(nn, lang)` (lines 44-50) where `nn` is interpolated raw: `re.match(rf"{nn}-", p)`. A malformed/tampered spec (`nn` containing regex metacharacters or `../`) yields a crash (`re.error`), wrong-chapter reads, or (harmlessly, since list-args are used) odd argv — but `validate_spec` exists precisely to prevent this and is not invoked by `build_cases`. Not a security boundary (local, committed spec), purely robustness.
**Fix:** call `validate_spec()` (or at least `re.escape(nn)` + membership check against `CHAPTERS`) at the top of `build_cases`.

---

## Test-quality assessment (task item 5)

- Suite at HEAD: **94 tests, 0 failures** (`Ran 94 tests in 7.367s / OK`). The brief's "79 tests" is stale — the branch grew (test_golden_collect, test_plainness added by concurrent work).
- Tests assert real behavior, not smoke: exact kappa values (1/6 case, test_judge_metrics.py:31-36), confusion-matrix counts (test_judge_metrics.py:47-58), grounding drop reasons per class (test_factcheck.py:75-99), cap enforcement (test_style_check.py:81-87), CLI exit codes via real subprocess (test_style_check.py:103-117), SEED_REF pinning (test_mutation_spec.py:54-55).
- Skips are artifact-guarded and justified (spec/session/labels "not yet generated" → SkipTest with reason), e.g. test_mutation_spec.py:44-47, test_golden_collect.py:27-30. No silent passes found. Two skips on this machine are environment-honest (`test_run_scores_without_venv_raises_unavailable` runs its assertion here since the venv is absent).
- Mutation-kill quality: the tests would catch the reported bugs only partially — none covers `_line_of_collapsed` boundary behavior (finding 1), stamp pollution (finding 2), or unparseable-verdict gating (finding 4). Suggested additions are listed per finding.
- Known gap worth a test: `golden_collect._rate` mapping (`(a == 1) == native_first`) is correct for AB/BA (I traced both) but has no unit test over a synthetic manifest+answers fixture; it currently only runs against the live manifest (SkipTest-guarded).

## What checked out clean

- Subprocess usage in `mutation_test.run_verify` is list-form argv, no shell, tmp file created with `mkstemp` and removed in `finally` — no argument-injection vector beyond finding 17.
- API key handling (`judges.resolve_api_key`, judges.py:35-45): key never logged, never persisted; verdict payloads carry hashes, not secrets; `tools/judge/` gitignored.
- UTF-8 `encoding=` is present on every text `open()` across the reviewed files (CN/RU text safe); no `eval`/`exec` anywhere.
- `write_verdict`'s `os.replace` is atomic per write for single writers (finding 11 is only about the shared tmp name).
- `.gitignore` correctly covers `tools/judge/`, `tools/.qe/`, batch/session files; seeded results (golden_manifest, mutations_seed42, blind summary, retro findings) are committed as the protocol requires.
- `golden_pairs.py validate` passes at HEAD (60 pairs, 10 decoys, gen_ref consistent).
- `norm_text`/`cn_body` service-line handling for CRLF and unicode whitespace is sound (`splitlines` + `strip()`); no NFD/NFC hazard was demonstrated in the committed corpus.
