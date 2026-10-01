# Syncing Chinese content from upstream

> **Agents:** this file is mandatory for any upstream pull. Also mirrored in [AGENTS.md](../../AGENTS.md) and the fork banner in [CLAUDE.md](../../CLAUDE.md).

This fork (`dlgrv/HowToLiveBetter`) is an **English-primary translation overlay** on [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter). Chinese chapter files stay at `book/*.md` (same paths as upstream). Do **not** merge upstream wholesale.

## Reading GitHub “behind / ahead”

Compare **`eternity4719:main...dlgrv:main`** (upstream base → this fork):

| Field | Meaning |
|-------|---------|
| `behind_by` | Upstream commits not yet recorded as ancestors of fork `main` (lineage lag after the last `-s ours` anchor) |
| `ahead_by` | Commits unique to this fork |

Do **not** invert the compare and treat a large `behind_by` as “we are missing Chinese content.” Content lag is whatever `book/NN-*.md` / CN `docs/` differ from `upstream/main` after a path-filtered pull — not the raw counter alone.

Quick check:

```bash
gh api "repos/dlgrv/HowToLiveBetter/compare/eternity4719:main...main" \
  --jq '{ahead_by, behind_by, merge_base: .merge_base_commit.sha[0:7]}'
git merge-base HEAD upstream/main | cut -c1-7   # should match merge_base when synced
```

## One-time setup

```bash
git remote add upstream https://github.com/eternity4719/HowToLiveBetter.git
git fetch upstream
```

## Pull (path-filtered)

Prefer `make sync-upstream` (same steps). Manual form:

```bash
git fetch upstream

# Chinese chapters (root book/*.md only — not book/en|ru|es|pt)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main book | grep -E '^book/[0-9]{2}-.*\.md$')

# Chinese long reads at docs root + verification notes (exclude docs/en|ru|…)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main docs | grep -E '^docs/[^/]+\.md$' ; git ls-tree -r --name-only upstream/main docs/核实记录)

# Upstream AI skill (zh product content)
git checkout upstream/main -- skills/

# Optional
# git checkout upstream/main -- LICENSE

# Chinese README → README.zh.md ONLY (never root README.md)
git show upstream/main:README.md > README.zh.md
python3 forge/ops/strip_zh_readme_ads.py README.zh.md
# strip script also: docs/ → docs/research/, og.png → site/assets/og/zh.png,
# language table from README.md if [README.md](README.md) is missing

# Do NOT checkout ads/, site/, index.html, og.png, or translate/
```

Review `git status` / `git diff --stat` before committing CN. Then:

1. List touched chapters (Makefile prints them; or see [Inventory](#1-inventory-cn-changes)).
2. Fill `docs/.retranslate-pending` with drifted `<NN>` while locales catch up.
3. Run the [Translation catch-up](#translation-catch-up-after-cn-sync) checklist (`en` / `ru` / `es` / `pt`).
4. **After** catch-up (or with pending listed): `python3 forge/ops/check_content.py`.
5. If site template or counts changed: `python3 forge/site/build_pages.py`.

Do **not** expect `check_content.py` to pass immediately after the CN pull alone — mid-sync parity failures are normal until pending is filled or locales match.

Do **not** commit one-off catch-up helpers under `translate/`. Resume from units already on disk under `translate/runs/active/<lang>/<NN>/` if an agent dies.

## Translation catch-up (after CN sync)

Chinese files at `book/NN-*.md` are the source of truth. After every path-filtered pull, list what moved and re-run locales through the **locked pipeline order** in [translation-playbook.md §2](translation-playbook.md#2-пайплайн) (paths **A** / **B** in that section).

### 1. Inventory CN changes

Before committing the sync (or immediately after), list touched chapter files and root Chinese docs:

```bash
# Unstaged + staged CN chapters (adjust comparison if you already committed sync)
git diff --name-only HEAD -- 'book/[0-9][0-9]-*.md'
git diff --cached --name-only -- 'book/[0-9][0-9]-*.md'

# Long reads at docs root (not docs/en|ru|es|pt|…)
git diff --name-only HEAD -- docs/*.md
git diff --cached --name-only -- docs/*.md
```

Extract `<NN>` from each `book/NN-*.md` filename. If `README.zh.md` changed, queue README work for each non-`zh` locale (`README.md`, `README.ru.md`, `README.es.md`, `README.pt.md`, … — see [translate/langs.json](../../translate/langs.json)).

### 2. Queue locales

For each changed `<NN>`, catch up **every shipped translation locale** (today: `en`, `ru`, `es`, `pt`). Skip `zh` (live mirror at `book/*.md`). Match slugs under `book/<lang>/` to the Chinese chapter; conventions in [TRANSLATION.md](../../TRANSLATION.md).

### 3. Choose path A or B

| Situation | Path | Start at |
|-----------|------|----------|
| No `book/<lang>/` file yet, or CN added/removed/reordered items, or edits outside plain-terms (Benefit, Sources, tags, titles) | **A** — new / full chapter | `make_digest.py` → LLM unit translate → assemble |
| Chapter already passes `verify.py`; CN drift is **说人话 / plain-terms only** and structure/counts unchanged | **B** — simplify-only | Patch plain-terms in existing `book/<lang>/` file |

When in doubt, use **A** for the affected units (re-digest and re-translate only changed units if the chapter is large).

`make digest CH=08` (and `09`) is safe: Make pads with decimal arithmetic. Assemble rewrites CN-style `](../docs/…)` / `](../README…)` to fork paths under `book/<lang>/` (`../../docs/research/`, `../../README…`).

### 4. Locked step order (do not reorder)

**Required spine** (`make wave` = assemble + verify):

```text
digest → translate → assemble → verify ↔ repair → lt → style → human(+commit)
```

- Hard stop on first `verify.py` FAIL.
- `number_absent` → mechanical inject (`make repair` / `mechanical.py`), **not** LLM retry.
- Stale `translate/runs/active/<lang>/<NN>/` older than `book/<lang>/` is skipped by
  `wave_pipeline` unless `HTLB_FORCE_ASSEMBLE=1`.
- `make lt` requires LanguageTool `:8010` (exit 2 if down).
- Book-wide style: `make quality` → readability + `style_check --book --strict`.
- One chapter per commit when the user asks to commit (fork policy).

### 4b. Ship catch-up incrementally (agents)

Do **not** hold an entire post-sync locale catch-up in one mega-PR. As soon as a
chapter is green for the shipped locales (or a small coherent salvage set) on
`verify` (+ `lt` / `style`), open a branch, PR, and **squash-merge to `main`**.
Intermediate landings survive agent or llama crashes; `translate/runs/` stays
gitignored resume state only.

- Commit only `book/{en,ru,es,pt}/` (and locale READMEs if they changed).
- Never commit `translate/runs/`, `translate/.status/`, or one-off helpers under
  `translate/ops/`.
- One chapter × all locales in a single PR is fine; waiting for later chapters is not.

### 5. Docs and site

If root Chinese `docs/*.md` (or `docs/核实记录`) changed, catch up matching files under `docs/research/{en,ru,es,pt}/` using the same byte-verification rules as chapters. After all queued chapters verify, clear drifted lines from `.retranslate-pending`, then run `check_content.py` and `build_pages.py` if needed.

## Lineage anchor (`-s ours`)

After a content sync is on `main`, if `git merge-base HEAD upstream/main` is **behind** `upstream/main`, record lineage without changing the tree:

```bash
git fetch upstream
git merge -s ours upstream/main -m "chore: record upstream lineage through $(git rev-parse --short upstream/main)"
git push origin main   # real merge commit — never squash
```

- Current base is whatever `git merge-base HEAD upstream/main` prints (not a frozen SHA from an old note).
- This does **not** legalize wholesale merges. After the anchor, a bare `git merge upstream/main` would 3-way-merge into fork-owned paths — never do that. Path-filtered checkout + dry-run stay mandatory.
- Push to `main` without squash: squashing drops the upstream ancestor and `behind_by` lies again. Branch protection may report a bypass; that is the intended exception. Content PRs still use MR + squash.
- Upstream's `skills/` directory is Chinese product content: include it in the path-filtered checkout. `.claude/skills/` mirror is optional and not needed by the gates.

## Never auto-merge

These are fork-owned. A broad `git merge upstream/main` or `checkout upstream/main -- .` will damage the product:

- `README.md`, `README.ru.md`, `README.es.md`, `README.pt.md` (and any `README.<lang>.md` except the explicit `README.zh.md` ritual above)
- Entire `site/` (UI, assets, OG PNGs, robots, sitemap)
- `forge/v2.css`, `forge/og/`, `forge/site/build_pages.py`, `forge/site/pages_artifact.py`, `translate/langs.json`, `forge/ops/check_content.py`, `forge/ops/strip_zh_readme_ads.py`
- `.github/workflows/`
- `CLAUDE.md`, `TRANSLATION.md`, `AGENTS.md`
- `docs/research/en/`, `docs/research/ru/`, `docs/research/es/`, `docs/research/pt/`, `book/en/`, `book/ru/`, `book/es/`, `book/pt/`
- **Never** restore `ads/` (upstream author promo — this fork does not ship it)

## ZH policy

- `book/*.md` and root Chinese `docs/*.md` are a **live mirror** of upstream content (docs land under `docs/research/` on this fork after the strip overlay / layout).
- Chinese CN pages live at `/zh/` on this fork (same auto-detect as other locales).
- Product default language is **English** when the browser language is unknown (`/` → `/en/`).

## Dry-run check

Before committing a sync, confirm never-merge paths are absent from the staged set:

```bash
git diff --cached --name-only | grep -E '^(README\.md|README\.ru\.md|README\.es\.md|README\.pt\.md|site/|ads/|translate/(v2|og|build_pages|pages_artifact|langs|check_content|strip_zh)|CLAUDE\.md|TRANSLATION\.md|AGENTS\.md)' && echo 'FAIL: never-merge path staged' || echo 'ok'
```
