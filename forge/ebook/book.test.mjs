import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ensureH1, isChapterPath, localeFor, readBook, requireRepoFile, stripBackLink } from './book.mjs';

const EXPECTED_CHAPTERS = 34;

test('stripBackLink drops known first-page back links', () => {
  const cases = [
    ['[← 回总目录](../README.md)\n\n# T\n', '# T\n'],
    ['\n\n[← Voltar ao índice](../../README.pt.md)\n# T\n', '# T\n'],
    ['[← Volver al índice](../../README.es.md)\n# T\n', '# T\n'],
    ['[← К оглавлению](../../README.ru.md)\n# T\n', '# T\n'],
    ['[← Back to contents](../../README.md)\n# T\n', '# T\n'],
    ['# T\n\nbody\n', '# T\n\nbody\n'],
  ];
  for (const [input, expected] of cases) {
    assert.equal(stripBackLink(input), expected);
  }
});

test('ensureH1 promotes a leading section heading', () => {
  const md = '> note\n\n## Title\n\nbody\n';
  assert.match(ensureH1(md), /^> note\n\n# Title\n/);
  assert.equal(ensureH1('# Already\n'), '# Already\n');
});

test('zh chapters stay in book/NN-*.md', () => {
  assert.equal(isChapterPath('book/01-不要早死.md', 'book'), true);
  assert.equal(isChapterPath('book/en/01-Do-Not-Die-Early.md', 'book'), false);
  assert.equal(isChapterPath('book/ru/01-Не-умирайте-рано.md', 'book'), false);
  assert.equal(isChapterPath('book/pt/01-Como-Evitar-Uma-Morte-Prematura.md', 'book/pt'), true);
});

test('es reuses English README markers', () => {
  assert.deepEqual(localeFor('es').markers, localeFor('en').markers);
});

test('each locale TOC has 34 chapters and long reads', () => {
  for (const code of ['en', 'ru', 'zh', 'es', 'pt']) {
    const book = readBook(code);
    assert.equal(book.bookFiles.length, EXPECTED_CHAPTERS, code);
    assert.ok(book.docFiles.length > 0, code);
    assert.equal(book.locale.dcLanguage, localeFor(code).dcLanguage);
    if (code === 'zh') {
      for (const rel of book.bookFiles) {
        assert.match(rel, /^book\/\d{2}-[^/]+\.md$/);
      }
    }
  }
});

test('missing chapter file fails', () => {
  assert.throws(() => requireRepoFile('book/99-missing.md'), /missing book\/99-missing\.md/);
  assert.throws(() => readBook('nope'), /unknown --lang/);
});
