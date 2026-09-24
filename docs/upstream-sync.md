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

# Upstream AI skill (zh product content; see "One-time history anchor" note)
git checkout upstream/main -- skills/

# Optional
# git checkout upstream/main -- LICENSE

# Chinese README → README.zh.md ONLY (never root README.md)
git show upstream/main:README.md > README.zh.md
```

Review `git status` / `git diff --stat` before committing. Then:

1. Run the [Translation catch-up](#translation-catch-up-after-cn-sync) checklist below (changed chapters → queue `en` / `ru` / `es`).
2. `python3 tools/check_content.py` (parity / stats).
3. If site template or counts changed: `python3 tools/build_pages.py`.

## Translation catch-up (after CN sync)

Chinese files at `book/NN-*.md` are the source of truth. After every path-filtered pull, list what moved and re-run locales through the **locked pipeline order** in [docs/translation-playbook.md §2](translation-playbook.md#2-пайплайн) (same as plan paths **A** / **B** in [plain-language pipeline plan](superpowers/plans/2026-09-23-plain-language-pipeline.md#correct-pipeline-order-commands)).

### 1. Inventory CN changes

Before committing the sync (or immediately after), list touched chapter files and root Chinese docs:

```bash
# Unstaged + staged CN chapters (adjust comparison if you already committed sync)
git diff --name-only HEAD -- 'book/[0-9][0-9]-*.md'
git diff --cached --name-only -- 'book/[0-9][0-9]-*.md'

# Long reads at docs root (not docs/en|ru|es|…)
git diff --name-only HEAD -- docs/*.md
git diff --cached --name-only -- docs/*.md
```

Extract `<NN>` from each `book/NN-*.md` filename. If `README.zh.md` changed, queue README work for each non-`zh` locale (`README.md`, `README.ru.md`, `README.es.md`, … — see [tools/langs.json](../tools/langs.json)).

### 2. Queue locales

For each changed `<NN>`, catch up **every shipped translation locale** (today: `en`, `ru`, `es`). Skip `zh` (live mirror at `book/*.md`). Match slugs under `book/<lang>/` to the Chinese chapter; conventions in [TRANSLATION.md](../TRANSLATION.md).

### 3. Choose path A or B

| Situation | Path | Start at |
|-----------|------|----------|
| No `book/<lang>/` file yet, or CN added/removed/reordered items, or edits outside plain-terms (Benefit, Sources, tags, titles) | **A** — new / full chapter | `make_digest.py` → LLM unit translate → assemble |
| Chapter already passes `verify.py`; CN drift is **说人话 / plain-terms only** and structure/counts unchanged | **B** — simplify-only | Patch plain-terms in existing `book/<lang>/` file |

When in doubt, use **A** for the affected units (re-digest and re-translate only changed units if the chapter is large).

### 4. Locked step order (do not reorder)

```text
digest → translate → assemble → verify → [simplify] → verify → factcheck → style_check → lt_check → plainness → human
```

- **Path A:** all steps from `python3 tools/make_digest.py <NN>` through human pass (see playbook §2 for exact commands: `assemble` / `assemble_en` / `assemble_es`, two `verify` runs if you simplify, then `factcheck`, `style_check`, `lt_check`, `plainness`).
- **Path B:** omit digest/translate/assemble; run: patch plain-terms → `verify` → `factcheck` → `style_check` → `lt_check` → `plainness` → human.

Hard stop on first `verify.py` FAIL. Do not run style / LanguageTool / plainness before the post-simplify `verify` and **factcheck** (see playbook §2).

Notes:

- `factcheck.py` today: `--lang ru|en` only (Spanish N/A until extended); use `--stdin-verdict` for smoke when live judge is unavailable.
- `plainness`: `ru|en` only today (no ES plain field yet).
- One chapter per commit when the user asks to commit (fork policy).

### 5. Docs and site

If root Chinese `docs/*.md` (or `docs/核实记录`) changed, catch up matching files under `docs/en/`, `docs/ru/`, `docs/es/` using the same byte-verification rules as chapters. After all queued chapters verify, re-run step 2–3 in [Pull](#pull-path-filtered) (`check_content.py`, `build_pages.py` if needed).

## One-time history anchor (2026-09-23)

A single exception was made: `git merge -s ours upstream/main --allow-unrelated-histories` recorded
the upstream lineage through `dfebc18` as an ancestor of fork `main` **without changing any file**
(tree of a `-s ours` merge equals HEAD). This zeroes the GitHub "behind" counter so it becomes a
meaningful "new upstream commits since last sync" indicator.

- This does **not** legalize wholesale merges. On the contrary: after the anchor the merge base is
  `dfebc18`, so a bare `git merge upstream/main` no longer fails loudly on unrelated histories —
  it would silently 3-way-merge upstream changes into fork-owned files. The Never auto-merge rule
  below is now enforced by discipline + the dry-run check, not by git.
- The anchor is tied to the upstream lineage (`dfebc18`). If upstream ever rewrites history, the
  anchor drifts and "behind" reappears — repeat the anchor merge then. The sync ritual itself stays
  **content-based** (diff `book/*.md` between snapshots, never SHA comparison).
- Sync/anchor commits are pushed directly to `main` (no MR/squash): squashing the anchor would
  destroy the recorded lineage and the counter reset. The MR+squash rule applies to content PRs.
- Upstream's `skills/` directory is Chinese product content (AI skill for the book): include it in
  the path-filtered checkout. `.claude/skills/` mirror is optional and not needed by the gates.

## Never auto-merge

These are fork-owned. A broad `git merge upstream/main` or `checkout upstream/main -- .` will damage the product (and after the 2026-09-23 history anchor it would no longer fail loudly — see above):

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
