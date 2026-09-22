# Add a language

English is the fork primary (`README.md`, `book/en/`, site default `/en/`). Chinese stays at upstream paths (`book/*.md`, `README.zh.md`). Every other locale follows this checklist.

Locale registry: [`tools/langs.json`](../tools/langs.json). Upstream sync: [`docs/upstream-sync.md`](upstream-sync.md).

## Steps

1. **Registry** — append an object to `languages[]` in `tools/langs.json`:
   - `code` (URL segment, e.g. `es`)
   - `primary`: false
   - `contentRoot`: `book/<code>`
   - `readme`: `README.<code>.md`
   - `htmlLang`, `ogLocale`, `inLanguage`
   - `shortLabel` (nav chip), `menuLabel` (dropdown)
   - Order in the array = order in the language menu after the next build.

2. **UI strings** — add `I18N.<code>:{ … }` in root [`index.html`](../index.html) (copy from `en:` / `ru:` and translate). Build fails loudly if the block is missing.

3. **Content** — create `book/<code>/` chapters (status line + localized slugs per [`TRANSLATION.md`](../TRANSLATION.md)) and `README.<code>.md`. Optionally `docs/<code>/` long reads.

4. **Build** — from repo root:
   ```bash
   python3 tools/build_pages.py
   ```
   This patches the `/* HTLB_LANGS_BEGIN */` marker and lang menu in root `index.html`, then writes `/{code}/`, `v1/{code}/`, `v2/{code}/`.

5. **README Languages lines** — add a native-CTA row on every existing README (EN / RU / ZH / …), same pattern as today.

6. **Optional** — OG banner `og-<code>.png` + `tools/og-<code>.html` later; not required for the site to run.

7. **Gates** — `python3 tools/check_content.py`. Parity/verify helpers may still list only `en|ru` until extended; runtime/build must not need triple hardcoding.

## Do not

- Put translated chapters in root `book/` next to Chinese files.
- Overwrite root `README.md` with upstream Chinese (use `README.zh.md` only — see upstream-sync).
- Hand-edit `['ru','en','zh']` lists in JS; change `langs.json` and rebuild.
