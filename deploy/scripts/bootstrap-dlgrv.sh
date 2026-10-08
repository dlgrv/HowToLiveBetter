#!/usr/bin/env bash
# One-time (idempotent) host prep for dlgrv. Run as root or via sudo.
set -euo pipefail

# Works whether invoked from a full clone (…/deploy/scripts/) or a copied tree (/tmp/…/scripts/).
DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

echo "==> system packages (nginx, certbot)"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx rsync curl
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y nginx certbot python3-certbot-nginx rsync curl
else
  echo "Install nginx, certbot, rsync, and curl manually, then re-run." >&2
  exit 1
fi

echo "==> user htlb"
if ! id htlb &>/dev/null; then
  useradd --system --home-dir /opt/htlb-api --shell /usr/sbin/nologin htlb
fi

echo "==> user deploy (rsync from CI)"
if ! id deploy &>/dev/null; then
  useradd --create-home --shell /bin/bash deploy
fi
# Restricted sudo for deploy path (binary restart + book docroot)
cat >/etc/sudoers.d/htlb-deploy <<'SUDO'
deploy ALL=(root) NOPASSWD: /bin/systemctl stop htlb-api.service, /bin/systemctl start htlb-api.service, /bin/systemctl restart htlb-api.service, /bin/systemctl status htlb-api.service, /bin/ln, /bin/chown, /bin/mkdir, /bin/tar, /bin/rm
SUDO
chmod 0440 /etc/sudoers.d/htlb-deploy

echo "==> directories"
install -d -o htlb -g htlb -m 0750 /opt/htlb-api
install -d -o htlb -g htlb -m 0750 /opt/htlb-api/pb_data
install -d -o htlb -g htlb -m 0750 /opt/htlb-api/releases
install -d -o htlb -g htlb -m 0750 /opt/htlb-api/backups
install -d -o deploy -g deploy -m 0755 /var/www/book.dlgrv.com
install -d -o deploy -g deploy -m 0755 /var/www/book.dlgrv.com/releases
install -d -o deploy -g deploy -m 0755 /var/www/book.dlgrv.com/current-placeholder
echo '<!doctype html><title>book</title><p>awaiting first deploy</p>' >/var/www/book.dlgrv.com/current-placeholder/index.html
ln -sfn /var/www/book.dlgrv.com/current-placeholder /var/www/book.dlgrv.com/current
# deploy needs write on /opt/htlb-api/releases for rsync
usermod -aG htlb deploy
chmod 0775 /opt/htlb-api/releases
install -d -m 0755 /var/www/certbot
echo "Install deploy SSH public key into ~deploy/.ssh/authorized_keys before CI deploy."

echo "==> env file template"
if [[ ! -f /etc/htlb-api.env ]]; then
  install -m 0600 -o root -g root "$DEPLOY_DIR/htlb-api.env.example" /etc/htlb-api.env
  echo "Edit /etc/htlb-api.env before starting htlb-api (secrets not in repo)."
fi

echo "==> systemd unit"
install -m 0644 -o root -g root "$DEPLOY_DIR/htlb-api.service" /etc/systemd/system/htlb-api.service
systemctl daemon-reload
systemctl enable htlb-api.service

echo "==> firewall (public HTTP/HTTPS; SSH already expected)"
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH >/dev/null 2>&1 || ufw allow 22/tcp >/dev/null 2>&1 || true
  ufw allow 80/tcp >/dev/null 2>&1 || true
  ufw allow 443/tcp >/dev/null 2>&1 || true
fi

echo "==> nginx vhosts"
# Configs listen on the public IP (178.104.217.93) so they do not clash with
# Tailscale Serve on the TS address :80.
install -m 0644 -o root -g root "$DEPLOY_DIR/nginx/book.dlgrv.com.conf" /etc/nginx/sites-available/book.dlgrv.com.conf
install -m 0644 -o root -g root "$DEPLOY_DIR/nginx/api.dlgrv.com.conf" /etc/nginx/sites-available/api.dlgrv.com.conf
ln -sf /etc/nginx/sites-available/book.dlgrv.com.conf /etc/nginx/sites-enabled/book.dlgrv.com.conf
ln -sf /etc/nginx/sites-available/api.dlgrv.com.conf /etc/nginx/sites-enabled/api.dlgrv.com.conf
if [[ -f /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
fi
nginx -t
systemctl enable nginx
systemctl reload nginx || systemctl start nginx

cat <<'EOF'

==> TLS (after DNS A records point here)

  ufw allow 80/tcp; ufw allow 443/tcp
  certbot certonly --webroot -w /var/www/certbot -d book.dlgrv.com -d api.dlgrv.com \
    --non-interactive --agree-tos --register-unsafely-without-email
  # Ensure /etc/letsencrypt/options-ssl-nginx.conf + ssl-dhparams.pem exist, then
  # install the HTTPS server blocks from deploy/nginx/*.conf and reload nginx.

==> next steps

  1. Edit /etc/htlb-api.env (HTLB_VOTE_SALT, OAuth client IDs)
  2. Place htlb-api binary: make api-build && deploy/scripts/deploy-api.sh
  3. Publish book: make pages-artifact && deploy/scripts/deploy-book.sh
  4. GitHub Environment production secrets: DEPLOY_SSH_KEY, DEPLOY_HOST=dlgrv (or IP), DEPLOY_USER=deploy

EOF
