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
