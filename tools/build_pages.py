#!/usr/bin/env python3
"""Generate language pages under site/ from site/index.html + tools/langs.json.

Layout (git):
  site/index.html              language router / template
  site/{lang}/index.html       generated locale pages
  site/assets/v2.css           copy of tools/v2.css (synced each run)
  site/assets/og/{lang}.png    OG images (make og)

Published Pages artifact flattens site/ to the host root and adds book/ + README*
beside it (see tools/pages_artifact.py). Locale pages use __HTLB_BASE__='../'
so fetch paths resolve to that flat root.

I18N prose lives in site/index.html; every langs.json code needs I18N.{code}:{…}.

Run from repo root:  python3 tools/build_pages.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys

from tools.pipeline.config import default_root
from tools.pipeline.config import load_langs as load_langs_registry

ROOT = default_root()
SITE = os.path.join(ROOT, "site")
INDEX_PATH = os.path.join(SITE, "index.html")
V2_CSS_SRC = os.path.join(ROOT, "tools", "v2.css")
V2_CSS_DST = os.path.join(SITE, "assets", "v2.css")

HOST = "https://dlgrv.github.io/HowToLiveBetter"
ORIGIN_PAGES = "https://eternity4719.github.io/HowToLiveBetter/"
ORIGIN_REPO = "https://github.com/eternity4719/HowToLiveBetter"


def og_image_url(lang: str) -> str:
    return f"{HOST}/assets/og/{lang}.png"


CANON_RE = re.compile(r'<link rel="canonical" href="[^"]*">')
OGURL_RE = re.compile(r'<meta property="og:url" content="[^"]*">')
OGIMG_RE = re.compile(r'<meta property="og:image" content="[^"]*">')
TWIMG_RE = re.compile(r'<meta name="twitter:image" content="[^"]*">')
HTML_LANG_RE = re.compile(r'(<html\s[^>]*lang=")[^"]*(")')
TITLE_RE = re.compile(r"<title>[^<]*</title>")
STYLESHEET_V2_RE = re.compile(
    r'<link\s+rel="stylesheet"\s+href="(?:\.\./)?assets/v2\.css"\s*>\s*',
    re.IGNORECASE,
)
META_NAME_RE = {
    "description": re.compile(r'<meta name="description" content="[^"]*">'),
    "keywords": re.compile(r'<meta name="keywords" content="[^"]*">'),
    "author": re.compile(r'<meta name="author" content="[^"]*">'),
}
OG_PROP_RE = {
    "og:site_name": re.compile(r'<meta property="og:site_name" content="[^"]*">'),
    "og:locale": re.compile(r'<meta property="og:locale" content="[^"]*">'),
    "og:title": re.compile(r'<meta property="og:title" content="[^"]*">'),
    "og:description": re.compile(r'<meta property="og:description" content="[^"]*">'),
}
TW_RE = {
    "twitter:title": re.compile(r'<meta name="twitter:title" content="[^"]*">'),
    "twitter:description": re.compile(r'<meta name="twitter:description" content="[^"]*">'),
}
LD_RE = re.compile(r'<script type="application/ld\+json">\s*.*?\s*</script>', re.DOTALL)
STYLE_RE = re.compile(r"<style>.*?</style>", re.DOTALL)
LANGS_BLOCK_RE = re.compile(
    r"<script>\s*/\* HTLB_LANGS_BEGIN \*/.*?/\* HTLB_LANGS_END \*/\s*</script>",
    re.DOTALL,
)
BOOTSTRAP_RE = re.compile(r"<script>/\* per-language override.*?</script>", re.DOTALL)


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("built", os.path.relpath(path, ROOT))


def esc_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def sync_v2_css() -> str:
    """Copy tools/v2.css → site/assets/v2.css; return CSS text for locale inlining."""
    if not os.path.isfile(V2_CSS_SRC):
        sys.exit(f"missing {V2_CSS_SRC}")
    os.makedirs(os.path.dirname(V2_CSS_DST), exist_ok=True)
    shutil.copy2(V2_CSS_SRC, V2_CSS_DST)
    print("synced", os.path.relpath(V2_CSS_DST, ROOT))
    with open(V2_CSS_SRC, encoding="utf-8") as f:
        return f.read()


def load_langs():
    langs = load_langs_registry(ROOT)
    if not isinstance(langs, list) or not langs:
        sys.exit("tools/langs.json: languages[] required")
    primary = None
    for lang_entry in langs:
        for key in (
            "code",
            "contentRoot",
            "readme",
            "htmlLang",
            "ogLocale",
            "inLanguage",
            "shortLabel",
            "menuLabel",
        ):
            if key not in lang_entry or not lang_entry[key]:
                sys.exit(f"tools/langs.json: language missing {key!r}")
        if lang_entry.get("primary"):
            if primary:
                sys.exit("tools/langs.json: only one primary language allowed")
            primary = lang_entry["code"]
    if not primary:
        sys.exit("tools/langs.json: set primary:true on exactly one language")
    return langs, primary


def langs_payload(langs, primary):
    return {
        "codes": [entry["code"] for entry in langs],
        "primary": primary,
        "shortLabels": {entry["code"]: entry["shortLabel"] for entry in langs},
        "menuLabels": {entry["code"]: entry["menuLabel"] for entry in langs},
        "readmes": {entry["code"]: entry["readme"] for entry in langs},
        "ogLocales": {entry["code"]: entry["ogLocale"] for entry in langs},
        "inLanguages": {entry["code"]: entry["inLanguage"] for entry in langs},
    }


def langs_script(payload) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        "<script>\n"
        "/* HTLB_LANGS_BEGIN */\n"
        f"window.__HTLB_LANGS__={body};\n"
        "/* HTLB_LANGS_END */\n"
        "</script>"
    )


def menu_html(langs) -> str:
    buttons = "\n".join(
        '          <button type="button" role="menuitem" data-lang="{}">{}</button>'.format(
            entry["code"], esc_attr(entry["menuLabel"])
        )
        for entry in langs
    )
    return f'        <div class="lang-menu" role="menu">\n{buttons}\n        </div>'


def i18n_block(src_html: str, lang: str) -> str:
    """Slice the I18N.{lang}:{ ... } object body from index.html (brace-aware)."""
    start = re.search(rf"\n {lang}:\{{", src_html)
    if not start:
        sys.exit(f"I18N block not found for lang={lang} (add I18N.{lang}:{{…}} in site/index.html)")
    i = start.end()
    depth = 1
    while i < len(src_html) and depth:
        c = src_html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "'":
            i += 1
            while i < len(src_html):
                if src_html[i] == "\\":
                    i += 2
                    continue
                if src_html[i] == "'":
                    break
                i += 1
        i += 1
    return src_html[start.end() : i - 1]


def i18n_str(block: str, key: str) -> str:
    m = re.search(rf"\b{key}:'((?:\\'|[^'])*)'", block)
    if not m:
        sys.exit(f"I18N key {key!r} missing")
    return m.group(1).replace("\\'", "'")


def i18n_about(block: str):
    m = re.search(r"\babout:\[([^\]]*)\]", block)
    if not m:
        sys.exit("I18N about[] missing")
    return re.findall(r"'([^']*)'", m.group(1))


def count_entries(content_root: str) -> int:
    d = os.path.join(ROOT, content_root)
    if not os.path.isdir(d):
        sys.exit(f"contentRoot missing: {content_root}")
    n = 0
    for f in os.listdir(d):
        path = os.path.join(d, f)
        if not (f.endswith(".md") and os.path.isfile(path)):
            continue
        with open(path, encoding="utf-8") as fh:
            t = fh.read()
        n += len(re.findall(r"^### \d+\. ", t, re.MULTILINE))
    return n


def by_code(langs):
    return {entry["code"]: entry for entry in langs}


def apply_lang_head(html: str, src_for_i18n: str, lang_meta: dict, path_suffix: str) -> str:
    lang = lang_meta["code"]
    block = i18n_block(src_for_i18n, lang)
    title = i18n_str(block, "title")
    meta_desc = i18n_str(block, "metaDesc")
    keywords = i18n_str(block, "keywords")
    author = i18n_str(block, "author")
    html_lang = lang_meta["htmlLang"] or i18n_str(block, "htmlLang")
    about = i18n_about(block)
    pages = count_entries(lang_meta["contentRoot"])
    page_url = f"{HOST}/{path_suffix}"
    locale = lang_meta["ogLocale"]
    in_lang = lang_meta["inLanguage"]
    og = og_image_url(lang)

    html = HTML_LANG_RE.sub(rf"\1{html_lang}\2", html, count=1)
    html = TITLE_RE.sub(f"<title>{esc_attr(title)}</title>", html, count=1)
    html = META_NAME_RE["description"].sub(
        f'<meta name="description" content="{esc_attr(meta_desc)}">', html, count=1
    )
    html = META_NAME_RE["keywords"].sub(
        f'<meta name="keywords" content="{esc_attr(keywords)}">', html, count=1
    )
    html = META_NAME_RE["author"].sub(
        f'<meta name="author" content="{esc_attr(author)}">', html, count=1
    )
    html = CANON_RE.sub(f'<link rel="canonical" href="{page_url}">', html, count=1)
    html = OGURL_RE.sub(f'<meta property="og:url" content="{page_url}">', html, count=1)
    html = OGIMG_RE.sub(f'<meta property="og:image" content="{og}">', html, count=1)
    html = TWIMG_RE.sub(f'<meta name="twitter:image" content="{og}">', html, count=1)
    html = OG_PROP_RE["og:site_name"].sub(
        f'<meta property="og:site_name" content="{esc_attr(title)}">', html, count=1
    )
    html = OG_PROP_RE["og:locale"].sub(
        f'<meta property="og:locale" content="{locale}">', html, count=1
    )
    html = OG_PROP_RE["og:title"].sub(
        f'<meta property="og:title" content="{esc_attr(title)}">', html, count=1
    )
    html = OG_PROP_RE["og:description"].sub(
        f'<meta property="og:description" content="{esc_attr(meta_desc)}">',
        html,
        count=1,
    )
    html = TW_RE["twitter:title"].sub(
        f'<meta name="twitter:title" content="{esc_attr(title)}">', html, count=1
    )
    html = TW_RE["twitter:description"].sub(
        f'<meta name="twitter:description" content="{esc_attr(meta_desc)}">',
        html,
        count=1,
    )

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": page_url + "#website",
                "url": page_url,
                "name": title,
                "description": meta_desc,
                "inLanguage": in_lang,
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": {
                        "@type": "EntryPoint",
                        "urlTemplate": page_url + "?q={search_term_string}",
                    },
                    "query-input": "required name=search_term_string",
                },
                "isBasedOn": ORIGIN_PAGES,
                "sameAs": [ORIGIN_PAGES, ORIGIN_REPO],
            },
            {
                "@type": "Book",
                "@id": page_url + "#book",
                "name": title,
                "url": page_url,
                "inLanguage": in_lang,
                "bookFormat": "https://schema.org/EBook",
                "numberOfPages": pages,
                "license": "https://unlicense.org/",
                "abstract": meta_desc,
                "about": about,
                "isAccessibleForFree": True,
                "isBasedOn": ORIGIN_PAGES,
                "sameAs": [ORIGIN_PAGES, ORIGIN_REPO],
            },
        ],
    }
    ld_html = f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False, indent=1)}\n</script>'
    html, n = LD_RE.subn(ld_html, html, count=1)
    if n != 1:
        sys.exit(f"JSON-LD block not replaced for lang={lang}")
    return html


def inject_root(src: str, langs, primary: str) -> str:
    payload = langs_payload(langs, primary)
    script = langs_script(payload)
    if not LANGS_BLOCK_RE.search(src):
        sys.exit("site/index.html: missing /* HTLB_LANGS_BEGIN */ marker script")
    src = LANGS_BLOCK_RE.sub(script, src, count=1)

    menu = menu_html(langs)
    menu_re = re.compile(r'<div class="lang-menu" role="menu">.*?</div>', re.DOTALL)
    if not menu_re.search(src):
        sys.exit("site/index.html: lang-menu not found")
    src = menu_re.sub(menu, src, count=1)

    # Router page OG → primary locale image
    og = og_image_url(primary)
    src = OGIMG_RE.sub(f'<meta property="og:image" content="{og}">', src, count=1)
    return TWIMG_RE.sub(f'<meta name="twitter:image" content="{og}">', src, count=1)


def build_locale_page(src: str, bootstrap_tpl: str, v2css: str, lang_meta: dict) -> str:
    lang = lang_meta["code"]
    page = src.replace(
        bootstrap_tpl,
        (
            f"<script>window.__HTLB_LANG__='{lang}';window.__HTLB_BASE__='../';"
            "window.__HTLB_V2__=1;document.documentElement.classList.add('v2');</script>"
        ),
    )
    # Locale pages live in site/{lang}/; content is fetched from the flat Pages root.
    page = page.replace('href="README', 'href="../README').replace('href="book/', 'href="../book/')
    # Skin is inlined (tools/v2.css); drop the router stylesheet link so it is not
    # resolved as site/{lang}/assets/v2.css.
    page = STYLESHEET_V2_RE.sub("", page, count=1)
    if not STYLE_RE.search(page):
        sys.exit("site/index.html: <style> block not found")
    page = STYLE_RE.sub(lambda _: "<style>\n" + v2css + "\n</style>", page, count=1)
    return apply_lang_head(page, src, lang_meta, lang + "/")


def main() -> int:
    if not os.path.isfile(INDEX_PATH):
        sys.exit(f"missing {INDEX_PATH}")

    langs, primary = load_langs()
    meta = by_code(langs)
    codes = [entry["code"] for entry in langs]
    v2css = sync_v2_css()

    src = open(INDEX_PATH, encoding="utf-8").read()
    m = BOOTSTRAP_RE.search(src)
    if not m:
        print(
            "WARNING: bootstrap placeholder not found — skipping per-language pages",
            file=sys.stderr,
        )
        return 0
    bootstrap_tpl = m.group(0)

    for code in codes:
        i18n_block(src, code)

    src = inject_root(src, langs, primary)
    write(INDEX_PATH, src)

    for lang in codes:
        page = build_locale_page(src, bootstrap_tpl, v2css, meta[lang])
        write(os.path.join(SITE, lang, "index.html"), page)

    return 0


if __name__ == "__main__":
    sys.exit(main())
