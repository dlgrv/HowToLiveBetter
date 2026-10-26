/**
 * Tests for the Anki .apkg builder (forge/ebook/anki/build.mjs).
 */
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, test } from 'node:test';

import { buildAnki, guidFor, itemFields, zipStore } from './build.mjs';

const TMP = mkdtempSync(join(tmpdir(), 'htlb-anki-'));
after(() => rmSync(TMP, { recursive: true, force: true }));

test('itemFields maps labels from every locale', () => {
  const ru = itemFields(['- Стоимость: 0 рублей', '- Простыми словами: просто', '- Уровень доказательности: A']);
  assert.deepEqual(ru, { plain: 'просто', cost: '0 рублей', gain: '', grade: 'A', notes: '' });

  const zh = itemFields(['- 成本： 免费', '- 说人话： 很简单', '- 收益： 很大', '- 证据等级： B', '- 备注： 注意']);
  assert.equal(zh.plain, '很简单');
  assert.equal(zh.gain, '很大');
  assert.equal(zh.grade, 'B');
  assert.equal(zh.notes, '注意');

  const es = itemFields(['- Costo: nada', '- En términos sencillos: fácil', '- Nivel de evidencia: C']);
  assert.equal(es.cost, 'nada');
  assert.equal(es.grade, 'C');

  // First value wins; unknown labels ignored.
  const dup = itemFields(['- Cost: first', '- Cost: second', '- Whatever: x']);
  assert.equal(dup.cost, 'first');
  assert.equal(dup.plain, '');
});

test('guidFor is stable and distinct per lang/entry', () => {
  assert.equal(guidFor('en', '1-1'), guidFor('en', '1-1'));
  assert.notEqual(guidFor('en', '1-1'), guidFor('ru', '1-1'));
  assert.notEqual(guidFor('en', '1-1'), guidFor('en', '1-2'));
  assert.match(guidFor('en', '1-1'), /^[0-9a-f]{20}$/);
});

test('zipStore produces a valid stored zip', () => {
  const buf = zipStore([{ name: 'media', data: '{}' }]);
  assert.equal(buf[0], 0x50);
  assert.equal(buf[1], 0x4b); // PK
  assert.equal(buf[2], 3);
  assert.equal(buf[3], 4); // local file header
  assert.ok(buf.subarray(-22, -18).equals(Buffer.from([0x50, 0x4b, 5, 6])), 'EOCD');
  assert.ok(buf.includes(Buffer.from('media')));
});

test('buildAnki(en): real deck stats and signature', async () => {
  const out = join(TMP, 'HowToLiveBetter-en.apkg');
  const stats = await buildAnki('en', out);
  const buf = readFileSync(out);
  assert.ok(stats.notes >= 700, `notes ${stats.notes}`);
  assert.equal(stats.chapters, 34);
  assert.equal(buf[0], 0x50);
  assert.ok(stats.bytes > 500_000, `size ${stats.bytes}`);
});
