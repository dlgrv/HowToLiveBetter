# LanguageTool (self-hosted, $0)

Grammar and spelling hints for **plain-terms lines only** via `tools/lt_check.py`.
Runs in the translation pipeline **after factcheck** and **after** `style_check.py`.
Output is WARN-only; a down server never fails a chapter.

## Docker image (pinned tag)

```text
erikvl87/languagetool:latest
```

To pin by digest, replace `latest` with the digest from [Docker Hub](https://hub.docker.com/r/erikvl87/languagetool/tags) and update this file when you bump.

## Start

```bash
docker run --rm -d --name htlb-lt -p 8010:8010 erikvl87/languagetool:latest
```

API base URL: `http://127.0.0.1:8010` (endpoint `/v2/check`).

## Stop

```bash
docker stop htlb-lt
```

If the container was started without `--name htlb-lt`, use `docker ps` and `docker stop <container_id>`.

## Check a chapter

```bash
python3 tools/lt_check.py --file book/ru/01-Не-умирайте-рано.md --lang ru
python3 tools/lt_check.py --file book/en/01-Do-Not-Die-Early.md --lang en
python3 tools/lt_check.py --file book/es/01-No-Mueras-Temprano.md --lang es
```

JSON output:

```bash
python3 tools/lt_check.py --file book/ru/01-Не-умирайте-рано.md --lang ru --json
```

Language map: `ru` → `ru-RU`, `en` → `en-US`, `es` → `es`.

## Server down

If nothing listens on port 8010, `lt_check.py` prints one skip warning and exits **0**.
This is intentional — LT is advisory and not a CI hard gate.

## License / cost

Uses the community Docker image (LanguageTool is LGPL). No LanguageTool Premium subscription required.
