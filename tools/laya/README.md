# Laya System-1 (optional WARN triage)

Self-hosted HTTP serve for [Laya](https://github.com/NandhaKishorM/laya) —
typed `choice` / `noul` decisions over Russian style hits. **Not** on the
publish spine (`make wave` / verify). Spike client only; triage lands later.

## Ports (do not collide)

| Service | Port |
|---|---|
| Pages preview | `8000` |
| Hy-MT2 `llama-server` | `8080` |
| LanguageTool | `8010` |
| **Laya** | **`8090`** |

## Install (local only)

```bash
python3 -m pip install -r tools/laya/requirements-laya.txt
```

Not installed in CI. Extra is `laya[serve]` (FastAPI + uvicorn).

## Start

```bash
./tools/laya/start-laya-server.sh
# or: HTLB_LAYA_PORT=8090 HTLB_LAYA_DEVICE=mps ./tools/laya/start-laya-server.sh
```

Binds `127.0.0.1:8090`, preloads **multilingual only** (`LAYA_MODELS=multilingual`).
`HTLB_LAYA_MODEL` must stay `multilingual` — English checkpoint is rejected.

**RAM:** do not co-load Laya with Hy-MT2 Q8 on a 48 GB Mac (same class of note as LanguageTool after a translate wave).

## Probe

```bash
# health + one /v1/systemone call; exit 0 if server down
PYTHONPATH=. python3 -m tools.laya.client
PYTHONPATH=. python3 -m tools.laya.client --fixture tools/laya/fixtures/ru-data-noun-01.json
```

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
