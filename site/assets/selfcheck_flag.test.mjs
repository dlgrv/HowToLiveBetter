/**
 * Logic + contract tests for the self-check mode (?mode=selfcheck).
 *
 * The scoring model lives inline in site/index.html and is copied into every
 * site/<lang>/index.html. Tests extract the shipped scScore()/scTop() from
 * the actual HTML sources (a forgotten rebuild fails) and assert the mode
 * wiring (button, URL param, sync calls) in every page + interactive.js.
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
  assert.ok(end > i, `${name} body end not found in ${label}`);
  const src = html.slice(i, end + 2);
  const argNames = args.map((a) => a[0]);
  const argVals = args.map((a) => a[1]);
  return new Function(
    ...argNames,
    `${src.replace(`function ${name}`, `return function ${name}`)};`,
  )(...argVals);
}

function pages() {
  const pages = [['site/index.html', join(ROOT, 'site/index.html')]];
  for (const lang of ['en', 'ru', 'es', 'pt', 'ar', 'id']) {
    const p = join(ROOT, `site/${lang}/index.html`);
    if (existsSync(p)) pages.push([`site/${lang}/index.html`, p]);
  }
  return pages;
}

const ENTRIES = [
  { id: '1-1', sec: '1', n: '1', ratio: '极高', cs: 0 },
  { id: '1-2', sec: '1', n: '2', ratio: '高', cs: 2 },
  { id: '2-1', sec: '2', n: '1', ratio: '一般', cs: 1 },
  { id: '2-2', sec: '2', n: '2', ratio: '极高', cs: 4 },
];

for (const [label, path] of pages()) {
  const html = readFileSync(path, 'utf8');
  const scScore = extractFn(html, 'scScore', label);
  const scTop = extractFn(html, 'scTop', label, [['SC_RATIO_W', { '极高': 0, '高': 1, '一般': 2 }]]);

  test(`[${label}] scScore counts answered only, ordered by section`, () => {
    const got = scScore(ENTRIES, { '1-1': 1, '1-2': 0, '2-1': 0 });
    assert.deepEqual(got, [
      { sec: '1', total: 2, yes: 1 },
      { sec: '2', total: 1, yes: 0 },
    ]);
    assert.deepEqual(scScore(ENTRIES, {}), []);
  });

  test(`[${label}] scTop orders unmet by ratio then cost, ignores yes`, () => {
    const all = scTop(ENTRIES, { '1-1': 0, '1-2': 0, '2-1': 0, '2-2': 0 });
    assert.deepEqual(all.map((e) => e.id), ['1-1', '2-2', '1-2', '2-1']);
    const one = scTop(ENTRIES, { '1-1': 1, '2-2': 0 });
    assert.deepEqual(one.map((e) => e.id), ['2-2']);
    assert.equal(scTop(ENTRIES, { '1-1': 0, '1-2': 0, '2-1': 0, '2-2': 0 }, 2).length, 2);
  });

  test(`[${label}] selfcheck mode wiring exists`, () => {
    assert.ok(html.includes('id="selfcheck-btn"'), 'sidebar entry button');
    assert.ok(html.includes('id="sc"'), 'mode section');
    assert.ok(html.includes('id="sc-yes"') && html.includes('id="sc-no"'), 'answer buttons');
    assert.ok(/p\.get\('mode'\)\s*===\s*'selfcheck'/.test(html), 'readUrl mode');
    assert.ok(/p\.set\('mode'/.test(html), 'writeUrl mode');
    assert.ok(html.includes("state.mode === 'selfcheck'"), 'auto-enter');
    assert.ok(/addEventListener\('click', scEnter\)/.test(html), 'enter handler');
    assert.ok(/addEventListener\('click', scExit\)/.test(html), 'exit handler');
    assert.ok(/scAnswer\(1\)/.test(html) && /scAnswer\(0\)/.test(html), 'answer wiring');
    assert.ok(/if \(SC\.on\) scExit\(\)/.test(html), 'Esc exits');
    assert.ok(html.includes("localStorage.getItem(SC_KEY)"), 'local persistence');
  });

  test(`[${label}] every I18N block carries selfcheck strings`, () => {
    for (const key of ['scStart:', 'scExit:', 'scYes:', 'scNo:', 'scBack:', 'scResultsH:', 'scTopH:', 'scRestart:', 'scOf:', 'scNote:']) {
      const n = (html.match(new RegExp(`\\b${key}`, 'g')) || []).length;
      assert.equal(n, 7, `${key} in 7 I18N blocks (got ${n})`);
    }
  });
}

test('interactive.js selfcheck sync contract', () => {
  const js = readFileSync(join(ROOT, 'site/assets/interactive.js'), 'utf8');
  assert.ok(js.includes("api('/selfcheck'"), 'API endpoint used');
  assert.ok(/method:\s*'PUT'/.test(js) && /body:\s*\{\s*answers:/.test(js), 'PUT full map');
  assert.ok(js.includes('selfcheck: { load: scLoad, save: scSave }'), 'exported for the site');
  // Site side calls save after each answer; load must be cached (one GET per session).
  assert.ok(js.includes('if (scRemote) return scRemote'), 'load cached');
});
