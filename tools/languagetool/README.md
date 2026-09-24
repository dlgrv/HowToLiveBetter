# LanguageTool (self-hosted, $0)

Grammar/spelling hints for **plain-terms lines only** via `tools/lt_check.py`.
Pipeline order: **after factcheck** and **after** `style_check.py`.
WARN-only: a down server never fails a chapter (exit 0) — read the skip line.

## Docker image

```text
erikvl87/languagetool:latest
```

Pin by digest from [Docker Hub](https://hub.docker.com/r/erikvl87/languagetool/tags) when you need reproducibility.

## Start

```bash
docker run --rm -d --name htlb-lt -p 8010:8010 erikvl87/languagetool:latest
```

API: `http://127.0.0.1:8010` (`/v2/check`). Override with `HTLB_LT_BASE_URL` or `--base-url`.

## Language packs (HTLB → LanguageTool)

| `--lang` | LT code |
|---|---|
| `ru` | `ru-RU` |
| `en` | `en-US` |
| `es` | `es` |

## Healthcheck

```bash
curl -sf -X POST "http://127.0.0.1:8010/v2/check" \
  -d "language=en-US&text=Hello" | head -c 200
```

Empty / connection refused → start container (or expect `lt_check` skip / exit 0).

## RAM note (Mac + local Hy-MT2 Q8)

`htlb-lt` plus Q8 (~32 GB weights) on 48 GB unified memory is tight. Prefer LT checks **after** translate waves, or stop the container while loading/serving Q8 if swap spikes.

## Stop

```bash
docker stop htlb-lt
```

## Check a chapter

```bash
python3 tools/lt_check.py --file book/ru/01-Не-умирайте-рано.md --lang ru
python3 tools/lt_check.py --file book/en/01-Do-Not-Die-Early.md --lang en
python3 tools/lt_check.py --file book/es/01-No-Mueras-Temprano.md --lang es
```

JSON:

```bash
python3 tools/lt_check.py --file book/ru/01-Не-умирайте-рано.md --lang ru --json
```

If nothing listens on 8010, `lt_check.py` prints skip (`server_down` or mid-run `skip_partial`) and exits **0**. Do not treat exit 0 as “LT ran clean” without reading stdout.

Uses the community Docker image (LanguageTool LGPL). No Premium.
