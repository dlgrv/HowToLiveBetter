# htlb-api

Go backend for HowToLiveBetter interactive features (PocketBase as a library).

## Public API

Base: `https://api.dlgrv.com/api/htlb/v1`

| Method | Path | Auth |
|--------|------|------|
| GET | `/health` | none |
| POST | `/guest/session` | none |
| POST | `/guest/claim-code` | `X-HTLB-Sync` |
| POST | `/guest/claim` | body `{code}` |
| GET/POST | `/useful` | optional / required |
| GET/PUT/DELETE | `/bookmarks` | guest or user |
| GET/PUT | `/reading` | guest or user |
| POST | `/merge` | `Authorization` + `X-HTLB-Sync` |

Guest credential: header `X-HTLB-Sync` only. User JWT: `Authorization: Bearer …`.

OAuth: Google + GitHub only (password auth disabled). Configure via env:

- `HTLB_OAUTH_GOOGLE_CLIENT_ID` / `HTLB_OAUTH_GOOGLE_CLIENT_SECRET`
- `HTLB_OAUTH_GITHUB_CLIENT_ID` / `HTLB_OAUTH_GITHUB_CLIENT_SECRET`
- `HTLB_CORS_ORIGINS` (comma-separated)
- `HTLB_VOTE_SALT`
- `HTLB_DATA_DIR` (default `./pb_data`)

## Local

```bash
cd api
export HTLB_VOTE_SALT=dev
export HTLB_CORS_ORIGINS=http://127.0.0.1:8000
make -C .. api-dev
```

## Build

```bash
CGO_ENABLED=0 go build -o bin/htlb-api ./cmd/htlb-api
```

Attribution: PocketBase (MIT) — see `deploy/THIRD_PARTY.md`.
