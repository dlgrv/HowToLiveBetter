# Syncing Chinese content from upstream

> **Agents:** this file is mandatory for any upstream pull. Also mirrored in [AGENTS.md](../AGENTS.md) and the fork banner in [CLAUDE.md](../CLAUDE.md).

This fork (`dlgrv/HowToLiveBetter`) is an **English-primary translation overlay** on [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter). Chinese chapter files stay at `book/*.md` (same paths as upstream). Do **not** merge upstream wholesale.

## One-time setup

```bash
git remote add upstream https://github.com/eternity4719/HowToLiveBetter.git
git fetch upstream
```

## Pull (path-filtered)

```bash
git fetch upstream

# Chinese chapters (root book/*.md only — not book/en|ru|…)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main book | grep -E '^book/[0-9]{2}-.*\.md$')

# Chinese long reads at docs root + verification notes (exclude docs/en|ru|…)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main docs | grep -E '^docs/[^/]+\.md$' ; git ls-tree -r --name-only upstream/main docs/核实记录)

# Optional
# git checkout upstream/main -- LICENSE

# Chinese README → README.zh.md ONLY (never root README.md)
git show upstream/main:README.md > README.zh.md
```

Review `git status` / `git diff --stat` before committing. Then:

1. Diff new/changed `book/NN-*.md` → catch up each `book/<lang>/` (and docs translations if needed).
2. `python3 tools/check_content.py` (parity / stats).
3. If site template or counts changed: `python3 tools/build_pages.py`.

## Never auto-merge

These are fork-owned. A broad `git merge upstream/main` or `checkout upstream/main -- .` will damage the product:

- `README.md`, `README.ru.md` (and any `README.<lang>.md` except the explicit `README.zh.md` ritual above)
- `index.html`
- `og.png`, `og-en.png`, `og-ru.png`
- `tools/v2.css`, `tools/build_pages.py`, `tools/langs.json`, `tools/check_content.py`
- Generated pages: `en/`, `ru/`, `zh/`, `v1/`, `v2/`
- `.github/workflows/`
- `CLAUDE.md`, `TRANSLATION.md`, `sitemap.xml`
- `docs/en/`, `docs/ru/`, `book/en/`, `book/ru/` (and future `book/<lang>/`)

## ZH policy

- `book/*.md` and root Chinese `docs/*.md` are a **live mirror** of upstream content.
- Site may still soft-redirect bare zh browsers to the original Pages host (see root `index.html`).
- Product default language is **English** (`/` → `/en/`).

## Dry-run check

Before committing a sync, confirm never-merge paths are absent from the staged set:

```bash
git diff --cached --name-only | grep -E '^(README\.md|README\.ru\.md|index\.html|og|tools/(v2|build_pages|langs|check_content)|CLAUDE\.md|TRANSLATION\.md|sitemap\.xml|(en|ru|zh|v1|v2)/)' && echo 'FAIL: never-merge path staged' || echo 'ok'
```
