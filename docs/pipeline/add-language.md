# Add a language

English is the fork primary (`README.md`, `book/en/`, site default `/en/`). Chinese stays at upstream paths (`book/*.md`, `README.zh.md`). Every other locale follows this checklist.

Locale registry: [`translate/langs.json`](../../translate/langs.json). Upstream sync: [`docs/upstream-sync.md`](upstream-sync.md).

## Steps

1. **Registry** — append an object to `languages[]` in `translate/langs.json`:
   - `code` (URL segment, e.g. `es`)
   - `primary`: false
   - `contentRoot`: `book/<code>`
   - `readme`: `README.<code>.md`
   - `htmlLang`, `ogLocale`, `inLanguage`
   - `shortLabel` (nav chip), `menuLabel` (dropdown)
   - Order in the array = order in the language menu after the next build.

2. **UI strings** — add `I18N.<code>:{ … }` in [`site/index.html`](../../site/index.html) (copy from `en:` / `ru:` and translate). Build fails loudly if the block is missing.

3. **Content** — create `book/<code>/` chapters (status line + localized slugs per [`TRANSLATION.md`](../../TRANSLATION.md)) and `README.<code>.md`. Optionally `docs/research/<code>/` long reads.

4. **Build** — from repo root:
   ```bash
   python3 forge/site/build_pages.py
   # or: make web-build
   ```
   This patches the `/* HTLB_LANGS_BEGIN */` marker and lang menu in `site/index.html`, then writes `site/{code}/index.html`.

5. **README Languages lines** — add a native-CTA row on every existing README (EN / RU / ZH / …), same pattern as today.

6. **Optional** — OG banner: add `forge/og/<code>.html`, run `make og` → `site/assets/og/<code>.png`.

7. **Gates** — `python3 forge/ops/check_content.py`. Parity/verify helpers may still list only `en|ru` until extended; runtime/build must not need triple hardcoding.

## Do not

- Put translated chapters in root `book/` next to Chinese files.
- Overwrite root `README.md` with upstream Chinese (use `README.zh.md` only — see upstream-sync).
- Hand-edit `['ru','en','zh']` lists in JS; change `langs.json` and rebuild.
- Checkout or restore upstream `ads/`.
