import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ensureH1, fitEpubTableColumns, fitTypstTableColumns, formatEntryFields, headingText, isChapterPath, localeFor, loadLangs, navLabel, prepareSection, promoteItemHeadings, read, readBook, renderEpubHtmlToken, requireRepoFile, stripBackLink, stripSourceLines, tableColumnFr, twoColumnTableFr, isRtl, EBOOK_IDS } from './book.mjs';

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

test('stripSourceLines drops locale source bullets and keeps other fields', () => {
  const md = [
    '### 1. Item',
    '- Cost: none',
    '- Evidence grade: A',
    '- Sources: https://doi.org/10.1000/example; https://example.org',
    '- Notes: keep me',
    '- 来源：某论文 https://doi.org/10.1000/cn',
    '- Источники:gov.cn (2026)',
    '',
  ].join('\n');
  const out = stripSourceLines(md);
  assert.equal(out.includes('Sources:'), false);
  assert.equal(out.includes('来源'), false);
  assert.equal(out.includes('Источники'), false);
  assert.match(out, /- Cost: none/);
  assert.match(out, /- Evidence grade: A/);
  assert.match(out, /- Notes: keep me/);
  assert.equal(/\n{3,}/.test(out), false);
});

test('stripSourceLines leaves fenced examples alone', () => {
  const md = '# T\n\n```\n- Sources: do not strip\n```\n\n- Sources: strip this\n- Notes: keep\n';
  const out = stripSourceLines(md);
  assert.match(out, /```\n- Sources: do not strip\n```/);
  assert.equal(out.includes('- Sources: strip this'), false);
  assert.match(out, /- Notes: keep/);
});

test('prepareSection strips sources after back link and before promote', () => {
  const md = [
    '[← Back to contents](../../README.md)',
    '',
    '# 1. Title',
    '',
    '### 1. Do the thing',
    '- Cost: none',
    '- Sources: https://doi.org/10.1000/x',
    '- Notes: ok',
    '',
  ].join('\n');
  const out = prepareSection(md);
  assert.equal(out.includes('Back to contents'), false);
  assert.equal(out.includes('Sources:'), false);
  assert.match(out, /^# 1\. Title/);
  assert.match(out, /## 1\. Do the thing/);
  assert.match(out, /^Notes\n: ok$/m);
  assert.equal(out.includes('- Notes:'), false);
});

test('formatEntryFields turns RU/EN fields into deflist and html', () => {
  const md = [
    '### 1. Item',
    '- Cost: free',
    '- In plain terms: plain text',
    '- Benefit: big',
    '- Evidence grade: A',
    '- Notes: keep notes',
    '',
    '### 2. RU',
    '- Стоимость: ноль',
    '- Простыми словами: просто',
    '- Эффект: большой',
    '- Уровень доказательности: A',
    '- Примечания: заметка',
    '',
  ].join('\n');
  const def = formatEntryFields(md, 'deflist');
  assert.match(def, /^Cost\n: free$/m);
  assert.match(def, /^In plain terms\n: plain text$/m);
  assert.match(def, /^Notes\n: keep notes$/m);
  assert.match(def, /^Стоимость\n: ноль$/m);
  assert.match(def, /^Примечания\n: заметка$/m);
  assert.equal(def.includes('- Cost:'), false);
  const html = formatEntryFields(md, 'html');
  assert.match(html, /<dl class="entry">/);
  assert.match(html, /<dt>Cost<\/dt>\n<dd>free<\/dd>/);
  assert.match(html, /<dt>Примечания<\/dt>\n<dd>заметка<\/dd>/);
  assert.equal(html.includes('- Cost:'), false);
});

test('formatEntryFields leaves ordinary bullets and fenced fields alone', () => {
  const md = [
    '# T',
    '',
    '```',
    '- Стоимость: inside fence',
    '```',
    '',
    '- Cost: real',
    '- Notes: real',
    '- Ordinary bullet stays',
    '',
  ].join('\n');
  const out = formatEntryFields(md, 'deflist');
  assert.match(out, /```\n- Стоимость: inside fence\n```/);
  assert.match(out, /^Cost\n: real$/m);
  assert.match(out, /^- Ordinary bullet stays$/m);
});

test('prepareSection html kind emits entry dl', () => {
  const md = '# 1. Title\n\n### 1. Item\n- Cost: none\n- Notes: ok\n';
  const out = prepareSection(md, 'html');
  assert.match(out, /<dl class="entry">/);
  assert.match(out, /<dt>Cost<\/dt>/);
  assert.match(out, /## 1\. Item/);
});

test('renderEpubHtmlToken keeps entry dl and drops comments', () => {
  const dl = '<dl class="entry">\n<dt>Cost</dt>\n<dd>free</dd>\n</dl>';
  assert.equal(renderEpubHtmlToken(dl), dl);
  assert.equal(renderEpubHtmlToken('<!-- 成本标签: 钱=0 -->'), '');
  assert.equal(renderEpubHtmlToken('<script>alert(1)</script>'), '');
  assert.equal(renderEpubHtmlToken('<p class="x">x</p>'), '');
});

test('pdf and epub keep field gaps above body leading', () => {
  const typ = read('forge/ebook/pdf/template.typ');
  assert.match(typ, /#let lead = 0\.65em/);
  assert.match(typ, /#let para-gap = lead \+ 6pt/);
  assert.match(typ, /#let field-gap = lead \+ 5pt/);
  assert.match(typ, /#let toc-gap = lead \+ 5pt/);
  assert.match(typ, /spacing: field-gap/);
  assert.match(typ, /spacing: para-gap/);
  assert.match(typ, /above: head-above, below: head-below/);
  const css = read('forge/ebook/epub/style.css');
  assert.match(css, /line-height:\s*1\.5/);
  assert.match(css, /p \{ margin: 0 0 0\.75em; \}/);
  assert.match(css, /dl\.entry dt \{[^}]*margin:\s*0\.85em/);
  assert.match(css, /nav#toc > ol > li \{[^}]*margin:\s*0\.55em/);
  assert.match(css, /padding-inline-start:\s*1\.4em/);
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
  for (const code of ['en', 'ru', 'zh', 'es', 'pt', 'ar']) {
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

test('two-column question tables prefer a wide question column', () => {
  assert.deepEqual(twoColumnTableFr('Вопрос', 'Где посмотреть'), ['1.8fr', '1fr']);
  assert.deepEqual(twoColumnTableFr('Question', 'Where to look'), ['1.8fr', '1fr']);
  assert.deepEqual(tableColumnFr(['السؤال', 'أين تنظر']), ['1.8fr', '1fr']);
  assert.deepEqual(tableColumnFr(['الدرجة', 'المعنى']), ['1fr', '7fr']);
  assert.deepEqual(tableColumnFr(['المصطلح', 'المعنى']), ['1fr', '2.5fr']);
  assert.deepEqual(tableColumnFr(['البعد', 'القيم', 'كيف يحدد']), ['1.1fr', '1.2fr', '2.7fr']);
  assert.deepEqual(tableColumnFr(['Уровень', 'Значение']), ['1fr', '7fr']);
  assert.deepEqual(tableColumnFr(['Термин', 'Значение']), ['1fr', '2.5fr']);
  assert.deepEqual(tableColumnFr(['Измерение', 'Значения', 'Как определяется']), [
    '1.1fr',
    '1.2fr',
    '2.7fr',
  ]);
  assert.equal(twoColumnTableFr('A', 'B'), null);
  const src = `#figure(
  align(center)[#table(
    columns: 2,
    align: (auto,auto,),
    table.header([Вопрос], [Где посмотреть],),
    table.hline(),
    [q], [a],
  )]
)`;
  const out = fitTypstTableColumns(src);
  assert.match(out, /columns: \(1\.8fr, 1fr\),/);
  const grade = fitTypstTableColumns(`columns: 2,
    align: (auto,auto,),
    table.header([Уровень], [Значение],),`);
  assert.match(grade, /columns: \(1fr, 7fr\),/);
  const dim = fitTypstTableColumns(`columns: 3,
    align: (auto,auto,auto,),
    table.header([Измерение], [Значения], [Как определяется],),`);
  assert.match(dim, /columns: \(1\.1fr, 1\.2fr, 2\.7fr\),/);
  const ar = fitTypstTableColumns(`columns: 2,
    align: (auto,auto,),
    table.header([السؤال], [أين تنظر],),`);
  assert.match(ar, /columns: \(1\.8fr, 1fr\),/);
  const epubTable = fitEpubTableColumns(`<table>
<thead>
<tr>
<th>Вопрос</th>
<th>Где посмотреть</th>
</tr>
</thead>
</table>`);
  assert.match(epubTable, /<colgroup><col style="width:64\.3%"\/><col style="width:35\.7%"\/><\/colgroup>/);
  assert.match(
    fitEpubTableColumns('<table>\n<thead>\n<tr>\n<th>Уровень</th>\n<th>Значение</th>\n</tr>'),
    /width:12\.5%.*width:87\.5%/s,
  );
});

test('missing chapter file fails', () => {
  assert.throws(() => requireRepoFile('book/99-missing.md'), /missing book\/99-missing\.md/);
  assert.throws(() => readBook('nope'), /unknown --lang/);
});

test('every locale has a unique ebook id and RTL is ar-only', () => {
  const codes = loadLangs().map((row) => row.code);
  for (const code of codes) {
    assert.match(EBOOK_IDS[code] ?? '', /^urn:uuid:[0-9a-f-]+$/, code);
  }
  assert.equal(new Set(Object.values(EBOOK_IDS)).size, Object.keys(EBOOK_IDS).length);
  assert.equal(isRtl('ar'), true);
  for (const code of codes.filter((c) => c !== 'ar')) {
    assert.equal(isRtl(code), false);
  }
});

test('PDF template carries Arabic fonts and an RTL branch', () => {
  const typ = read('forge/ebook/pdf/template.typ');
  assert.match(typ, /"Amiri", "Noto Naskh Arabic"/);
  assert.match(typ, /\$if\(rtl\)\$/);
  assert.match(typ, /align\(start, it\)/);
});
