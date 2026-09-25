#!/usr/bin/env bash
# Canonical Hy-MT2 Q8 llama-server flags for HTLB unit translation (48 GB Mac).
# Context locked 2026-09-24: 16384 — covers unit-00 full glossary gloss + prompt + reply;
# 4096 was too tight (unit 00 ≈4427 prompt tokens).
set -euo pipefail

MODEL="${HTLB_LLAMA_MODEL:-$HOME/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf}"
LLAMA_CPP="${HTLB_LLAMA_CPP:-$HOME/llama.cpp}"
HOST="${HTLB_LLAMA_HOST:-127.0.0.1}"
PORT="${HTLB_LLAMA_PORT:-8080}"
# Locked default — override only with HTLB_LLAMA_CTX if experimenting
CTX="${HTLB_LLAMA_CTX:-16384}"

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
  -np 1 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja
