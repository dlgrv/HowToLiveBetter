#!/usr/bin/env python3
"""Generate language pages from tools/langs.json + root index.html.

Default (v2 editorial skin):  {lang}/index.html
Legacy (v1 skin):             v1/{lang}/index.html
Back-compat redirects:        v2/{lang}/index.html → ../../{lang}/

Also patches the committed root index.html HTLB_LANGS marker from langs.json
(one inject contract — runtime reads only that block).

I18N prose stays in index.html; every langs.json code must have an I18N.{code}:{…} block.

Run from repo root:  python3 tools/build_pages.py
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS_PATH = os.path.join(ROOT, 'tools', 'langs.json')
INDEX_PATH = os.path.join(ROOT, 'index.html')

HOST = 'https://dlgrv.github.io/HowToLiveBetter'
ORIGIN_PAGES = 'https://eternity4719.github.io/HowToLiveBetter/'
ORIGIN_REPO = 'https://github.com/eternity4719/HowToLiveBetter'
OG_IMAGE = HOST + '/og.png'

CANON_RE = re.compile(r'<link rel="canonical" href="[^"]*">')
OGURL_RE = re.compile(r'<meta property="og:url" content="[^"]*">')
OGIMG_RE = re.compile(r'<meta property="og:image" content="[^"]*">')
TWIMG_RE = re.compile(r'<meta name="twitter:image" content="[^"]*">')
HTML_LANG_RE = re.compile(r'(<html\s[^>]*lang=")[^"]*(")')
TITLE_RE = re.compile(r'<title>[^<]*</title>')
META_NAME_RE = {
    'description': re.compile(r'<meta name="description" content="[^"]*">'),
    'keywords': re.compile(r'<meta name="keywords" content="[^"]*">'),
    'author': re.compile(r'<meta name="author" content="[^"]*">'),
}
OG_PROP_RE = {
    'og:site_name': re.compile(r'<meta property="og:site_name" content="[^"]*">'),
    'og:locale': re.compile(r'<meta property="og:locale" content="[^"]*">'),
    'og:title': re.compile(r'<meta property="og:title" content="[^"]*">'),
    'og:description': re.compile(r'<meta property="og:description" content="[^"]*">'),
}
TW_RE = {
    'twitter:title': re.compile(r'<meta name="twitter:title" content="[^"]*">'),
    'twitter:description': re.compile(r'<meta name="twitter:description" content="[^"]*">'),
}
LD_RE = re.compile(r'<script type="application/ld\+json">\s*.*?\s*</script>', re.S)
STYLE_RE = re.compile(r'<style>.*?</style>', re.S)
LANGS_BLOCK_RE = re.compile(
    r'<script>\s*/\* HTLB_LANGS_BEGIN \*/.*?/\* HTLB_LANGS_END \*/\s*</script>',
    re.S)


def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)
    print('built', os.path.relpath(path, ROOT))


def esc_attr(s):
    return (s.replace('&', '&amp;').replace('"', '&quot;')
             .replace('<', '&lt;').replace('>', '&gt;'))


def load_langs():
    data = json.load(open(LANGS_PATH, encoding='utf-8'))
    langs = data.get('languages')
    if not isinstance(langs, list) or not langs:
        sys.exit('tools/langs.json: languages[] required')
    primary = None
    codes = []
    for L in langs:
        for key in ('code', 'contentRoot', 'readme', 'htmlLang', 'ogLocale', 'inLanguage',
                    'shortLabel', 'menuLabel'):
            if key not in L or not L[key]:
                sys.exit('tools/langs.json: language missing %r' % key)
        codes.append(L['code'])
        if L.get('primary'):
            if primary:
                sys.exit('tools/langs.json: only one primary language allowed')
            primary = L['code']
    if not primary:
        sys.exit('tools/langs.json: set primary:true on exactly one language')
    return langs, primary


def langs_payload(langs, primary):
    return {
        'codes': [L['code'] for L in langs],
        'primary': primary,
        'shortLabels': {L['code']: L['shortLabel'] for L in langs},
        'menuLabels': {L['code']: L['menuLabel'] for L in langs},
        'readmes': {L['code']: L['readme'] for L in langs},
        'ogLocales': {L['code']: L['ogLocale'] for L in langs},
        'inLanguages': {L['code']: L['inLanguage'] for L in langs},
    }


def langs_script(payload):
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return (
        '<script>\n'
        '/* HTLB_LANGS_BEGIN */\n'
        'window.__HTLB_LANGS__=%s;\n'
        '/* HTLB_LANGS_END */\n'
        '</script>'
    ) % body


def menu_html(langs):
    buttons = '\n'.join(
        '          <button role="menuitem" data-lang="%s">%s</button>' % (
            L['code'], esc_attr(L['menuLabel']))
        for L in langs)
    return (
        '        <div class="lang-menu" role="menu">\n'
        '%s\n'
        '        </div>'
    ) % buttons


def i18n_block(src_html, lang):
    """Slice the I18N.{lang}:{ ... } object body from index.html (brace-aware)."""
    start = re.search(rf'\n {lang}:\{{', src_html)
    if not start:
        sys.exit('I18N block not found for lang=%s (add I18N.%s:{…} in index.html)' % (lang, lang))
    i = start.end()
    depth = 1
    while i < len(src_html) and depth:
        c = src_html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c == "'":
            i += 1
            while i < len(src_html):
                if src_html[i] == '\\':
                    i += 2
                    continue
                if src_html[i] == "'":
                    break
                i += 1
        i += 1
    return src_html[start.end():i - 1]


def i18n_str(block, key):
    m = re.search(rf"\b{key}:'((?:\\'|[^'])*)'", block)
    if not m:
        sys.exit('I18N key %r missing' % key)
    return m.group(1).replace("\\'", "'")


def i18n_about(block):
    m = re.search(r"\babout:\[([^\]]*)\]", block)
    if not m:
        sys.exit('I18N about[] missing')
    return re.findall(r"'([^']*)'", m.group(1))


def count_entries(content_root):
    d = os.path.join(ROOT, content_root)
    if not os.path.isdir(d):
        sys.exit('contentRoot missing: %s' % content_root)
    n = 0
    for f in os.listdir(d):
        path = os.path.join(d, f)
        if not (f.endswith('.md') and os.path.isfile(path)):
            continue
        t = open(path, encoding='utf-8').read()
        n += len(re.findall(r'^### \d+\. ', t, re.M))
    return n


def by_code(langs):
    return {L['code']: L for L in langs}


def apply_lang_head(html, src_for_i18n, lang_meta, path_suffix):
    lang = lang_meta['code']
    block = i18n_block(src_for_i18n, lang)
    title = i18n_str(block, 'title')
    meta_desc = i18n_str(block, 'metaDesc')
    keywords = i18n_str(block, 'keywords')
    author = i18n_str(block, 'author')
    html_lang = lang_meta['htmlLang'] or i18n_str(block, 'htmlLang')
    about = i18n_about(block)
    pages = count_entries(lang_meta['contentRoot'])
    page_url = '%s/%s' % (HOST, path_suffix)
    locale = lang_meta['ogLocale']
    in_lang = lang_meta['inLanguage']

    html = HTML_LANG_RE.sub(r'\1%s\2' % html_lang, html, count=1)
    html = TITLE_RE.sub('<title>%s</title>' % esc_attr(title), html, count=1)
    html = META_NAME_RE['description'].sub(
        '<meta name="description" content="%s">' % esc_attr(meta_desc), html, count=1)
    html = META_NAME_RE['keywords'].sub(
        '<meta name="keywords" content="%s">' % esc_attr(keywords), html, count=1)
    html = META_NAME_RE['author'].sub(
        '<meta name="author" content="%s">' % esc_attr(author), html, count=1)
    html = CANON_RE.sub('<link rel="canonical" href="%s">' % page_url, html, count=1)
    html = OGURL_RE.sub('<meta property="og:url" content="%s">' % page_url, html, count=1)
    html = OGIMG_RE.sub('<meta property="og:image" content="%s">' % OG_IMAGE, html, count=1)
    html = TWIMG_RE.sub('<meta name="twitter:image" content="%s">' % OG_IMAGE, html, count=1)
    html = OG_PROP_RE['og:site_name'].sub(
        '<meta property="og:site_name" content="%s">' % esc_attr(title), html, count=1)
    html = OG_PROP_RE['og:locale'].sub(
        '<meta property="og:locale" content="%s">' % locale, html, count=1)
    html = OG_PROP_RE['og:title'].sub(
        '<meta property="og:title" content="%s">' % esc_attr(title), html, count=1)
    html = OG_PROP_RE['og:description'].sub(
        '<meta property="og:description" content="%s">' % esc_attr(meta_desc), html, count=1)
    html = TW_RE['twitter:title'].sub(
        '<meta name="twitter:title" content="%s">' % esc_attr(title), html, count=1)
    html = TW_RE['twitter:description'].sub(
        '<meta name="twitter:description" content="%s">' % esc_attr(meta_desc), html, count=1)

    ld = {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'WebSite',
                '@id': page_url + '#website',
                'url': page_url,
                'name': title,
                'description': meta_desc,
                'inLanguage': in_lang,
                'potentialAction': {
                    '@type': 'SearchAction',
                    'target': {
                        '@type': 'EntryPoint',
                        'urlTemplate': page_url + '?q={search_term_string}',
                    },
                    'query-input': 'required name=search_term_string',
                },
                'isBasedOn': ORIGIN_PAGES,
                'sameAs': [ORIGIN_PAGES, ORIGIN_REPO],
            },
            {
                '@type': 'Book',
                '@id': page_url + '#book',
                'name': title,
                'url': page_url,
                'inLanguage': in_lang,
                'bookFormat': 'https://schema.org/EBook',
                'numberOfPages': pages,
                'license': 'https://unlicense.org/',
                'abstract': meta_desc,
                'about': about,
                'isAccessibleForFree': True,
                'isBasedOn': ORIGIN_PAGES,
                'sameAs': [ORIGIN_PAGES, ORIGIN_REPO],
            },
        ],
    }
    ld_html = '<script type="application/ld+json">\n%s\n</script>' % json.dumps(
        ld, ensure_ascii=False, indent=1)
    html, n = LD_RE.subn(ld_html, html, count=1)
    if n != 1:
        sys.exit('JSON-LD block not replaced for lang=%s' % lang)
    return html


def inject_root(src, langs, primary):
    payload = langs_payload(langs, primary)
    script = langs_script(payload)
    if not LANGS_BLOCK_RE.search(src):
        sys.exit('root index.html: missing /* HTLB_LANGS_BEGIN */ marker script')
    src = LANGS_BLOCK_RE.sub(script, src, count=1)

    menu = menu_html(langs)
    menu_re = re.compile(
        r'<div class="lang-menu" role="menu">.*?</div>', re.S)
    if not menu_re.search(src):
        sys.exit('root index.html: lang-menu not found')
    src = menu_re.sub(menu, src, count=1)
    return src


def main():
    langs, primary = load_langs()
    meta = by_code(langs)
    codes = [L['code'] for L in langs]

    src = open(INDEX_PATH, encoding='utf-8').read()
    m = re.search(r'<script>/\* per-language override.*?</script>', src)
    if not m:
        sys.exit('root index.html: bootstrap placeholder not found')
    tpl = m.group(0)
    v2css = open(os.path.join(ROOT, 'tools', 'v2.css'), encoding='utf-8').read()
    if not STYLE_RE.search(src):
        sys.exit('root index.html: <style> block not found')

    # Fail loud if I18N missing for any registered lang
    for code in codes:
        i18n_block(src, code)

    src = inject_root(src, langs, primary)
    write(INDEX_PATH, src)

    # ---------- default = v2 editorial under /{lang}/ ----------
    for lang in codes:
        d = src.replace(
            tpl,
            "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../';"
            "window.__HTLB_V2__=1;document.documentElement.classList.add('v2');</script>" % lang)
        d = d.replace('href="README', 'href="../README').replace('href="book/', 'href="../book/')
        d = STYLE_RE.sub(lambda _: '<style>\n' + v2css + '\n</style>', d, count=1)
        d = apply_lang_head(d, src, meta[lang], lang + '/')
        write(os.path.join(ROOT, lang, 'index.html'), d)

    # ---------- legacy v1 under /v1/{lang}/ ----------
    for lang in codes:
        d = src.replace(
            tpl,
            "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../../';</script>" % lang)
        d = d.replace('href="README', 'href="../../README').replace('href="book/', 'href="../../book/')
        d = apply_lang_head(d, src, meta[lang], 'v1/%s/' % lang)
        write(os.path.join(ROOT, 'v1', lang, 'index.html'), d)

    # ---------- back-compat: /v2/{lang}/ → /{lang}/ ----------
    for lang in codes:
        hl = meta[lang]['htmlLang']
        html = '''<!doctype html>
<html lang="%s">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0;url=../../%s/">
<link rel="canonical" href="%s/%s/">
<title>Redirect</title>
<script>location.replace('../../%s/'+location.search+location.hash);</script>
</head>
<body><p><a href="../../%s/">Continue</a></p></body>
</html>
''' % (hl, lang, HOST, lang, lang, lang)
        write(os.path.join(ROOT, 'v2', lang, 'index.html'), html)


if __name__ == '__main__':
    main()
