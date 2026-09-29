# Add a chapter

When a new CN chapter appears (via upstream sync) or a chapter needs translation into a new language, follow this checklist.

## Prerequisites

- Upstream CN chapter exists at `book/NN-*.md`
- `translate/langs.json` has the target language registered
- `waves.json` includes this chapter in a wave

## Steps

### 1. Digest

Split the CN chapter into translatable units:

```bash
make digest CH=NN
```

This creates `translate/digest/NN/units/` with per-item `.md` files and a `blocks.json` with byte-faithful blocks (tags + sources).

### 2. Translate

Translate each unit in `translate/digest/NN/units/`:

```
translate/digest/NN/units/00.md  → head (chapter intro)
translate/digest/NN/units/01.md  → first item (replace §TAG§/§SRC§ placeholders)
translate/digest/NN/units/02.md  → second item
...
```

Translation conventions: [TRANSLATION.md](../../TRANSLATION.md). Per-language style rules: `translate/rules/{lang}.json`.

Store translated units under `translate/runs/active/{lang}/NN/units/`.

### 3. Assemble

Rebuild the translated chapter from units + byte-faithful blocks:

```bash
make assemble CH=NN LANG=ru
```

(`WORKDIR` defaults to `translate/runs/active/$(LANG)/$(CH)`; override for smoke/other runs.)

Output: `book/{lang}/NN-*.md` — the assembled chapter in target language format.

### 4. Verify

Run integrity checks against the CN original:

```bash
make verify CH=NN LANG=ru
```

Checks: heading count, tag count, source line byte-identity, CJK leakage, banned calques.

### 5. LanguageTool / style / polish

After green verify (LT Docker `:8010` and Laya `:8090` must be up):

```bash
make lt CH=NN LANG=ru
make style CH=NN LANG=ru   # or: make quality
make polish CH=NN LANG=ru
```

`make lt` / `make polish` exit **2** if LT / Laya is down.

### 6. Status

Update `translations.json` — mark the chapter as `done` for this language.

```bash
make status
```

### 7. Build pages

Regenerate per-language HTML:

```bash
make web-build
```

### 8. README and OG preview

Audit README chapter lists and OG preview images:

```bash
make update-readme
```

If README chapter counts are wrong, regenerate:

```bash
make update-readme ARGS=--fix
```

OG previews: regenerate `site/assets/og/{lang}.png` from `forge/og/{lang}.html` when chapter counts change:

```bash
make og
```

This uses headless Chrome for pixel-perfect 1200×630 screenshots.

### 9. Quality gates

```bash
make format      # Ruff + djlint autofix (optional before commit)
make lint        # Ruff / djlint / yamllint / shellcheck (also via pre-commit)
make ci          # tests + lint + links + content + pages + .publish artifact
make quality     # readability + style_check --book --strict (or LANG=ru)
```

### 9. Commit

```bash
git checkout -b translation/NN-{lang}
git add book/{lang}/ translations.json
git commit -m "translation({lang}): chapter NN — {title}"
```

## Do not

- Edit CN source files (`book/NN-*.md`) — they come from upstream
- Skip verify step — broken chapters block CI
- Forget to update `translations.json` — it's the single source of truth for pipeline status
- Overwrite root `README.md` with CN content — use `README.zh.md`