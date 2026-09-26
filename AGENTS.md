# Agent notes (dlgrv/HowToLiveBetter)

English-primary fork of [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter).

## Sync Chinese content from upstream

**Source of truth for the ritual:** [docs/upstream-sync.md](docs/upstream-sync.md). Read it before any upstream pull. Do **not** `git merge upstream/main`.

```bash
git fetch upstream

# Chinese chapters only (root book/NN-*.md)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main book | grep -E '^book/[0-9]{2}-.*\.md$')

# Chinese docs root + 核实记录 (not docs/en|ru|…)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main docs | grep -E '^docs/[^/]+\.md$' ; git ls-tree -r --name-only upstream/main docs/核实记录)

# Chinese README → README.zh.md ONLY (never root README.md)
git show upstream/main:README.md > README.zh.md

python3 tools/check_content.py
# if template/counts changed: python3 tools/build_pages.py
```

After sync: diff new/changed `book/NN-*.md` and catch up each `book/<lang>/`.

## Locales

- Registry: [tools/langs.json](tools/langs.json)
- Add a language: [docs/add-language.md](docs/add-language.md)
- Conventions: [TRANSLATION.md](TRANSLATION.md)

## Never overwrite (fork-owned)

`README.md`, `README.ru.md`, `index.html`, `og*`, `tools/v2*`, `tools/build_pages.py`, `tools/langs.json`, generated `en|ru|zh|v1|v2/`, `.github/workflows/`, `CLAUDE.md`, `TRANSLATION.md`, `sitemap.xml`, `book/en|ru/`, `docs/en|ru/`.

## Pipeline (for AI agents)

Entry point: `make help` lists all commands. Topology: `pipeline.yaml`.

### Conventions

- **CN source is read-only.** Only `sync-upstream` touches `book/NN-*.md`.
- **Translations live in `book/{ru,en,es}/`** — one chapter = one file.
- **Status is in `translations.json`** — single source of truth for what's done.
- **Waves are in `waves.json`** — 1-3 chapters each.
- **Run state is gitignored** — `run/`, `tools/digest/`, `tools/.status/`, `tools/runs/`.
- **Tool output contracts:** `--json` → structured stdout. Exit codes: 0=pass, 1=FAIL, 2=WARN.
- **Commit policy:** publication only through MR + squash-merge to `main`. No direct pushes.

### Typical agent session

```bash
# 1. Orient
make help
cat translations.json    # what's done?
cat pipeline.yaml        # what tools exist?

# 2. Sync upstream (if needed)
make sync-upstream       # pulls CN changes
git diff -- book/        # what changed?

# 3. Translate a wave
make digest CH=02        # split CN chapter into units
# ... translate units manually or via delegation ...
make assemble CH=02 LANG=ru WORKDIR=run/ru/02
make verify CH=02 LANG=ru

# 4. Full wave
make wave WAVE=1
make status
```

### Committing

```bash
# After translation work — always ask user before committing.
# Merge strategy: branch → MR → squash to main.
git checkout -b translation/ru-ch02
git add book/ru/ translations.json
git commit -m "translation(ru): chapter 02 — $(grep '^# ' book/ru/02-*.md | head -1 | cut -d' ' -f2-)"
```
