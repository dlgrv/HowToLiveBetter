#!/usr/bin/env bash
# Canonical Hy-MT2 Q8 llama-server flags for HTLB unit translation (48 GB Mac).
# Context 2026-09-25: -np 2 x 10240 (variant A) — 2 parallel unit slots.
# Worst observed unit: 5056 prompt + 3945 gen ≈ 9000 tokens → 10240 safe.
# Unit 00 glossary prompt ≈4427 tokens (16384 was sized for it; 10240 still covers).
set -euo pipefail

MODEL="${HTLB_LLAMA_MODEL:-$HOME/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf}"
LLAMA_CPP="${HTLB_LLAMA_CPP:-$HOME/llama.cpp}"
HOST="${HTLB_LLAMA_HOST:-127.0.0.1}"
PORT="${HTLB_LLAMA_PORT:-8080}"
# Locked default — override only with HTLB_LLAMA_CTX if experimenting
CTX="${HTLB_LLAMA_CTX:-10240}"
SLOTS="${HTLB_LLAMA_SLOTS:-2}"

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
