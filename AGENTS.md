# Agent notes (dlgrv/HowToLiveBetter)

English-primary fork of [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter).

## Sync Chinese content from upstream

**Source of truth for the ritual:** [docs/pipeline/upstream-sync.md](docs/pipeline/upstream-sync.md). Read it before any upstream pull. Do **not** `git merge upstream/main`.

```bash
git fetch upstream

# Chinese chapters only (root book/NN-*.md)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main book | grep -E '^book/[0-9]{2}-.*\.md$')

# Chinese docs root + 核实记录 (not docs/en|ru|…)
git checkout upstream/main -- $(git ls-tree -r --name-only upstream/main docs | grep -E '^docs/[^/]+\.md$' ; git ls-tree -r --name-only upstream/main docs/核实记录)

# Chinese README → README.zh.md ONLY (never root README.md)
git show upstream/main:README.md > README.zh.md
python3 tools/strip_zh_readme_ads.py README.zh.md

python3 tools/check_content.py
# if template/counts changed: python3 tools/build_pages.py
```

After sync: diff new/changed `book/NN-*.md` and catch up each `book/<lang>/`.

**Never** checkout from upstream: `ads/`, `site/`, `index.html`, `og.png`, `tools/`.

## Layout

| Path | Role |
|---|---|
| `book/NN-*.md` | CN source (upstream paths — frozen) |
| `book/{en,ru,es}/` | translations |
| `site/` | authored Pages UI (`index.html`, `{lang}/`, `assets/`) |
| `.publish/` | Pages deploy artifact (`make serve` / `pages_artifact.py`) |
| `tools/` | pipeline + `tools/og/*.html` screenshot sources |
| `tools/llm/` | machine translate / repair (LLM CLIs) |
| `tools/validate/` | research / golden / judge — **not** required to publish |
| `README*.md` | stay at repo root (GitHub UI + Pages artifact) |

**Publish path:** digest → `tools/runs/active/<lang>/<NN>/` → assemble → verify → `book/<lang>/`.

Local preview: `make serve` → http://127.0.0.1:8000/en/. Deploy: GitHub Actions Pages job after workflow `test` succeeds on `main`.
## Locales

- Registry: [tools/langs.json](tools/langs.json)
- Add a language: [docs/pipeline/add-language.md](docs/pipeline/add-language.md)
- Conventions: [TRANSLATION.md](TRANSLATION.md)

## Never overwrite (fork-owned)

`README.md`, `README.ru.md`, `README.es.md`, entire `site/`, `tools/v2.css`, `tools/og/`, `tools/build_pages.py`, `tools/langs.json`, `tools/pages_artifact.py`, `.github/workflows/`, `CLAUDE.md`, `TRANSLATION.md`, `book/en|ru|es/`, `docs/research/en|ru|es/`. Never restore `ads/`.

## Pipeline (for AI agents)

Entry point: `make help` lists all commands. Raw `python3 tools/…` from the repo root needs `PYTHONPATH=.` (Make exports it).

### Adding a chapter

Full checklist: [docs/pipeline/add-chapter.md](docs/pipeline/add-chapter.md). Summary: digest → translate → assemble → verify → status → build → commit.

### Conventions

- **CN source is read-only.** Only `sync-upstream` touches `book/NN-*.md`.
- **Translations live in `book/{ru,en,es}/`** — one chapter = one file.
- **Status is in `translations.json`** — single source of truth for what's done.
- **Waves are in `waves.json`** — 1-3 chapters each.
- **Run state is gitignored** — `tools/runs/` (canonical wave workdirs under `tools/runs/active/<lang>/<NN>/`), `tools/digest/`, `tools/.status/`; legacy `run/` also ignored if present.
- **Tool output contracts:** `--json` → structured stdout. Exit codes: 0=pass, 1=FAIL, 2=WARN.
- **Commit policy:** publication only through MR + squash-merge to `main`. No direct pushes.
- **Commit messages:** English Conventional Commits only — enforced by `.githooks/commit-msg` and CI on PRs. Run `make hooks` once after clone.
- **Code quality stack** (config in `pyproject.toml` / `.yamllint.yaml`): **Ruff** (Python lint+format), **djlint** (`tools/og/*.html`, lint `site/index.html`), **yamllint**, **shellcheck** (`tools/llm/*.sh`). Commands: `make format`, `make lint`. Requires Python **≥3.11** venv and `shellcheck` on PATH. `.githooks/pre-commit` runs `make lint` + `make check-content`; `.githooks/pre-push` runs `make test` + `make check-content`. Full GitHub replica: `make ci` before push if hooks are not installed.
- **Repair issue locator:** `tools/llm/verify_issues.py` maps verify HARD fails to unit IDs (used by `repair_wave --dry-locate`); not the chapter verify gate (`tools/verify.py`).
### Commit messages

Format: `type(optional-scope): description`

| Rule | Detail |
|---|---|
| Language | **English only** (no Cyrillic / CJK in subject or body) |
| Types | `feat` `fix` `docs` `chore` `ci` `test` `refactor` `sync` `translation` `quality` |
| Scope | optional, lowercase: `ru` `en` `es` `pipeline` `og` `ch02` `skills` … |
| Description | imperative, starts with lowercase letter/digit, no trailing period, subject ≤72 chars |
| Body | optional; blank line after subject |
| Forbidden | Cursor/AI attribution trailers (`Co-authored-by: Cursor`, `Made with Cursor`, …) |
| Allowed exceptions | `Merge pull request/branch …`, `Revert "…"` |

Examples:

```
translation(ru): chapter 02
sync: pull upstream chapters 03, 08, 10
fix(og): restore V2 editorial templates
feat(pipeline): add make og target for locale previews
quality(ru): strip bureaucratese markers
chore: ignore pipeline run state and untrack judge verdicts
ci: enforce English conventional commit messages
```

Local check: `make check-commit-msg MSG='fix: restore templates'` or `make hooks` then normal `git commit`.

### Typical agent session

```bash
# 1. Orient
make help
cat translations.json    # what's done?

# 2. Sync upstream (if needed)
make sync-upstream       # pulls CN changes
git diff -- book/        # what changed?

# 3. Translate a wave
make digest CH=02        # split CN chapter into units
# ... translate units manually or via delegation ...
# Canonical workdir: tools/runs/active/<lang>/<NN>/ (parent of units/)
make assemble CH=02 LANG=ru
make verify CH=02 LANG=ru

# 4. Full wave
make wave WAVE=1
make status
```

### Committing

```bash
# After translation work — always ask user before committing.
# Merge strategy: branch → MR → squash to main.
# Subject must stay English (do not paste RU/CN chapter titles into the message).
git checkout -b translation/ru-ch02
git add book/ru/ translations.json
git commit -m "translation(ru): chapter 02"
```
