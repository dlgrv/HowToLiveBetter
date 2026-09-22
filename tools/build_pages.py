#!/usr/bin/env python3
"""Generate language pages.

Default (v2 editorial skin):  {ru,en,zh}/index.html
Legacy (v1 skin):             v1/{ru,en,zh}/index.html
Back-compat redirects:        v2/{ru,en,zh}/index.html → ../../{lang}/

Root index.html stays the source template (v1 styles inline); build does not overwrite it.
Root redirects to /{lang}/ via a small script in index.html (zh auto → original site).

I18N in index.html is SSOT for title/metaDesc/keywords/author/about/htmlLang;
this script extracts those fields (no separate META prose map).
numberOfPages = count of `### N. ` entries under book/{lang}/ (zh: book/*.md).

Run from repo root:  python3 tools/build_pages.py
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
m = re.search(r'<script>/\* per-language override.*?</script>', src)
if not m:
    sys.exit('root index.html: bootstrap placeholder not found; add the __HTLB_LANG__/__HTLB_BASE__ placeholder script after <head> first')
tpl = m.group(0)
STYLE_RE = re.compile(r'<style>.*?</style>', re.S)
v2css = open(os.path.join(ROOT, 'tools', 'v2.css'), encoding='utf-8').read()
if not STYLE_RE.search(src):
    sys.exit('root index.html: <style> block not found')

HOST = 'https://dlgrv.github.io/HowToLiveBetter'
ORIGIN_PAGES = 'https://eternity4719.github.io/HowToLiveBetter/'
ORIGIN_REPO = 'https://github.com/eternity4719/HowToLiveBetter'
OG_IMAGE = HOST + '/og.png'

# Templates may still mention either host before rewrite
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


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)
    print('built', os.path.relpath(path, ROOT))


def esc_attr(s):
    return (s.replace('&', '&amp;').replace('"', '&quot;')
             .replace('<', '&lt;').replace('>', '&gt;'))


def i18n_block(src_html, lang):
    """Slice the I18N.{lang}:{ ... } object body from index.html (brace-aware)."""
    start = re.search(rf'\n {lang}:\{{', src_html)
    if not start:
        sys.exit('I18N block not found for lang=%s' % lang)
    i = start.end()  # after opening {
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


def count_entries(lang):
    """numberOfPages = ### N. headings in book text (sync with site cards)."""
    n = 0
    if lang == 'zh':
        d = os.path.join(ROOT, 'book')
        files = [f for f in os.listdir(d) if f.endswith('.md') and os.path.isfile(os.path.join(d, f))]
    else:
        d = os.path.join(ROOT, 'book', lang)
        files = [f for f in os.listdir(d) if f.endswith('.md')]
    for f in files:
        t = open(os.path.join(d, f), encoding='utf-8').read()
        n += len(re.findall(r'^### \d+\. ', t, re.M))
    return n


def html_lang_attr(lang, html_lang):
    # Prefer I18N htmlLang; force zh-CN for zh
    if lang == 'zh':
        return 'zh-CN'
    return html_lang or lang


def apply_lang_head(html, lang, path_suffix):
    """path_suffix e.g. 'ru/' or 'v1/ru/'."""
    block = i18n_block(src, lang)
    title = i18n_str(block, 'title')
    meta_desc = i18n_str(block, 'metaDesc')
    keywords = i18n_str(block, 'keywords')
    author = i18n_str(block, 'author')
    html_lang = html_lang_attr(lang, i18n_str(block, 'htmlLang'))
    about = i18n_about(block)
    pages = count_entries(lang)
    page_url = '%s/%s' % (HOST, path_suffix)
    locale = {'ru': 'ru_RU', 'en': 'en_US', 'zh': 'zh_CN'}[lang]
    in_lang = {'ru': 'ru', 'en': 'en', 'zh': 'zh-CN'}[lang]

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
    ld_html = '<script type="application/ld+json">\n%s\n</script>' % json.dumps(ld, ensure_ascii=False, indent=1)
    html, n = LD_RE.subn(ld_html, html, count=1)
    if n != 1:
        sys.exit('JSON-LD block not replaced for lang=%s' % lang)
    return html


# ---------- default = v2 editorial under /{lang}/ ----------
for lang in ('ru', 'en', 'zh'):
    d = src.replace(tpl, "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../';window.__HTLB_V2__=1;document.documentElement.classList.add('v2');</script>" % lang)
    d = d.replace('href="README', 'href="../README').replace('href="book/', 'href="../book/')
    d = STYLE_RE.sub(lambda _: '<style>\n' + v2css + '\n</style>', d, count=1)
    d = apply_lang_head(d, lang, lang + '/')
    write(os.path.join(ROOT, lang, 'index.html'), d)

# ---------- legacy v1 under /v1/{lang}/ ----------
for lang in ('ru', 'en', 'zh'):
    d = src.replace(tpl, "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../../';</script>" % lang)
    d = d.replace('href="README', 'href="../../README').replace('href="book/', 'href="../../book/')
    d = apply_lang_head(d, lang, 'v1/%s/' % lang)
    write(os.path.join(ROOT, 'v1', lang, 'index.html'), d)

# ---------- back-compat: /v2/{lang}/ → /{lang}/ ----------
for lang in ('ru', 'en', 'zh'):
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
''' % (html_lang_attr(lang, lang), lang, HOST, lang, lang, lang)
    write(os.path.join(ROOT, 'v2', lang, 'index.html'), html)
