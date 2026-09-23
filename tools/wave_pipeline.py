#!/usr/bin/env python3
"""Пайплайн волны: сборка 3 языков указанных глав + verify + check_content.
Использование: python3 tools/wave_pipeline.py 02 05 06 ...
Печатает таблицу OK/FAIL по главе×языку и общий вердикт."""
import subprocess, sys, os, re

REPO = '/root/github/htlb-ru'
SCRIPTS = {'ru': 'assemble.py', 'en': 'assemble_en.py', 'es': 'assemble_es.py'}

def fname(lang, nn):
    for f in os.listdir(f'{REPO}/book/{lang}'):
        if f.startswith(nn + '-'):
            return f
    raise FileNotFoundError(f'{lang}/{nn}')

def main(chapters):
    rows, fails = [], 0
    for nn in chapters:
        for lang in ('ru', 'en', 'es'):
            bk = fname(lang, nn)
            out = f'{REPO}/book/{lang}/{bk}'
            r = subprocess.run(
                ['python3', f'tools/{SCRIPTS[lang]}', nn, f'/root/htlb-run-{lang}/{nn}', out],
                cwd=REPO, capture_output=True, text=True)
            asm = (r.stdout.strip().splitlines() or ['ERR: ' + r.stderr[-120:]])[-1]
            if not asm.startswith('OK'):
                rows.append((lang, nn, 'ASSEMBLE FAIL: ' + asm[:70])); fails += 1; continue
            v = subprocess.run(['python3', 'tools/verify.py', nn, '--lang', lang, '--file',
                                f'book/{lang}/{bk}'], cwd=REPO, capture_output=True, text=True)
            ok = any(l.startswith('OK') for l in v.stdout.splitlines())
            detail = next((l for l in v.stdout.splitlines() if l.startswith(('OK', 'FAIL'))), '')[:60]
            rows.append((lang, nn, detail))
            if not ok: fails += 1
    for lang, nn, st in rows:
        print(f'{lang} ch{nn}: {st}')
    print('---')
    print('VERDICT:', 'GREEN' if fails == 0 else f'{fails} FAIL(s)')
    return 0 if fails == 0 else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:] or ['02']))
