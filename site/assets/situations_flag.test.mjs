/**
 * Logic + contract tests for the situation chips (?sit=free|d30|35|60).
 * Extracts the shipped SITUATIONS/sitMatch from every page and checks the
 * wiring (chip group, DIMS, apply predicate, i18n coverage).
 */
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');

function pages() {
  const pages = [['site/index.html', join(ROOT, 'site/index.html')]];
  for (const lang of ['en', 'ru', 'es', 'pt', 'ar', 'id']) {
    const p = join(ROOT, `site/${lang}/index.html`);
    if (existsSync(p)) pages.push([`site/${lang}/index.html`, p]);
  }
  return pages;
}

function extractSituation(html, label) {
  const i = html.indexOf('const SITUATIONS = {');
  assert.ok(i >= 0, `SITUATIONS not found in ${label}`);
  const end = html.indexOf('\n};', i);
  assert.ok(end > i, `SITUATIONS end not found in ${label}`);
  const table = html.slice(i, end + 3);
  const fnI = html.indexOf('function sitMatch(');
  const fnEnd = html.indexOf('\n}', fnI);
  assert.ok(fnI >= 0 && fnEnd > fnI, `sitMatch not found in ${label}`);
  const fn = html.slice(fnI, fnEnd + 2);
  return new Function(`${table}\n${fn.replace('function sitMatch', 'return function sitMatch')};\n`)();
}

const E = {
  ch16: { sec: '16', money: '多', time: '中', will: '些' },
  ch17: { sec: '17', money: '0', time: '少', will: '否' },
  ch01: { sec: '01', money: '0', time: '少', will: '否' },
};

for (const [label, path] of pages()) {
  const html = readFileSync(path, 'utf8');
  const sitMatch = extractSituation(html, label);

  test(`[${label}] sitMatch: age tags and derived tags`, () => {
    assert.equal(sitMatch(E.ch16, new Set(['60'])), true);
    assert.equal(sitMatch(E.ch16, new Set(['35'])), true);
    assert.equal(sitMatch(E.ch17, new Set(['35'])), false);
    assert.equal(sitMatch(E.ch01, new Set(['35', '60'])), false);
    assert.equal(sitMatch(E.ch01, new Set(['free'])), true);
    assert.equal(sitMatch(E.ch01, new Set(['d30'])), true);
    assert.equal(sitMatch({ sec: '01', money: '少' }, new Set(['free'])), false);
    assert.equal(sitMatch({ sec: '01', time: '少', will: '是' }, new Set(['d30'])), false);
    assert.equal(sitMatch(E.ch16, new Set()), false);
  });

  test(`[${label}] situation chips wiring exists`, () => {
    assert.ok(html.includes('data-dim="sit"'), 'chip group');
    for (const v of ['free', 'd30', '35', '60']) {
      assert.ok(html.includes(`data-v="${v}"`), `chip ${v}`);
    }
    assert.ok(html.includes("'sit'"), "DIMS includes 'sit'");
    assert.ok(html.includes('sitMatch(e, state.sit)'), 'apply predicate');
    assert.ok(html.includes('id="sit-h"'), 'group header');
  });

  test(`[${label}] every I18N block carries situation strings`, () => {
    for (const key of ['sitH:', 'sitFree:', 'sitD30:', 'sit35:', 'sit60:', 'sitS:']) {
      const n = (html.match(new RegExp(`\\b${key}`, 'g')) || []).length;
      assert.equal(n, 7, `${key} in 7 I18N blocks (got ${n})`);
    }
  });
}
