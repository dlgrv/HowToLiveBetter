#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$(mktemp -d)"
trap 'kill ${PID:-} 2>/dev/null || true; rm -rf "$DIR"' EXIT
export HTLB_DATA_DIR="$DIR/pb_data"
export HTLB_VOTE_SALT=smoke
export HTLB_CORS_ORIGINS=http://127.0.0.1:8000
export HTLB_LISTEN=127.0.0.1:18090
cd "$ROOT"
CGO_ENABLED=0 go build -o "$DIR/htlb-api" ./cmd/htlb-api
"$DIR/htlb-api" serve --http=127.0.0.1:18090 &
PID=$!
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:18090/api/htlb/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
curl -fsS "http://127.0.0.1:18090/api/htlb/v1/health" | grep -q '"ok":true'
TOKEN=$(curl -fsS -X POST "http://127.0.0.1:18090/api/htlb/v1/guest/session" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
code=$(curl -s -o /dev/null -w '%{http_code}' -H "X-HTLB-Sync: $TOKEN" "http://127.0.0.1:18090/api/htlb/v1/bookmarks")
test "$code" = "200"
code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:18090/api/htlb/v1/bookmarks")
test "$code" = "401"
# useful: public GET counts; guest POST requires sign-in
curl -fsS "http://127.0.0.1:18090/api/htlb/v1/useful?entryIds=smoke-e1" | grep -q '"count"'
code=$(curl -s -o /dev/null -w '%{http_code}' -H "X-HTLB-Sync: $TOKEN" -H "Content-Type: application/json" \
  -d '{"entryId":"smoke-e1","useful":true}' "http://127.0.0.1:18090/api/htlb/v1/useful")
test "$code" = "401"
echo "smoke ok"
