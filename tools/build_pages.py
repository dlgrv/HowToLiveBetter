#!/usr/bin/env python3
"""Generate language pages.

Default (v2 editorial skin):  {ru,en,zh}/index.html
Legacy (v1 skin):             v1/{ru,en,zh}/index.html
Back-compat redirects:        v2/{ru,en,zh}/index.html → ../../{lang}/

Root index.html stays the source template (v1 styles inline); build does not overwrite it.
Root redirects to /{lang}/ via a small script in index.html.

Run from repo root:  python3 tools/build_pages.py
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT,'index.html'), encoding='utf-8').read()
m = re.search(r'<script>/\* per-language override.*?</script>', src)
if not m:
    sys.exit('root index.html: bootstrap placeholder not found; add the __HTLB_LANG__/__HTLB_BASE__ placeholder script after <head> first')
tpl = m.group(0)
CANON = '<link rel="canonical" href="https://eternity4719.github.io/HowToLiveBetter/">'
OGURL = '<meta property="og:url" content="https://eternity4719.github.io/HowToLiveBetter/">'
STYLE_RE = re.compile(r'<style>.*?</style>', re.S)
v2css = open(os.path.join(ROOT,'tools','v2.css'), encoding='utf-8').read()
if not STYLE_RE.search(src):
    sys.exit('root index.html: <style> block not found')

HOST = 'https://dlgrv.github.io/HowToLiveBetter'

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)
    print('built', os.path.relpath(path, ROOT))

# ---------- default = v2 editorial under /{lang}/ ----------
for lang in ('ru','en','zh'):
    d = src.replace(tpl, "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../';window.__HTLB_V2__=1;document.documentElement.classList.add('v2');</script>" % lang)
    d = d.replace('href="README', 'href="../README').replace('href="book/', 'href="../book/')
    d = STYLE_RE.sub(lambda _: '<style>\n' + v2css + '\n</style>', d, count=1)
    d = d.replace(CANON, '<link rel="canonical" href="%s/%s/">' % (HOST, lang))
    d = d.replace(OGURL, '<meta property="og:url" content="%s/%s/">' % (HOST, lang))
    write(os.path.join(ROOT, lang, 'index.html'), d)

# ---------- legacy v1 under /v1/{lang}/ ----------
for lang in ('ru','en','zh'):
    d = src.replace(tpl, "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../../';</script>" % lang)
    d = d.replace('href="README', 'href="../../README').replace('href="book/', 'href="../../book/')
    d = d.replace(CANON, '<link rel="canonical" href="%s/v1/%s/">' % (HOST, lang))
    d = d.replace(OGURL, '<meta property="og:url" content="%s/v1/%s/">' % (HOST, lang))
    write(os.path.join(ROOT, 'v1', lang, 'index.html'), d)

# ---------- back-compat: /v2/{lang}/ → /{lang}/ ----------
for lang in ('ru','en','zh'):
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
''' % (lang, lang, HOST, lang, lang, lang)
    write(os.path.join(ROOT, 'v2', lang, 'index.html'), html)
