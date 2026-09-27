# Add a chapter

When a new CN chapter appears (via upstream sync) or a chapter needs translation into a new language, follow this checklist.

## Prerequisites

- Upstream CN chapter exists at `book/NN-*.md`
- `tools/langs.json` has the target language registered
- `waves.json` includes this chapter in a wave

## Steps

### 1. Digest

Split the CN chapter into translatable units:

```bash
make digest CH=NN
```

This creates `tools/digest/NN/units/` with per-item `.md` files and a `blocks.json` with byte-faithful blocks (tags + sources).

### 2. Translate

Translate each unit in `tools/digest/NN/units/`:

```
tools/digest/NN/units/00.md  → head (chapter intro)
tools/digest/NN/units/01.md  → first item (replace §TAG§/§SRC§ placeholders)
tools/digest/NN/units/02.md  → second item
...
```

Translation conventions: [TRANSLATION.md](../../TRANSLATION.md). Per-language style rules: `tools/rules/{lang}.json`.

Store translated units under `tools/runs/active/{lang}/NN/units/`.

### 3. Assemble

Rebuild the translated chapter from units + byte-faithful blocks:

```bash
make assemble CH=NN LANG=ru
```

(`WORKDIR` defaults to `tools/runs/active/$(LANG)/$(CH)`; override for smoke/other runs.)

Output: `book/{lang}/NN-*.md` — the assembled chapter in target language format.

### 4. Verify

Run integrity checks against the CN original:

```bash
make verify CH=NN LANG=ru
```

Checks: heading count, tag count, source line byte-identity, CJK leakage, banned calques.

### 5. Status

Update `translations.json` — mark the chapter as `done` for this language.

```bash
make status
```

### 6. Build pages

Regenerate per-language HTML:

```bash
make web-build
```

### 7. README and OG preview

Audit README chapter lists and OG preview images:

```bash
make update-readme
```

If README chapter counts are wrong, regenerate:

```bash
make update-readme ARGS=--fix
```

OG previews: regenerate `site/assets/og/{lang}.png` from `tools/og/{lang}.html` when chapter counts change:

```bash
make og
```

This uses headless Chrome for pixel-perfect 1200×630 screenshots.

### 8. Quality gates

```bash
make format      # Ruff + djlint autofix (optional before commit)
make lint        # Ruff / djlint / yamllint / shellcheck (also via pre-commit)
make ci          # tests + lint + links + content + pages + .publish artifact
make quality     # readability + bureaucratese for ru/en/es (or LANG=ru)
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