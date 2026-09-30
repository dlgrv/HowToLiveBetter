#!/usr/bin/env bash
# Canonical Hy-MT2 Q8 llama-server for HTLB unit translation (48 GB Mac).
#
# Locked defaults (2026-09-30):
#   -np 1   — one slot only; units are translated sequentially
#   -c 10240 — large enough for long units (prompt + gen). -c 4096 truncates
#              long notes/benefits and drops numbers (verify number_absent).
#
# Worst observed unit ≈ 5056 prompt + 3945 gen ≈ 9000 tokens → 10240 is the
# floor. Do not lower CTX without re-checking a long chapter (08 / 13 / 23).
# Override only for experiments: HTLB_LLAMA_CTX / HTLB_LLAMA_SLOTS.
set -euo pipefail

MODEL="${HTLB_LLAMA_MODEL:-$HOME/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf}"
LLAMA_CPP="${HTLB_LLAMA_CPP:-$HOME/llama.cpp}"
HOST="${HTLB_LLAMA_HOST:-127.0.0.1}"
PORT="${HTLB_LLAMA_PORT:-8080}"
CTX="${HTLB_LLAMA_CTX:-10240}"
SLOTS="${HTLB_LLAMA_SLOTS:-1}"

BIN="$LLAMA_CPP/build/bin/llama-server"
if [[ ! -x "$BIN" ]]; then
  echo "llama-server not found: $BIN" >&2
  exit 1
fi
if [[ ! -f "$MODEL" ]]; then
  echo "model not found: $MODEL" >&2
  exit 1
fi

if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "port $PORT busy — kill existing listener first" >&2
  exit 1
fi

echo "starting llama-server host=$HOST port=$PORT ctx=$CTX slots=$SLOTS" >&2

exec "$BIN" \
  -m "$MODEL" \
  --host "$HOST" --port "$PORT" \
  -ngl 99 \
  -fa on \
  -c "$CTX" \
  -b 512 -ub 512 \
  -np "$SLOTS" \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja
