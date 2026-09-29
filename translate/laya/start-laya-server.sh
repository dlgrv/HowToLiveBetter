#!/usr/bin/env bash
# Self-host Laya multilingual checkpoint on loopback :8090 (HTLB_LAYA_PORT).
# Fine alongside Hy-MT2 on :8080 (polish uses both).
# Pin multilingual only — never preload the English-only checkpoint as default.
set -euo pipefail

HOST="${HTLB_LAYA_HOST:-127.0.0.1}"
PORT="${HTLB_LAYA_PORT:-8090}"
MODEL="${HTLB_LAYA_MODEL:-multilingual}"

if [[ "$MODEL" != "multilingual" ]]; then
  echo "HTLB_LAYA_MODEL must be multilingual (got: $MODEL)" >&2
  exit 1
fi

if ! command -v laya-serve >/dev/null 2>&1; then
  echo "laya-serve not found — pip install -r translate/laya/requirements-laya.txt" >&2
  exit 1
fi

if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "port $PORT busy — kill existing listener first" >&2
  exit 1
fi

export LAYA_HOST="$HOST"
export LAYA_PORT="$PORT"
export LAYA_PRELOAD="${LAYA_PRELOAD:-1}"
export LAYA_MODELS=multilingual

if [[ -n "${HTLB_LAYA_DEVICE:-}" ]]; then
  export LAYA_DEVICE="$HTLB_LAYA_DEVICE"
fi

echo "laya-serve multilingual on http://${HOST}:${PORT}" >&2
exec laya-serve
