/**
 * Logic tests for the "unverified" (todo) flag regex in the inline parser.
 *
 * The parser lives inline in site/index.html and is copied by build_pages.py
 * into every site/<lang>/index.html. The bug this guards against: a
 * case-insensitive /TODO/ also matches the Spanish/Portuguese word
 * "todo/todos" ("all"), flagging hundreds of es/pt entries as unverified.
 *
 * The test extracts the shipped regex from the actual HTML sources and runs
 * it against field samples, so it fails if anyone regresses the source or
 * forgets to rebuild locales.
 */
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');

/** Extract the e.todo regex literal from an index.html and compile it. */
function todoRegex(html, label) {
  const m = /e\.todo\s*=\s*(\/.*?\/[a-z]*)\s*\.\s*test/.exec(html);
  assert.ok(m, `e.todo regex not found in ${label}`);
  return new Function(`return ${m[1]};`)();
}

/** Extract the e.dispute ternary chain and compile it into note -> boolean. */
function disputePredicate(html, label) {
  const i = html.indexOf('e.dispute =');
  assert.ok(i >= 0, `e.dispute chain not found in ${label}`);
  const stmt = html.slice(i + 'e.dispute ='.length, html.indexOf(';', i));
  return new Function('LANG', 'note', `var e = { note: note }; return ${stmt};`);
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
  const re = todoRegex(html, label);
  const disputeOf = disputePredicate(html, label);

  test(`[${label}] todo flag ignores Spanish/Portuguese "todo/todos"`, () => {
    assert.equal(re.test('Fontes: dado de 2025, vale em todo o país'), false);
    assert.equal(re.test('Fuentes: registros de todo el país (828 casos)'), false);
    assert.equal(re.test('Notas: todos los puntos se calculan por mortalidad'), false);
    assert.equal(re.test('Notas: nem todo ferimento requer a vacina'), false);
  });

  test(`[${label}] todo flag catches real unverified markers`, () => {
    assert.equal(re.test('Notas: TODO (a verificar: não se encontrou o documento)'), true);
    assert.equal(re.test('Notas: …没核到原文（TODO：待核实）'), true);
    assert.equal(re.test('备注：联合调查组只说将及时公布。TODO（待核实：结论）'), true);
    assert.equal(re.test('Notes: "will be announced in due course." TODO (to be verified)'), true);
  });

  test(`[${label}] todo flag is case-sensitive for TODO and phrase-matched for "to be verified"`, () => {
    assert.equal(re.test('Notes: To be verified by the ministry'), true);
    assert.equal(re.test('Notes: todoing the checklist tomorrow'), false);
    assert.equal(re.test('Notes: a methodology, not a TODOing list'), false);
  });

  // The dispute chain is multi-language at runtime (LANG comes from the URL
  // or the browser), so every page must handle every language's markers.
  const disputeMarks = [
    ['zh', '争议：报警器那一半有反方数据'],
    ['en', 'Contested. The cost of staying up late'],
    ['en', 'Disputed. Results differ widely'],
    ['en', 'Controversy: Rogelberg’s 2006 research'],
    ['en', 'Controversial. A 2017 US study found'],
    ['ru', 'Спорно. Авторы сами сообщили'],
    ['ru', 'Спорный момент: одна статья перепроверила этот вывод'],
    ['es', 'En disputa: las mujeres del WHI'],
    ['es', 'Controversia. Los propios autores informan'],
    ['pt', 'Em disputa: o parecer de 2022'],
    ['pt', 'Controverso. Quase todos esses estudos'],
    ['ar', 'متنازع عليه. وجدت دراسة'],
    ['ar', 'خلاف. هذه الدراسات تقريبا'],
    ['id', 'Kontroversial. Biaya begadang'],
    ['id', 'Kontroversial: obat mana yang'],
  ];
  const plainNotes = [
    ['zh', '受益人主要是你自己和家人'],
    ['en', 'The 2017 analysis split by hours of use'],
    ['ru', 'Уровень доказательности: B'],
    ['es', 'Los estudios no dan una cifra de todo esto'],
    ['pt', 'Os dados de todo o país abrangem quatro países'],
    ['ar', 'الفائدة الأساسية تعود عليك'],
    ['id', 'Penelitian ini melibatkan 100 pasien'],
  ];

  test(`[${label}] dispute flag catches all marker variants of 争议 in every LANG`, () => {
    for (const [lang, note] of disputeMarks) {
      assert.equal(disputeOf(lang, note), true, `LANG=${lang}: ${note}`);
    }
  });

  test(`[${label}] dispute flag ignores ordinary notes in every LANG`, () => {
    for (const [lang, note] of plainNotes) {
      assert.equal(disputeOf(lang, note), false, `LANG=${lang}: ${note}`);
    }
  });
}
