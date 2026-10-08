# Deploy (book + API)

Ops artifacts for **dlgrv** (`book.dlgrv.com`, `api.dlgrv.com`).

Full checklist, secrets, OAuth, and rollback policy: [docs/pipeline/deploy-book-api.md](../docs/pipeline/deploy-book-api.md).

| Path | Purpose |
|------|---------|
| `nginx/` | Site vhosts (TLS via certbot) |
| `htlb-api.service` | systemd unit for `htlb-api` |
| `htlb-api.env.example` | Production env template → `/etc/htlb-api.env` |
| `scripts/bootstrap-dlgrv.sh` | One-time host prep (user, dirs, nginx, unit) |
| `scripts/deploy-book.sh` | Rsync `.publish/` to the book docroot |
| `scripts/deploy-api.sh` | Binary release, backup, health, rollback |
| `THIRD_PARTY.md` | PocketBase MIT attribution |

**Order:** bootstrap once → copy and edit `/etc/htlb-api.env` (never commit) → certbot → `deploy-api.sh` → `deploy-book.sh`.
