import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ensureH1, fitTypstTableColumns, headingText, isChapterPath, localeFor, navLabel, prepareSection, promoteItemHeadings, read, readBook, requireRepoFile, stripBackLink } from './book.mjs';

const EXPECTED_CHAPTERS = 34;

test('stripBackLink drops known first-page back links', () => {
  const cases = [
    ['[← 回总目录](../README.md)\n\n# T\n', '# T\n'],
    ['\n\n[← Voltar ao índice](../../README.pt.md)\n# T\n', '# T\n'],
    ['[← Volver al índice](../../README.es.md)\n# T\n', '# T\n'],
    ['[← К оглавлению](../../README.ru.md)\n# T\n', '# T\n'],
    ['[← Back to contents](../../README.md)\n# T\n', '# T\n'],
    ['Backlink: [← Return to main index](../../README.md)\n# T\n', '# T\n'],
    ['# T\n\nbody\n', '# T\n\nbody\n'],
  ];
  for (const [input, expected] of cases) {
    assert.equal(stripBackLink(input), expected);
  }
});

test('promoteItemHeadings lifts chapter items and leaves real sections', () => {
  const chapter = '# 1. Title\n\n### 1. Do the thing\n\n## 许可\n\nfooter\n';
  assert.match(promoteItemHeadings(chapter), /## 1\. Do the thing/);
  assert.match(promoteItemHeadings(chapter), /## 许可/);
  const longRead = '# Title\n\n## Section\n\n### Detail\n\n#### Note\n';
  assert.equal(promoteItemHeadings(longRead), longRead);
  const fenced = '# Title\n\n```\n### not a heading\n```\n\n### Real item\n';
  const promoted = promoteItemHeadings(fenced);
  assert.match(promoted, /```\n### not a heading\n```/);
  assert.match(promoted, /## Real item/);
});

test('prepareSection strips a labeled back link then promotes items', () => {
  const md = 'Backlink: [← Return to main index](../../README.md)\n\n# 14. Accounts\n\n### 1. Enable 2FA\n';
  const out = prepareSection(md);
  assert.equal(out.includes('Backlink'), false);
  assert.match(out, /^# 14\. Accounts/);
  assert.match(out, /## 1\. Enable 2FA/);
});

test('nav labels decode entities before escaping', () => {
  assert.equal(headingText('The platform&#39;s own'), "The platform's own");
  assert.equal(navLabel('The platform&#39;s own'), "The platform's own");
  assert.equal(navLabel('A &amp; B'), 'A &amp; B');
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

test('ebook links are underlined and tables stay on the page', () => {
  const css = read('forge/ebook/epub/style.css');
  assert.match(css, /a \{[^}]*text-decoration:\s*underline/);
  assert.match(css, /table \{[^}]*table-layout:\s*fixed/);
  assert.match(css, /th, td \{[^}]*overflow-wrap:\s*anywhere/);
  const typ = read('forge/ebook/pdf/template.typ');
  assert.match(typ, /#set table\([\s\S]*stroke:\s*0\.4pt/);
  assert.equal(typ.includes('stroke: none'), false);
  assert.match(typ, /#show link: it => underline\(/);
  const src = '#table(\n    columns: 5,\n    align: (auto,auto,),\n  )\n#grid(columns: (1fr, auto), a, b)';
  const fitted = fitTypstTableColumns(src);
  assert.match(fitted, /columns: 5 \* \(1fr,\),/);
  assert.match(fitted, /columns: \(1fr, auto\)/);
});

test('missing chapter file fails', () => {
  assert.throws(() => requireRepoFile('book/99-missing.md'), /missing book\/99-missing\.md/);
  assert.throws(() => readBook('nope'), /unknown --lang/);
});
