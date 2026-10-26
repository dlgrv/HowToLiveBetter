/**
 * Logic tests for the site link rewriter (hrefOf/mkLink), extracted from the
 * shipped pages: chapter-file links must become in-reader #sec-NN jumps
 * (same tab), everything else keeps the GitHub-blob fallback (new tab).
 */
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');

function extractFn(html, name, label, args = []) {
  const i = html.indexOf(`function ${name}(`);
  assert.ok(i >= 0, `${name} not found in ${label}`);
  const end = html.indexOf('\n}', i);
  assert.ok(end > i, `${name} end not found in ${label}`);
  const src = html.slice(i, end + 2);
  return new Function(
    ...args.map((a) => a[0]),
    `${src.replace(`function ${name}`, `return function ${name}`)};`,
  )(...args.map((a) => a[1]));
}

function pages() {
  const pages = [['site/index.html', join(ROOT, 'site/index.html')]];
  for (const lang of ['en', 'ru', 'es', 'pt', 'ar', 'id']) {
    const p = join(ROOT, `site/${lang}/index.html`);
    if (existsSync(p)) pages.push([`site/${lang}/index.html`, p]);
  }
  return pages;
}

for (const [label, path] of pages()) {
  const html = readFileSync(path, 'utf8');
  const hrefOf = extractFn(html, 'hrefOf', label, [['REPO_BLOB', 'https://github.com/dlgrv/HowToLiveBetter/blob/main/']]);

  test(`[${label}] chapter links become in-reader anchors`, () => {
    assert.equal(hrefOf('../04-Do-Not-Waste-Time.md'), '#sec-04');
    assert.equal(hrefOf('13-Emergencies.md'), '#sec-13');
    assert.equal(hrefOf('../28-Оформление-внешности.md'), '#sec-28');
  });

  test(`[${label}] other relative links stay on GitHub blob`, () => {
    assert.equal(
      hrefOf('../../docs/research/ru/Выгоден-ли-брак.md'),
      'https://github.com/dlgrv/HowToLiveBetter/blob/main/docs/research/ru/%D0%92%D1%8B%D0%B3%D0%BE%D0%B4%D0%B5%D0%BD-%D0%BB%D0%B8-%D0%B1%D1%80%D0%B0%D0%BA.md',
    );
  });

  test(`[${label}] absolute and hash hrefs pass through`, () => {
    assert.equal(hrefOf('https://example.com/x'), 'https://example.com/x');
    assert.equal(hrefOf('#sec-10'), '#sec-10');
    assert.equal(hrefOf('mailto:a@b.c'), 'mailto:a@b.c');
  });

  test(`[${label}] mkLink keeps hash links in the same tab`, () => {
    const i = html.indexOf('function mkLink(');
    assert.ok(i >= 0, `mkLink not found in ${label}`);
    const end = html.indexOf('\n}', i);
    const src = html.slice(i, end + 2);
    const factory = new Function(
      'document',
      `${src.replace('function mkLink', 'return function mkLink')};`,
    );
    const el = () => ({ set href(v) { this._h = v; }, get href() { return this._h; } });
    const mkLink = factory({ createElement: el });
    const a = mkLink('#sec-10', 'x');
    assert.equal(a.target, undefined);
    const b = mkLink('https://x/', 'y');
    assert.equal(b.target, '_blank');
    assert.equal(b.rel, 'noopener');
  });
}
