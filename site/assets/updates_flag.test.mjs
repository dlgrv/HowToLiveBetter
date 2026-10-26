/**
 * Logic + contract tests for the "fresh" (updates.json) chips.
 *
 * The predicate lives inline in site/index.html and is copied by
 * build_pages.py into every site/<lang>/index.html. Tests extract the
 * shipped updMatch() from the actual HTML sources (so a forgotten rebuild
 * fails too) and assert the chips/URL wiring exists in every page.
 */
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');

/** Extract updMatch() from an index.html and compile it with UPD_DAY_MS. */
function updMatchOf(html, label) {
  const i = html.indexOf('function updMatch(');
  assert.ok(i >= 0, `updMatch not found in ${label}`);
  const end = html.indexOf('\n}', i);
  assert.ok(end > i, `updMatch body end not found in ${label}`);
  const src = html.slice(i, end + 2);
  return new Function('UPD_DAY_MS', `${src.replace('function updMatch', 'return function updMatch')};`)(
    86400000,
  );
}

function pages() {
  const pages = [['site/index.html', join(ROOT, 'site/index.html')]];
  for (const lang of ['en', 'ru', 'es', 'pt', 'ar', 'id']) {
    const p = join(ROOT, `site/${lang}/index.html`);
    if (existsSync(p)) pages.push([`site/${lang}/index.html`, p]);
  }
  return pages;
}

const NOW = Date.parse('2026-10-26');

for (const [label, path] of pages()) {
  const html = readFileSync(path, 'utf8');
  const updMatch = updMatchOf(html, label);

  test(`[${label}] updMatch window arithmetic`, () => {
    const e = { upd: { added: '2026-10-20', changed: '2026-10-25' } };
    assert.equal(updMatch(e, new Set(['changed']), 7, NOW), true);   // 1 day back
    assert.equal(updMatch(e, new Set(['changed']), 1, NOW), true);   // boundary: exactly 1 day is inside
    assert.equal(updMatch(e, new Set(['changed']), 0, NOW), false);  // same-day only
    assert.equal(updMatch(e, new Set(['added']), 6, NOW), true);     // exactly 6 days back
    assert.equal(updMatch(e, new Set(['added']), 5, NOW), false);
    assert.equal(updMatch(e, new Set(['added', 'changed']), 5, NOW), true); // OR across kinds
    assert.equal(updMatch(e, new Set(), 30, NOW), false);
    assert.equal(updMatch({}, new Set(['changed']), 30, NOW), false);
    assert.equal(updMatch({ upd: {} }, new Set(['changed']), 30, NOW), false);
  });

  test(`[${label}] fresh chips wiring exists`, () => {
    assert.ok(html.includes('data-dim="upd"'), 'upd chip group');
    assert.ok(html.includes('data-v="added"'), 'added chip');
    assert.ok(html.includes('data-v="changed"'), 'changed chip');
    assert.ok(html.includes('id="upd-days"'), 'days select');
    assert.ok(html.includes('id="upd-s"'), 'days hint (i18n-managed, not hardcoded)');
    assert.ok(/state\.days\s*=\s*parseInt\(p\.get\('days'\)/.test(html), 'readUrl days');
    assert.ok(/p\.set\('days'/.test(html), 'writeUrl days');
    assert.ok(html.includes("'upd'"), "DIMS includes 'upd'");
    assert.ok(html.includes('updMatch(e, state.upd, state.days)'), 'apply() predicate');
    assert.ok(html.includes("fetch('updates.json'"), 'init() feed fetch');
    assert.ok(html.includes("'updb'"), 'card badge');
    assert.ok(html.includes('updBadge'), 'badge i18n');
    assert.ok(html.includes("updS.textContent=t.updS"), 'hint i18n replacement');
  });

  test(`[${label}] every I18N block carries the fresh strings`, () => {
    for (const key of ['updH:', 'updS:', 'updAdded:', 'updChanged:', 'updDaysAria:', 'updBadge:']) {
      const n = (html.match(new RegExp(`\\b${key}`, 'g')) || []).length;
      assert.equal(n, 7, `${key} in 7 I18N blocks (got ${n})`);
    }
  });
}
