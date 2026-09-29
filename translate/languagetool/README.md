# LanguageTool (required after verify)

Self-hosted [LanguageTool](https://github.com/languagetool-org/languagetool)
on loopback `:8010`. Grammar/spelling on **plain-terms** lines only.

**Order:** after green `verify`, before `make polish`.  
`make lt CH=NN LANG=ru|en|es` — if the server is down and there are plain-terms
to check → **exit 2**.

## Start

```bash
docker run -d --name htlb-lt -p 8010:8010 erikvl87/languagetool
# or see upstream image docs for LanguageTool HTTP API
```

Env: `HTLB_LT_BASE_URL` (default `http://127.0.0.1:8010`).

## Run

```bash
make lt CH=01 LANG=ru
# or: PYTHONPATH=. python3 translate/shelf/lt_check.py --file book/ru/01-….md --lang ru
```

| Exit | Meaning |
|---|---|
| `0` | LT answered (grammar hits may print as WARN) |
| `2` | unreachable / mid-run fail while plain-terms exist |

Prefer LT after Q8 translate waves if the machine is under memory pressure.
