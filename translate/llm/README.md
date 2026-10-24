# HTLB LLM adapter (third-party API)

OpenAI-compatible client: one digest unit → `translate/runs/.../units/*.md`.
Never write into `translate/digest/`.

Canonical wave workdir: `translate/runs/active/<lang>/<NN>/` (parent of `units/`).
Other wave names under `translate/runs/<wave>/...` are fine; `status.py` / `wave_pipeline.py` prefer `active`.

## Provider config (`.env`)

Translation runs on **third-party (cloud) OpenAI-compatible APIs only**. Local
llama.cpp / Hy-MT2 serving is retired — do not reintroduce it.

Copy `.env.example` → `.env` and fill in:

| Var | Meaning |
|---|---|
| `HTLB_LLM_BASE_URL` | Provider base URL, e.g. `https://api.example.com/v1` |
| `HTLB_LLM_API_KEY` | Provider API key |
| `HTLB_LLM_MODEL` | Model id for unit translation |
| `HTLB_LLM_TEMPERATURE` | `0.2` — factual unit translation; card default 0.7 is creative |

Client timeout 300s; up to 2 retries on connection/timeout only. One unit per
request; parallel waves are per-provider capacity decisions (see
[translation-playbook.md](../../docs/pipeline/translation-playbook.md) §3).

## Wave driver

```bash
./translate/llm/translate-wave.sh <lang> 16 17 18
```

Copies digest units into the canonical workdir, translates them one at a time,
re-adds the chapter number to H1, then runs one repair round.

## Translate one unit

```bash
python3 translate/steps/digest/make_digest.py 01
mkdir -p translate/runs/active/ru/01
cp -R translate/digest/01/units translate/runs/active/ru/01/

python3 translate/steps/translate/translate_unit.py --nn 01 --unit 01 --lang ru \
  --out-dir translate/runs/active/ru/01

python3 translate/steps/assemble/assemble.py 01 translate/runs/active/ru/01 /tmp/htlb-01-ru.md
python3 translate/steps/verify/verify.py 01 --lang ru --file /tmp/htlb-01-ru.md
```

## Repair wave (verify FAIL → auto-fix → re-verify)

When `verify.py` HARD-fails on `number_absent` / `banned_calque`, run the
repair loop instead of hand-editing units:

```bash
python3 translate/steps/repair/repair_wave.py --nn 01 --lang ru \
  --workdir translate/runs/active/ru/01 \
  --assembled translate/runs/active/ru/01/assembled.md \
  --max-rounds 3
# or: make repair CH=01 LANG=ru
```

**Numbers are mechanical-first** (`steps/repair/mechanical.py`):

- Locale render: es/pt/ru use decimal comma (`0,499`); bare `0.499` folds to
  `499` and will not clear verify.
- Safe inject into Notes uses `〔N〕` — never space-separated `2022 523`
  (thousands-fold glues them to `2022523`).
- Mangled `g = 0499` is rewritten to the locale form before inject.
- Multiline empty fields (`- Cost:\n  …`) are collapsed after every MT/repair
  draft; `validate_unit` rejects bare `- Label:` lines.

LLM re-prompt and fallback `translate_unit` are **skipped** for
`number_absent`-only rounds (absolute digits oscillate across LLM re-prompts).
`banned_calque` still uses `repair-unit.md` + optional fallback retranslate.

Per round: assemble → `verify --json` → locate → `repair_unit.py` →
re-assemble → re-verify. ≤ 8 dirty units/round; never writes
`translate/digest/` or (from repair_wave itself) `book/`. Exit: 0 OK,
1 exhausted/unrepairable, 2 LLM/infra. Preview: `--dry-locate`.

Assemble workdir = parent of `units/`. One script for all langs: `assemble.py <NN> <workdir> <out.md> [lang]` (`lang` defaults to `ru`).

Ops detail: this README + [translation-playbook.md](../../docs/pipeline/translation-playbook.md) (§ Ops).
