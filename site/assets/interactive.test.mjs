/**
 * Contract tests for interactive.js — no DOM/browser required.
 * Catches the window.CARDS / host-gate wiring bugs that string-guards also cover.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');
const JS = readFileSync(join(ROOT, 'site/assets/interactive.js'), 'utf8');
const INDEX = readFileSync(join(ROOT, 'site/index.html'), 'utf8');

test('index exposes window.CARDS before htlb:ready', () => {
  assert.match(
    INDEX,
    /window\.CARDS\s*=\s*CARDS\s*;\s*try\s*\{\s*dispatchEvent\(\s*new Event\('htlb:ready'\)/,
  );
});

test('enhanceCards uses window.CARDS local, not bare CARDS', () => {
  assert.match(JS, /function enhanceCards\(\)\s*\{\s*var cards = window\.CARDS;/);
  assert.equal(/!window\.CARDS\s*\|\|\s*!CARDS\.length/.test(JS), false);
});

test('host gate allows book.dlgrv.com and local preview', () => {
  assert.match(JS, /h === 'book\.dlgrv\.com'/);
  assert.match(JS, /h === '127\.0\.0\.1'/);
  assert.match(JS, /h === 'localhost'/);
});

test('off-host stub hides account and rejects api', () => {
  assert.match(JS, /acc\.hidden = true/);
  assert.match(JS, /interactive disabled/);
});

test('useful toggle posts to /useful', () => {
  assert.match(JS, /api\('\/useful',\s*\{\s*method:\s*'POST'/);
});

test('Useful button is placed after Sources, not under title', () => {
  assert.match(JS, /details\.src/);
  assert.match(JS, /htlb-useful/);
  assert.equal(/insertBefore\(bar,\s*title\.nextSibling\)/.test(JS), false);
});

