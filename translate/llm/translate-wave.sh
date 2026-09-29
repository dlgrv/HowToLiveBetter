#!/usr/bin/env bash
# Translate a batch of chapters sequentially; units within a chapter run
# 2-at-a-time (llama-server -np 2). Usage: ./translate-wave.sh <lang> 16 17 18
set -uo pipefail
cd "$(dirname "$0")/../.." || exit

lang="${1:?usage: $0 <lang> <nn>…}"
shift
case "$lang" in
  ru|en|es|pt) ;;
  *)
    echo "unsupported lang: $lang (want ru|en|es|pt)" >&2
    exit 1
    ;;
esac

for raw in "$@"; do
  nn=$(printf '%02d' "$raw")
  echo "===== chapter $nn ($lang) ====="
  rm -rf "translate/runs/active/$lang/$nn"
  mkdir -p "translate/runs/active/$lang/$nn"
  cp -R "translate/digest/$nn/units" "translate/runs/active/$lang/$nn/"

  units=()
  while IFS= read -r u; do
    units+=("$u")
  done < <(
    for f in "translate/digest/${nn}/units/"*.md; do
      [[ -f "$f" ]] || continue
      base=$(basename "$f" .md)
      [[ "$base" == *gloss* ]] && continue
      printf '%s\n' "$base"
    done | sort
  )
  i=0
  while [ "$i" -lt "${#units[@]}" ]; do
    batch=("${units[@]:$i:2}")
    pids=()
    for u in "${batch[@]}"; do
      python3 translate/steps/translate/translate_unit.py --nn "$nn" --unit "$u" --lang "$lang" \
        --out-dir "translate/runs/active/$lang/$nn" > "/tmp/tu_${lang}_${nn}_${u}.log" 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do
      wait "$p" || echo "unit failed (see /tmp/tu_${lang}_${nn}_*.log)"
    done
    i=$((i + 2))
  done

  python3 translate/steps/assemble/assemble.py "$nn" "translate/runs/active/$lang/$nn" \
    "translate/runs/active/$lang/$nn/assembled.md" "$lang" 2>&1 | tail -1
  # H1 must keep the chapter number (CN '# NN. …'): the model often drops it.
  python3 - "$lang" "$nn" <<'PYFIX'
import re
import sys

lang, nn = sys.argv[1], sys.argv[2]
path = f"translate/runs/active/{lang}/{nn}/assembled.md"
text = open(path, encoding="utf-8").read()
first = text.splitlines()[0]
if first.startswith("# ") and not re.match(r"^# \d+\.", first):
    text = text.replace(first, f"# {int(nn)}. {first[2:]}", 1)
    open(path, "w", encoding="utf-8").write(text)
    print(f"h1 fixed: {int(nn)}.")
PYFIX
  python3 translate/steps/repair/repair_wave.py --nn "$nn" --lang "$lang" \
    --workdir "translate/runs/active/$lang/$nn" \
    --assembled "translate/runs/active/$lang/$nn/assembled.md" \
    --max-rounds 3 2>&1 | tail -1
  echo "== ch$nn ($lang) done"
done
