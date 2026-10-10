#!/usr/bin/env bash
# Release htlb-api binary on the server: stop → backup → rsync → restart → health (rollback on failure).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BINARY_LOCAL="${BINARY_LOCAL:-$REPO_ROOT/api/bin/htlb-api}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_HOST="${DEPLOY_HOST:-dlgrv}"
REMOTE_OPT="${REMOTE_OPT:-/opt/htlb-api}"
REMOTE_BIN="$REMOTE_OPT/htlb-api"
REMOTE_DATA="$REMOTE_OPT/pb_data"
REMOTE_RELEASES="$REMOTE_OPT/releases"
HEALTH_URL="${HEALTH_URL:-https://api.dlgrv.com/api/htlb/v1/health}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_RELEASE="$REMOTE_RELEASES/$STAMP"

usage() {
  cat <<EOF
Usage: $0 [deploy|rollback [release-dir]|health]

  deploy   — default: stop, backup pb_data, install binary, restart, smoke health
  rollback — swap to previous release binary and restart
  health   — curl health endpoint only

Env: BINARY_LOCAL DEPLOY_USER DEPLOY_HOST HEALTH_URL
EOF
}

remote() {
  ssh "$DEPLOY_USER@$DEPLOY_HOST" "$@"
}

health_check() {
  local i
  for i in $(seq 1 40); do
    if curl -fsS "$HEALTH_URL" | grep -q '"ok":true'; then
      echo "health ok: $HEALTH_URL"
      return 0
    fi
    sleep 0.5
  done
  echo "health failed: $HEALTH_URL" >&2
  return 1
}

backup_pb_data() {
  echo "==> backup pb_data"
  remote "sudo mkdir -p '$REMOTE_OPT/backups' && sudo tar -czf '$REMOTE_OPT/backups/pb_data-$STAMP.tgz' -C '$REMOTE_OPT' pb_data"
}

# Service User=htlb needs traverse on WorkingDirectory=/opt/htlb-api (755).
# deployer owns releases/ for rsync; pb_data stays htlb:htlb.
fix_runtime_perms() {
  remote "sudo chown root:htlb '$REMOTE_OPT' \
    && sudo chmod 755 '$REMOTE_OPT' \
    && sudo chown -R htlb:htlb '$REMOTE_DATA' \
    && sudo chown -R '$DEPLOY_USER:$DEPLOY_USER' '$REMOTE_RELEASES' \
    && sudo chmod 755 '$REMOTE_RELEASES' \
    && sudo chown -h htlb:htlb '$REMOTE_BIN'"
}

do_deploy() {
  if [[ ! -f "$BINARY_LOCAL" ]]; then
    echo "Missing binary: $BINARY_LOCAL (run: make api-build)" >&2
    exit 1
  fi

  echo "==> stop htlb-api"
  remote "sudo systemctl stop htlb-api.service" || true

  backup_pb_data

  echo "==> rsync binary → $REMOTE_RELEASE/htlb-api"
  remote "mkdir -p '$REMOTE_RELEASE' '$REMOTE_RELEASES'"
  rsync -az "$BINARY_LOCAL" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_RELEASE/htlb-api"
  remote "chmod 0755 '$REMOTE_RELEASE/htlb-api'"

  echo "==> activate binary"
  remote "sudo ln -sfn '$REMOTE_RELEASE/htlb-api' '$REMOTE_BIN'"
  fix_runtime_perms

  echo "==> start htlb-api"
  remote "sudo systemctl start htlb-api.service"

  if health_check; then
    echo "deploy-api ok: $STAMP"
    remote "ls -1dt '$REMOTE_RELEASES'/* 2>/dev/null | tail -n +6 | xargs -r sudo rm -rf" || true
    return 0
  fi

  echo "==> deploy failed — rolling back to previous release" >&2
  do_rollback_auto || true
  exit 1
}

do_rollback_auto() {
  local prev
  prev="$(remote "ls -1dt '$REMOTE_RELEASES'/*/htlb-api 2>/dev/null | sed -n '2p'")" || true
  if [[ -z "$prev" ]]; then
    echo "no previous release to rollback" >&2
    return 1
  fi
  do_rollback "$prev"
}

do_rollback() {
  local target="${1:-}"
  if [[ -z "$target" ]]; then
    target="$(remote "ls -1dt '$REMOTE_RELEASES'/*/htlb-api 2>/dev/null | sed -n '2p'")"
  fi
  if [[ -z "$target" ]]; then
    echo "rollback: no target release" >&2
    exit 1
  fi
  echo "==> rollback binary → $target"
  remote "sudo systemctl stop htlb-api.service" || true
  remote "sudo ln -sfn '$target' '$REMOTE_BIN'"
  fix_runtime_perms
  remote "sudo systemctl start htlb-api.service"
  health_check
  echo "rollback ok"
}

cmd="${1:-deploy}"
case "$cmd" in
  deploy) do_deploy ;;
  rollback) do_rollback "${2:-}" ;;
  health) health_check ;;
  -h|--help|help) usage ;;
  *)
    echo "unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac
