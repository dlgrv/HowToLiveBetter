/**
 * Logic + contract tests for the sidebar section summary tooltip (issue #127).
 *
 * tipClamp is extracted from the shipped pages and unit-tested; the wiring
 * (hover/focus gates, aria-describedby lifecycle, shared placePop) is checked
 * as contracts over every shipped page.
 */
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');

function extractFn(html, name, label) {
  const i = html.indexOf(`function ${name}(`);
  assert.ok(i >= 0, `${name} not found in ${label}`);
  const end = html.indexOf('\n}', i);
  assert.ok(end > i, `${name} end not found in ${label}`);
  const src = html.slice(i, end + 2);
  return new Function(`${src.replace(`function ${name}`, `return function ${name}`)};`)();
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
  const tipClamp = extractFn(html, 'tipClamp', label);

  test(`[${label}] tipClamp keeps short intros, clamps long ones at word boundary`, () => {
    assert.equal(tipClamp('Короткое интро', 220), 'Короткое интро');
    assert.equal(tipClamp('', 220), '');
    assert.equal(tipClamp(null, 220), '');
    const long = 'слово '.repeat(100).trim();
    const out = tipClamp(long, 220);
    assert.ok(out.length <= 221, `clamped length ${out.length}`);
    assert.ok(out.endsWith('…'));
    assert.ok(!out.includes('  ')); // cut at a word boundary, no dangling spaces
  });

  test(`[${label}] sidebar summary tooltip wiring`, () => {
    assert.ok(html.includes('function showSecTip('), 'showSecTip');
    assert.ok(html.includes('function placePop('), 'shared placer');
    assert.ok(html.includes('showTerm(ab);\n  placePop(ab);') || /showTerm[\s\S]{0,200}placePop\(ab\)/.test(html), 'showTerm uses placer');
    assert.ok(html.includes('placePop(btn, true)'), 'sidebar tip opens to the right of the link');
    assert.ok(html.includes("(hover: hover) and (pointer: fine)"), 'hover-capability gate');
    assert.ok(html.includes("btn.addEventListener('pointerenter'"), 'hover show');
    assert.ok(html.includes("btn.addEventListener('focus'"), 'keyboard show');
    assert.ok(html.includes("btn.addEventListener('pointerleave', hidePop)"), 'hide on leave');
    assert.ok(html.includes("btn.setAttribute('aria-describedby', 'pop')"), 'a11y describedby');
    assert.ok(html.includes("hidePop();\n  document.querySelectorAll('[aria-describedby=\"pop\"]')".replace('\n  ', '\n')) || html.includes("removeAttribute('aria-describedby')"), 'describedby cleanup');
    assert.ok(html.includes('tipClamp(s.intro, 220)'), 'intro clamped');
  });
}
