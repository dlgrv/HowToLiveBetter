#!/usr/bin/env python3
"""Generate per-language pages ru/en/zh/index.html from the root index.html.
Root index.html = auto-detect (navigator.language, fallback en); subdir pages force their language.
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
