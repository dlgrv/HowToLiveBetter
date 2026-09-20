#!/usr/bin/env python3
"""Generate per-language pages ru/en/zh/index.html (v1 skin) and v2/{ru,en,zh}/index.html (editorial skin).

Root index.html = auto-detect (navigator.language, fallback en); subdir pages force their language.
v2 pages swap the <style> block for tools/v2.css and set __HTLB_BASE__='../../' so the same
README/book data files are fetched from the repo root (no data duplication).
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
for lang in ('ru','en','zh'):
    d = src.replace(tpl, "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../';</script>" % lang)
    d = d.replace(CANON, '<link rel="canonical" href="https://dlgrv.github.io/HowToLiveBetter/%s/">' % lang)
    d = d.replace(OGURL, '<meta property="og:url" content="https://dlgrv.github.io/HowToLiveBetter/%s/">' % lang)
    out = os.path.join(ROOT, lang, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out,'w',encoding='utf-8').write(d)
    print('built', os.path.relpath(out, ROOT))

# ---------- v2 (editorial skin) ----------
V2MARK = '<script>window.__HTLB_V2__=1;</script>'          # injected in root index.html <head>
STYLE_RE = re.compile(r'<style>.*?</style>', re.S)
v2css = open(os.path.join(ROOT,'tools','v2.css'), encoding='utf-8').read()
if not STYLE_RE.search(src):
    sys.exit('root index.html: <style> block not found')
if V2MARK not in src:
    print('note: root index.html has no %s marker; v2 pages get skin flag only via generation' % V2MARK)
for lang in ('ru','en','zh'):
    d = src.replace(tpl, "<script>window.__HTLB_LANG__='%s';window.__HTLB_BASE__='../../';window.__HTLB_V2__=1;</script>" % lang)
    # README/book links in header & noscript point to repo root; v2 lives one level deeper
    d = d.replace('href="README', 'href="../../README').replace('href="book/', 'href="../../book/')
    d = STYLE_RE.sub(lambda _: '<style>\n' + v2css + '\n</style>', d, count=1)
    d = d.replace(CANON, '<link rel="canonical" href="https://dlgrv.github.io/HowToLiveBetter/v2/%s/">' % lang)
    d = d.replace(OGURL, '<meta property="og:url" content="https://dlgrv.github.io/HowToLiveBetter/v2/%s/">' % lang)
    out = os.path.join(ROOT, 'v2', lang, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out,'w',encoding='utf-8').write(d)
    print('built', os.path.relpath(out, ROOT))
