# HTLB local LLM adapter

OpenAI-compatible client: one digest unit → `translate/runs/.../units/*.md`.
Never write into `translate/digest/`.

Canonical wave workdir: `translate/runs/active/<lang>/<NN>/` (parent of `units/`).
Other wave names under `translate/runs/<wave>/...` are fine; `status.py` / `wave_pipeline.py` prefer `active`.

## Build llama.cpp (Metal) + download official Q8

```bash
git clone https://github.com/ggml-org/llama.cpp.git ~/llama.cpp
cd ~/llama.cpp
cmake -B build -DGGML_METAL=ON
cmake --build build --config Release -j

# ~30 GB — official Tencent GGUF only
hf download tencent/Hy-MT2-30B-A3B-GGUF Hy-MT2-30B-A3B-Q8_0.gguf \
  --local-dir ~/models/Hy-MT2-30B-A3B-GGUF
```

Needs `hy_v3` in llama.cpp. If load fails with `unknown model architecture: 'hy_v3'`, update/rebuild. Fallback on swap/OOM: official `Q4_K_M` from the same HF repo (ask before community quants).

## Server (Hy-MT2 Q8)

```bash
./build/bin/llama-server \
  -m ~/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf \
  --host 127.0.0.1 --port 8080 \
  -ngl 99 -fa on -c 4096 -b 512 -ub 512 -np 1 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja
```

Copy `.env.example` → `.env`: `HTLB_LLM_BASE_URL`, `HTLB_LLM_MODEL`, `HTLB_LLM_API_KEY`, `HTLB_LLM_TEMPERATURE=0.2`.
Client timeout 300s; up to 2 retries on connection/timeout only.

Swap models by changing `-m` and `HTLB_LLM_MODEL`, then restart (Q8 ↔ official Q4).

## Sequential units on Q8

On 48 GB Mac with Q8, **one** translate worker (`-np 1`). Parallel waves = cloud / Q4 only — see [translation-playbook.md](../../docs/pipeline/translation-playbook.md).

Do not run heavy Docker LT + browser thrash during Q8 waves if Activity Monitor shows sustained swap.

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
  --max-rounds 3            # --fallback-retranslate is ON by default
```

Per round: assemble → `verify --json` → locate fails to digest/TR units
(`translate/steps/repair/verify_issues.py`) → `repair_unit.py` (constrained prompt,
`translate/prompts/repair-unit.md`) → post-repair assert (value in
`norm_numbers` / stem count down) → fallback to full `translate_unit.py`
only if the assert still fails → re-assemble → re-verify. ≤ 8 dirty units
per round; never writes `translate/digest/` or `book/`; no style/LT inside the
loop. Exit codes: 0 = verify OK, 1 = exhausted/unrepairable/unlocated,
2 = LLM/infra. Preview the located map without LLM: add `--dry-locate`.

## Polish wave (after green verify)

```bash
make polish CH=01 LANG=ru   # Laya :8090 + Hy-MT2 :8080 OK together
# or: python3 translate/steps/polish/polish_wave.py --nn 01 --lang ru \
#       --workdir translate/runs/active/ru/01 --assembled book/ru/01-….md
```

Clarity on unit plain-terms → `simplify_unit.py` (`simplify-plain.md`) →
assemble → verify. ≤3 rounds. Exit 0 leftover `непонятно`, 1 `RUN_REPAIR`,
2 Laya down. Client is still `translate/llm/client.py`.

Assemble workdir = parent of `units/`. One script for all langs: `assemble.py <NN> <workdir> <out.md> [lang]` (`lang` defaults to `ru`).

Ops detail: this README + [start-llama-server.sh](../steps/translate/start-llama-server.sh) + [translation-playbook.md](../../docs/pipeline/translation-playbook.md) (§ Ops).
