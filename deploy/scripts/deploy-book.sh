#!/usr/bin/env bash
# Rsync local .publish/ to a release dir; flip current symlink (nginx root);
# ping IndexNow with the changed URLs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SOURCE="${SOURCE:-$REPO_ROOT/.publish}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_HOST="${DEPLOY_HOST:-dlgrv}"
REMOTE_ROOT="${REMOTE_ROOT:-/var/www/book.dlgrv.com}"
RELEASES="${REMOTE_RELEASES:-$REMOTE_ROOT/releases}"
SITE_HOST="book.dlgrv.com"
INDEXNOW_KEY_FILE="$(find "$REPO_ROOT/deploy/indexnow" -maxdepth 1 -name '*.txt' -type f -print -quit 2>/dev/null || true)"

if [[ ! -d "$SOURCE" ]]; then
  echo "Missing artifact dir: $SOURCE (run: make pages-artifact)" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_RELEASE="$RELEASES/$STAMP"

echo "==> rsync $SOURCE/ → $DEPLOY_USER@$DEPLOY_HOST:$REMOTE_RELEASE/"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "mkdir -p '$RELEASES'"
CHANGED_LIST="$(mktemp)"
rsync -az --delete --human-readable --out-format="%n" "$SOURCE/" \
  "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_RELEASE/" | grep -v '/$' > "$CHANGED_LIST" || true

echo "==> activate release (symlink current)"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "ln -sfn '$REMOTE_RELEASE' '$REMOTE_ROOT/current'"

# Keep last 5 releases
ssh "$DEPLOY_USER@$DEPLOY_HOST" "ls -1dt '$RELEASES'/* 2>/dev/null | tail -n +6 | xargs -r rm -rf" || true

# IndexNow: notify participating search engines (Yandex, Bing, …) about
# changed content URLs. Key file is committed at deploy/indexnow/<key>.txt
# and already shipped to the docroot inside the artifact.
if [[ -n "$INDEXNOW_KEY_FILE" && -s "$CHANGED_LIST" ]]; then
  KEY="$(basename "$INDEXNOW_KEY_FILE" .txt)"
  mapfile -t URLS < <(
    grep -E '\.(md|html|txt|xml)$' "$CHANGED_LIST" \
      | grep -vE '^(assets/|login/|privacy/|useful/)' \
      | sed "s|^|https://$SITE_HOST/|"
  )
  # Always include the hub so search engines refresh the sitemap entry point.
  URLS+=("https://$SITE_HOST/")
  if [[ ${#URLS[@]} -gt 0 ]]; then
    PAYLOAD="$(jq -nc --arg host "$SITE_HOST" --arg key "$KEY" \
      --arg keyloc "https://$SITE_HOST/$KEY.txt" \
      --args "${URLS[@]}" '{host:$host, key:$key, keyLocation:$keyloc, urlList:$ARGS.positional}')"
    echo "==> indexnow: pinging ${#URLS[@]} urls"
    if ! curl -sS -f -X POST "https://api.indexnow.org/indexnow" \
        -H 'Content-Type: application/json; charset=utf-8' \
        -d "$PAYLOAD" >/dev/null; then
      echo "indexnow: ping failed (non-fatal)" >&2
    fi
  fi
else
  echo "indexnow: skipped (no key file or no changed files)"
fi
rm -f "$CHANGED_LIST"

echo "deploy-book ok: $STAMP"
