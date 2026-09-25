#!/usr/bin/env bash
# Translate a batch of chapters sequentially, but units WITHIN a chapter
# 2-at-a-time (llama-server runs -np 2 slots). Usage: ./translate-wave.sh 16 17 18
set -uo pipefail
cd "$(dirname "$0")/../.."   # repo root

WAVE_JOBS="${WAVE_JOBS:-2}"

for nn in "$@"; do
  echo "===== chapter $nn ====="
  rm -rf "tools/runs/active/ru/$nn"
  mkdir -p "tools/runs/active/ru/$nn"
  cp -R "tools/digest/$nn/units" "tools/runs/active/ru/$nn/"

  units=($(ls tools/digest/$nn/units/ | grep -v gloss | sed 's/.md//' | sort))
  i=0
  # 2-at-a-time loop (WAVE_JOBS parallel translate_unit.py processes)
  while [ $i -lt ${#units[@]} ]; do
    batch=("${units[@]:$i:2}")
    pids=()
    for u in "${batch[@]}"; do
      python3 tools/llm/translate_unit.py --nn "$nn" --unit "$u" --lang ru \
        --out-dir "tools/runs/active/ru/$nn" > "/tmp/tu_${nn}_${u}.log" 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p" || echo "unit failed (see /tmp/tu_${nn}_*.log)"; done
    i=$((i+2))
  done

  python3 tools/assemble.py "$nn" "tools/runs/active/ru/$nn" \
    "tools/runs/active/ru/$nn/assembled.md" 2>&1 | tail -1
  python3 tools/llm/repair_wave.py --nn "$nn" --lang ru \
    --workdir "tools/runs/active/ru/$nn" \
    --assembled "tools/runs/active/ru/$nn/assembled.md" \
    --max-rounds 3 2>&1 | tail -1
  echo "== ch$nn done"
done
