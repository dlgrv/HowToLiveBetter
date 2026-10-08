# Deploy: book.dlgrv.com + api.dlgrv.com

Ops checklist for the interactive book stack (fork dlgrv). Product decisions live in [interactive-site-ideas.md](interactive-site-ideas.md).

## Hosts

| Host | Role |
|------|------|
| `https://book.dlgrv.com` | Static book (nginx → `/var/www/book.dlgrv.com`) |
| `https://book.dlgrv.com/login/` | Sign-in page (Google/GitHub); `?next=` returns to the book URL after OAuth |
| `https://api.dlgrv.com` | `htlb-api` (Go + PocketBase) behind nginx → `127.0.0.1:8090` |
| `https://dlgrv.github.io/HowToLiveBetter/` | Static mirror (no auth UI; interactive sync only on `book.dlgrv.com`) |

DNS (Cloudflare, grey cloud / DNS only): `book` and `api` A → dlgrv `178.104.217.93`.

SSH host alias: `dlgrv` (see `~/.ssh/config`). Nginx binds the **public** IP only so it does not fight Tailscale Serve on `:80`.

## Repo layout

- [`api/`](../../api/) — Go module (`htlb-api`), custom routes `/api/htlb/v1`
- [`deploy/`](../../deploy/) — nginx, systemd, THIRD_PARTY
- Workflows: `deploy-book.yml`, `deploy-api.yml`; CI job `api` in `ci.yml`

## Local API

```bash
make api-dev          # go run … serve --http=127.0.0.1:8090 --dir=api/.local/pb_data
make api-test
make api-lint
```

Env (see `deploy/htlb-api.env.example`):

- `HTLB_CORS_ORIGINS` — comma list, e.g. `https://book.dlgrv.com,http://127.0.0.1:8000`
- `HTLB_GUEST_TTL_HOURS` — default `2160` (90d)
- `HTLB_VOTE_SALT` — server secret for useful fingerprints
- PocketBase encryption: `--encryptionEnv=HTLB_PB_ENCRYPTION` (32-char key in that env)

## Guest sync contract

- Long-lived token in `localStorage` key `htlb_sync_token`
- Header: `X-HTLB-Sync: <token>` (never `Authorization`)
- Cross-device sync is via OAuth account only (Google/GitHub); guest token stays on the browser until merge
- OAuth user uses `Authorization: Bearer <pb jwt>`; on login call `POST /api/htlb/v1/merge` with guest token in `X-HTLB-Sync`

## OAuth (manual, once)

1. GitHub OAuth App + Google Cloud OAuth client  
2. Redirect URI: `https://api.dlgrv.com/api/oauth2-redirect`  
3. Enable only Google + GitHub in PocketBase admin (`/_/`); disable password auth  
4. Keep `/_/` publicly reachable in nginx — OAuth completion loads `/_/#/auth/oauth2-*` in the popup (admin actions still need a superuser)

## Secrets (GitHub Environment `production`)

- `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`
- Never commit OAuth client secrets or encryption keys

## Deploy order (API)

1. `go test` / lint green  
2. `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build`  
3. Backup `pb_data` on server  
4. Rsync binary → `/opt/htlb-api/htlb-api`  
5. `systemctl restart htlb-api`  
6. Smoke: `GET /api/htlb/v1/health`, guest session, 401 on bookmarks without token  
7. On failure: restore previous binary + restart  

## Rollback (book)

Release dirs + symlink (or keep previous `.publish` tarball). Atomic swap preferred over live `rsync --delete` into docroot.

## Backup

Nightly: `htlb-api` `CreateBackup` or copy `pb_data` (include WAL); encrypt (`age`); off-host copy; restore drill quarterly.

## Cutover checklist (2026-10)

Live:

- `https://book.dlgrv.com/en/` — static book
- `https://api.dlgrv.com/api/htlb/v1/health` — API
- Guest: `POST /guest/session`, `X-HTLB-Sync` on `/bookmarks`
- GitHub Pages workflow publishes the static book (auth disabled on that host)

Still manual:

- GitHub Environment `production` secrets: `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER=deploy`
- OAuth Google + GitHub client IDs/secrets in `/etc/htlb-api.env`, then `systemctl restart htlb-api`
- PocketBase first superuser: `ssh dlgrv` → `/opt/htlb-api/htlb-api superuser upsert EMAIL PASS` (admin UI `/_/` — public shell, auth-gated)
- Confirm github.io serves the static book (no redirect) after next Pages deploy on `main`
