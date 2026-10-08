#!/usr/bin/env bash
# Rsync local .publish/ to a release dir; flip current symlink (nginx root).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SOURCE="${SOURCE:-$REPO_ROOT/.publish}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_HOST="${DEPLOY_HOST:-dlgrv}"
REMOTE_ROOT="${REMOTE_ROOT:-/var/www/book.dlgrv.com}"
RELEASES="${REMOTE_RELEASES:-$REMOTE_ROOT/releases}"

if [[ ! -d "$SOURCE" ]]; then
  echo "Missing artifact dir: $SOURCE (run: make pages-artifact)" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_RELEASE="$RELEASES/$STAMP"

echo "==> rsync $SOURCE/ → $DEPLOY_USER@$DEPLOY_HOST:$REMOTE_RELEASE/"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "mkdir -p '$RELEASES'"
rsync -az --delete --human-readable "$SOURCE/" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_RELEASE/"

echo "==> activate release (symlink current)"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "ln -sfn '$REMOTE_RELEASE' '$REMOTE_ROOT/current'"

# Keep last 5 releases
ssh "$DEPLOY_USER@$DEPLOY_HOST" "ls -1dt '$RELEASES'/* 2>/dev/null | tail -n +6 | xargs -r rm -rf" || true

echo "deploy-book ok: $STAMP"
