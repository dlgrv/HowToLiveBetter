# HTLB local LLM adapter

OpenAI-compatible client: one digest unit → `tools/runs/.../units/*.md`.
Never write into `tools/digest/`.

Canonical wave workdir: `tools/runs/active/<lang>/<NN>/` (parent of `units/`).
Other wave names under `tools/runs/<wave>/...` are fine; `status.py` / `wave_pipeline.py` prefer `active`.

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

On 48 GB Mac with Q8, **one** translate worker (`-np 1`). Parallel waves = cloud / Q4 only — see [docs/translation-playbook.md](../../docs/translation-playbook.md).

Do not run heavy Docker LT + browser thrash during Q8 waves if Activity Monitor shows sustained swap.

## Translate one unit

```bash
python3 tools/make_digest.py 01
mkdir -p tools/runs/active/ru/01
cp -R tools/digest/01/units tools/runs/active/ru/01/

python3 tools/llm/translate_unit.py --nn 01 --unit 01 --lang ru \
  --out-dir tools/runs/active/ru/01

python3 tools/assemble.py 01 tools/runs/active/ru/01 /tmp/htlb-01-ru.md
python3 tools/verify.py 01 --lang ru --file /tmp/htlb-01-ru.md
```

Assemble workdir = parent of `units/`. RU → `assemble.py`; EN → `assemble_en.py`; ES → `assemble_es.py`.

Full plan: [docs/superpowers/plans/2026-09-24-hy-mt2-local-llamacpp.md](../../docs/superpowers/plans/2026-09-24-hy-mt2-local-llamacpp.md).
