# Hy-MT2-30B-A3B local (llama.cpp GGUF Q8) → HTLB unit translation

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (preferred) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run **official** Tencent **Hy-MT2-30B-A3B** locally on MacBook Pro **M5 Pro / 48 GB** via **llama.cpp** + **Q8_0 GGUF**, expose OpenAI-compatible API, plug into HTLB as swappable LLM backend (same `.env` as CometAPI later).

**Locked choice (user 2026-09-24):**  
`tencent/Hy-MT2-30B-A3B-GGUF` → **`Hy-MT2-30B-A3B-Q8_0.gguf` (~32 GB)** — max local fidelity.  
**Fallback ladder (in order):** (1) drop `-c` 4096→2048; (2) official `Q4_K_M` from same HF repo if listed; (3) **stop and ask** before any community quant (APEX etc. = break-glass only).

**Architecture:**

```text
tools/digest/<NN>/units/*.md  (ZH, read-only)
        │
        ▼
llama-server (Metal, Q8, -np 1)  ← 127.0.0.1:8080/v1
        │
        ▼
tools/llm/translate_unit.py → tools/runs/<wave>/<lang>/<NN>/units/
        │
        ▼
assemble.py <NN> <workdir> <out.md>   # workdir = parent of units/; blocks from digest
        │
        ▼
verify → factcheck (exit 0/1/2) → style → LT → plainness → human
```

Never whole chapters. Never write into `tools/digest/`.

**Tech stack:** Self-built llama.cpp with **Metal** (`cmake -DGGML_METAL=ON`) from [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) **on install day** (needs `hy_v3`). Homebrew bottles often lag — Brew is optional only after `llama-cli -m …` loads Q8. Official HF GGUF + `.env` `HTLB_LLM_*`.

**Hardware (48 GB) — RAM budget (order-of-magnitude):**

| Piece | Approx |
|---|---|
| Q8_0 weights | ~32 GB |
| KV cache (`-c 4096`, q8_0 K/V, `-np 1`) | ~1–3 GB |
| macOS + Cursor/Chrome/Docker LT | ~8–12 GB |
| **Headroom** | **tight (~3–7 GB)** — close heavy apps |

**Ops rule (hard):** local Q8 = **strictly sequential units** (one translate worker). Playbook “5–6 parallel agents” applies to **cloud** waves only. Parallel only after Q4 (or cloud). See [translation-playbook.md](../../translation-playbook.md).

**Official vs not:** GGUF from `tencent/Hy-MT2-30B-A3B-GGUF` is **Tencent-published**. Needs llama.cpp with `hy_v3` (HF card STQ notes; historically ~b9993+ — do not treat build number as eternal truth).

**License:** Tencent Hy community — read on HF card.

**Related:** [plain-language pipeline](2026-09-23-plain-language-pipeline.md), `.env.example`.  
**Filename:** was `…-mlx.md`; content is llama.cpp GGUF (MLX superseded).

---

## File map

| Path | Role |
|---|---|
| `.env` / `.env.example` | local OpenAI-compatible URL + model id + sampling |
| `.gitignore` | must include `tools/runs/` |
| `tools/llm/README.md` | download, build llama.cpp, start server, swap models |
| `tools/llm/client.py` | env-driven `POST /v1/chat/completions` |
| `tools/llm/translate_unit.py` | one digest unit → one run file |
| `tools/validate/tests/test_llm_client.py` | mocked HTTP + path refuse |
| `tools/runs/` | gitignored wave outputs |
| Models | `~/models/…` or `HF_HUB_CACHE` (not in git); prefer `--local-dir` only — avoid duplicate ~32 GB snapshots |

---

## CORRECT ORDER

```text
1. llama-server with Q8_0 (stays up)
2. make_digest.py <NN>
3. translate_unit.py per unit (sequential on Q8) → tools/runs/active/<lang>/<NN>/units/
4. assemble.py <NN> tools/runs/active/<lang>/<NN> <out.md>
   # workdir = parent of units/  (NOT …/units)
   # CN blocks always from tools/digest/<NN>/blocks.json
5. verify.py
6. factcheck.py — exit 0 = pass; 1 = gate fail / ungrounded / issues;
   2 = judge unavailable (stop or inject --stdin-verdict). ES factcheck N/A.
7. style → lt → plainness → human
```

Optional `simplify-plain.md` pass only **after** verify, **before** or instead of a second translate — never before factcheck on a candidate that skipped verify.

---

### Task 1: Disk + llama.cpp with hy_v3

- [ ] Free disk ≥ **70 GB** (32 GB GGUF + HF/tooling slack; or set `HF_HUB_CACHE` / use `--local-dir` only so weights are not duplicated)
- [ ] **Primary:** clone + Metal build (not Brew-first):

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_METAL=ON
cmake --build build --config Release -j
# binaries: build/bin/llama-server, llama-cli
```

- [ ] **Done for hy_v3:** either Q8 loads, or fail with exact `unknown model architecture: 'hy_v3'` (then update llama.cpp and rebuild). Build numbers (e.g. b9993) are hints only — see HF model card STQ notes.

**Done when:** Metal `llama-server` / `llama-cli` present; hy_v3 gate above understood.

---

### Task 2: Download official Q8_0

```bash
# ~32 GB — official Tencent GGUF (single local-dir; no second snapshot)
# hf download …  (newer CLI) or huggingface-cli download …
huggingface-cli download tencent/Hy-MT2-30B-A3B-GGUF \
  Hy-MT2-30B-A3B-Q8_0.gguf \
  --local-dir ~/models/Hy-MT2-30B-A3B-GGUF
```

- [ ] Confirm filename on HF file list if renamed
- [ ] Note path for `.env` / server `-m`

**Done when:** `ls -lh …/Hy-MT2-30B-A3B-Q8_0.gguf` ≈ 32 GB.

---

### Task 3: Smoke CLI (no server)

Official-style prompt (no default system prompt on Hy-MT2):

```bash
./build/bin/llama-cli \
  -m ~/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf \
  -ngl 99 \
  --jinja \
  -n 128 \
  -p "Translate the following segment into Russian, without additional explanation: 安全带能降低前排死亡风险。"
```

**Sampling for HTLB factual units (default in client):** `temperature=0.2`, `top_p=1.0`.  
Tencent card default `temperature=0.7` is for general/creative use — **do not** use as translate default (invites paraphrase vs numbers).

- [ ] Watch Activity Monitor: if **swap** heavy → stop; follow fallback ladder
- [ ] Eyeball: Russian, no invented numbers

**Done when:** Completion returns without OOM.

---

### Task 4: OpenAI-compatible `llama-server` (macOS-optimal)

**Stack choice:** self-built llama.cpp + Metal. LM Studio / Ollama often lag on `hy_v3`.

**Optimal single-user flags on M5 Pro 48 GB + Q8 (~32 GB weights):**

```bash
# Optional / experimental once per boot — raise Metal wired limit (~70% of 48 GB ≈ 33600 MB).
# Not required for Done. Revert: sudo sysctl iogpu.wired_limit_mb=<previous or omit>.
# sudo sysctl iogpu.wired_limit_mb=33600

./build/bin/llama-server \
  -m ~/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf \
  --host 127.0.0.1 --port 8080 \
  -ngl 99 \
  -fa on \
  -c 4096 \
  -b 512 -ub 512 \
  -np 1 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja
```

| Flag | Why |
|---|---|
| `-ngl 99` | All layers on Metal GPU (unified memory) |
| `-fa on` | Flash attention — less KV RAM, faster |
| `-c 4096` | Unit prompts are small; huge `-c` wastes RAM on Q8 |
| `-np 1` | One slot only — parallel slots multiply KV |
| `-b/-ub 512` | Modest batches; bump if prompt-eval is slow and RAM free |
| `--cache-type-k/v q8_0` | Smaller KV than f16 — **quality tradeoff** for RAM; keep on 48 GB |
| **Avoid** `--mlock` on Q8@48GB | Can starve macOS → swap |
| **Avoid** `-np >1` / multi-agent translate | Until Q4 or cloud |

**KV / OOM ladder:** drop `-c` 4096→2048 → official Q4 file → only then consider f16 KV if headroom appears (unlikely on Q8@48GB).

```bash
# Sync model id with server
curl -s http://127.0.0.1:8080/v1/models | head -c 800
# Set HTLB_LLM_MODEL to the returned id (server may ignore id; client still sends one)

curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Hy-MT2-30B-A3B-Q8_0",
    "messages": [{"role":"user","content":"Translate into English, without additional explanation: 系安全带。"}],
    "temperature": 0.2,
    "max_tokens": 64
  }' | head -c 600
```

`.env`:

```bash
HTLB_LLM_BASE_URL=http://127.0.0.1:8080/v1
HTLB_LLM_MODEL=Hy-MT2-30B-A3B-Q8_0
HTLB_LLM_API_KEY=local
HTLB_LLM_TEMPERATURE=0.2
```

Note: OpenAI chat API exposes `temperature` / `top_p`; `repetition_penalty` from the card is **not** always mapped on `/v1/chat/completions` — do not assume parity with llama-cli flags.

**Done when:** curl OK; `/v1/models` checked; `.env` points at localhost Q8 with translate temperature 0.2.

---

### Task 5.0: gitignore `tools/runs/` (before any translate write)

- [ ] Add `tools/runs/` to `.gitignore`
- [ ] **Done:** `git check-ignore -v tools/runs/x` shows a match

---

### Task 5: Thin client + unit CLI

Create `tools/llm/` (does not exist yet):

**`client.py`**
- Read `HTLB_LLM_BASE_URL`, `HTLB_LLM_MODEL`, `HTLB_LLM_API_KEY` (required non-empty), optional `HTLB_LLM_TEMPERATURE` (default `0.2`)
- `POST {BASE}/chat/completions` with timeout (e.g. 300s)
- Non-2xx, empty `choices[0].message.content`, or transport error → exit ≠ 0 (1–2 retries on connection reset / timeout only; never silent write)
- Document: model string may be ignored by llama-server; still send non-empty id from env

**`translate_unit.py`**
- Args: `--nn NN` `--unit UU` `--lang {ru,en,es}` `--out-dir DIR`
- **`--out-dir` = assemble workdir** (parent of `units/`), e.g. `tools/runs/smoke/ru/01`. Writer **always** creates/writes `{out-dir}/units/{UU}.md` with zero-padded filenames (`01.md`, not `1.md`).
- Read **only** `tools/digest/<NN>/units/<UU>.md` + `tools/glossary.json` / prompt gloss as needed
- Load prompt template from `tools/prompts/translate-unit.md`; fill CN unit + lang + gloss; one completion
- **One unit per call**; preserve `§TAG§` / `§SRC§` placeholders verbatim
- **Refuse** if `Path(out-dir).resolve()` is under `tools/digest/` (exit ≠ 0, no write)
- Prefer write via temp file then rename (safe if client reused under parallel later)
- Never feed whole `book/*.md`

**Assemble by lang:** RU → `assemble.py`; EN → `assemble_en.py`; ES → `assemble_es.py`. Same workdir contract.

**`README.md`:** start server command, Q8 vs Q4 swap, sequential ops rule, link to playbook.

**Round-trip Done checklist:**
```bash
# digest must exist: python3 tools/make_digest.py 01
mkdir -p tools/runs/smoke/ru/01
cp -R tools/digest/01/units tools/runs/smoke/ru/01/
# server up; overwrite one unit (others stay ZH placeholders for assemble structure)
python3 tools/llm/translate_unit.py --nn 01 --unit 01 --lang ru \
  --out-dir tools/runs/smoke/ru/01
# writes tools/runs/smoke/ru/01/units/01.md
python3 tools/assemble.py 01 tools/runs/smoke/ru/01 /tmp/htlb-01-ru.md
python3 tools/verify.py 01 --lang ru --file /tmp/htlb-01-ru.md
# expect exit 0 / lost tags&sources = 0 (untranslated sibling units may still flag — OK for smoke if unit 01 clean)
```

Model swap = `.env` + restart server with different `-m` (Q8 → official Q4 path).

**Done when:** seed + translate unit `01` RU → assemble → `verify … --file` runs without inventing flags.

---

### Task 5b: Unit tests (mocked HTTP)

- [ ] `tools/validate/tests/test_llm_client.py`:
  - mock HTTP 200 → content returned
  - non-2xx / empty content → raises / exit ≠ 0
  - missing env → clear failure
  - out path = `{out_dir}/units/{unit}.md`; refuse when `out_dir` resolves under `tools/digest/`
- [ ] Skeleton (write failing tests first):

```python
def test_chat_ok(monkeypatch): ...
def test_refuse_digest_outdir(tmp_path): ...
```

- [ ] Live smoke against localhost marked manual / `@slow` (not required in default CI)

**Done when:** `python3 -m pytest tools/validate/tests/test_llm_client.py -q` passes offline.

---

### Task 5c: Q8 stability gate (before whole-chapter waves)

- [ ] Run **3 sequential** units with Activity Monitor open
- [ ] No sustained heavy swap; machine usable
- [ ] If gate fails → official Q4, re-smoke; **do not** parallelize Q8 with Docker LT + browser + 5 agents

**Done when:** 3 sequential units green without thrash.

---

### Task 6: Quality pack reality

Hy-MT2 = translation. Still run quality pack.

**Pilot (concrete):**
- Chapters `01`, `02`, `03` RU
- Workdirs: `tools/runs/pilot-q8/ru/01` … `03`
- After assemble+verify: factcheck (0/1/2); style; LT; plainness
- Compare sample units to existing `book/ru/` (human eyeball; not auto-overwrite `book/`)

Order reminder: verify → factcheck → style → LT → plainness. Optional simplify after verify.

---

## Out of scope

- Unofficial MLX community quants as primary (superseded by official GGUF Q8)
- BF16 full weights on 48 GB
- Mass `book/` rewrite
- CometAPI/Gemini (same client later)
- Parallel Q8 unit waves on this Mac

---

## Execution handoff

Plan path: `docs/superpowers/plans/2026-09-24-hy-mt2-local-llamacpp.md`

**Recommended:** Subagent-Driven Development after Task 4 smoke is green (server + curl). Inline for Tasks 1–4 ops is fine.
