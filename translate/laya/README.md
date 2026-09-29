# Laya System-1 (clarity + RU triage)

Self-hosted HTTP serve for [Laya](https://github.com/NandhaKishorM/laya) —
typed decisions for plain-terms clarity (`make clarity` / `make polish`) and
RU style triage (`make triage`). Required for polish when plain-terms exist.
Triage is not chained from `make style`.

## Ports (do not collide)

| Service | Port |
|---|---|
| Pages preview | `8000` |
| Hy-MT2 `llama-server` | `8080` |
| LanguageTool | `8010` |
| **Laya** | **`8090`** |

## Install (local only)

```bash
python3 -m pip install -r translate/laya/requirements-laya.txt
```

Not installed in CI. Extra is `laya[serve]` (FastAPI + uvicorn).

## Start

```bash
./translate/laya/start-laya-server.sh
# or: HTLB_LAYA_PORT=8090 HTLB_LAYA_DEVICE=mps ./translate/laya/start-laya-server.sh
```

Binds `127.0.0.1:8090`, preloads **multilingual only** (`LAYA_MODELS=multilingual`).
`HTLB_LAYA_MODEL` must stay `multilingual` — English checkpoint is rejected.

Fine to leave Hy-MT2 Q8 up on `:8080` while Laya runs on `:8090` (polish needs
both). Prefer LT **after** heavy Q8 waves if Activity Monitor shows swap.

## Probe

```bash
# health + one /v1/systemone call
PYTHONPATH=. python3 -m translate.laya.client
PYTHONPATH=. python3 -m translate.laya.client --fixture translate/laya/fixtures/ru-data-noun-01.json
```

## Clarity (plain-terms)

```bash
make clarity CH=10 LANG=ru|en|es
# or: PYTHONPATH=. python3 -m translate.laya.plain book/<lang>/… --lang …
make polish CH=10 LANG=ru   # after green verify: clarity → simplify → assemble → verify
```

| Exit (clarity / polish Laya phase) | Meaning |
|---|---|
| `0` | scored (понятно and/or непонятно); leftover непонятно is advisory |
| `2` | lines to score but server down / unreachable |

## Triage (manual)

```bash
make style CH=10 LANG=ru          # style_check only
make triage CH=10 LANG=ru         # triage alone when you want Laya on RU style hits
# or: PYTHONPATH=. python3 -m translate.laya.triage book/ru/10-….md --lang ru [--json]
```

Filters style hits to three RU labels (`этих-вместо-данных`, `согласно-творительный`,
`при-родительный-после-рамок`), asks Laya, prints cards `bug|ok|unclear`.

| Exit | Meaning |
|---|---|
| `0` | no triageable hits, or Laya answered |
| `2` | triageable hits exist but server down / unreachable |

`--apply` is reserved (default off; no autofix). Locked questions in `questions.py`.

Env (see `.env.example`):

| Var | Default |
|---|---|
| `HTLB_LAYA_BASE_URL` | `http://127.0.0.1:8090` |
| `HTLB_LAYA_PORT` | `8090` |
| `HTLB_LAYA_MODEL` | `multilingual` (required) |
| `HTLB_LAYA_DEVICE` | optional → `LAYA_DEVICE` (`cpu` / `mps` / `cuda`) |

Health uses current `GET /health`, with fallback to legacy `/healthz`.

## Fixtures

Hand-labeled snippets under `fixtures/` (данные/эти, согласно, при). Grow
toward ~30–50 locally; CI never hits a live server.
