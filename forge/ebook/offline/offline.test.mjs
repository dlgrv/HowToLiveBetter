/**
 * Tests for the single-file offline HTML builder (forge/ebook/offline/build.mjs).
 *
 * splitChapter is tested on fixtures; buildOffline is run for real locales
 * into a temp dir and the output invariants are asserted (all sections
 * present, no relative links left dangling, grade/hay data on items, size).
 */
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, test } from 'node:test';

import { buildOffline, splitChapter } from './build.mjs';
import { readBook } from '../book.mjs';

const TMP = mkdtempSync(join(tmpdir(), 'htlb-offline-'));
after(() => rmSync(TMP, { recursive: true, force: true }));

const CH = `# 03. Не трать силы зря

Вступление раздела.

### 1. Первый пункт
- 成本： бесплатно
- 说人话： просто и ясно
- 收益： много
- 证据等级： A
- 来源： <https://example.com/1>
- 备注： заметка

### 2. Второй пункт
- 成本： мало
- 证据等级： B

## Ссылки
хвост`;

test('splitChapter: headings, intro, items, grades, tail section', () => {
  const ch = splitChapter(CH);
  assert.equal(ch.n, '03');
  assert.equal(ch.title, 'Не трать силы зря');
  assert.equal(ch.intro.trim(), 'Вступление раздела.');
  assert.equal(ch.items.length, 2);
  assert.equal(ch.items[0].n, '1');
  assert.equal(ch.items[0].grade, 'A');
  assert.equal(ch.items[1].grade, 'B');
  // The trailing '## Ссылки' tail must not leak into item 2.
  assert.ok(!ch.items[1].body.join('\n').includes('Ссылки'));
});

test('splitChapter: ru grade label variant', () => {
  const ch = splitChapter('# 01. T\n\n### 1. Один\n- Уровень доказательности: C\n');
  assert.equal(ch.items[0].grade, 'C');
});

test('buildOffline(en): real build invariants', () => {
  const out = join(TMP, 'HowToLiveBetter-en.html');
  const stats = buildOffline('en', out);
  const html = readFileSync(out, 'utf8');
  const book = readBook('en');

  assert.ok(stats.sections === book.bookFiles.length && stats.sections >= 30, `sections ${stats.sections}`);
  assert.ok(stats.items >= 600, `items ${stats.items}`);
  assert.ok(html.startsWith('<!doctype html>'));
  assert.match(html, /<html lang="en">/);
  assert.ok(!/dir="rtl"/.test(html), 'en must not be rtl');
  assert.ok(html.includes('<script>') && html.includes("getElementById('q')"), 'filter script');
  // Every section anchor from the nav resolves.
  for (const m of html.matchAll(/href="#(sec-\d+|doc-\d+|front|about)"/g)) {
    assert.ok(html.includes(`id="${m[1]}"`), `anchor ${m[1]} missing`);
  }
  // No dangling relative links survive in the standalone file.
  assert.ok(!/href="(?!https?:|#|mailto:)[^"]*"/.test(html), 'non-absolute href left');
  // Item data for the filter.
  const graded = (html.match(/data-grade="[ABC]"/g) || []).length;
  assert.ok(graded >= Math.floor(stats.items * 0.9), `graded ${graded}/${stats.items}`);
  assert.ok(stats.bytes > 500_000 && stats.bytes < 15 * 1_048_576, `size ${stats.bytes}`);
});

test('buildOffline(ar): rtl direction', () => {
  const out = join(TMP, 'HowToLiveBetter-ar.html');
  buildOffline('ar', out);
  const html = readFileSync(out, 'utf8');
  assert.match(html, /<html lang="ar" dir="rtl">/);
});
