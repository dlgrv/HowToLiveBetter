// Shared README parsing for EPUB and PDF. File lists come from the README
// table of contents, not a hand-maintained manifest.
import { existsSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const REPO = 'https://github.com/dlgrv/HowToLiveBetter';
export const SITE_BASE = 'https://dlgrv.github.io/HowToLiveBetter';
export const RELEASE_TAG = 'ebooks-latest';

const LOCALE = {
  en: {
    markers: {
      front: '## Questions',
      toc: '## Table of contents',
      book: '## The book itself',
    },
    title: 'HowToLiveBetter',
    typstLang: 'en',
    typstRegion: 'US',
    labels: {
      front: 'Preface',
      contents: 'Section guide',
      about: 'About this edition',
      toc: 'Contents',
      cover: 'Cover',
      body: 'Text',
    },
  },
  ru: {
    markers: {
      front: '## Вопросы',
      toc: '## Оглавление',
      book: '## Текст книги',
    },
    title: 'HowToLiveBetter',
    typstLang: 'ru',
    typstRegion: 'RU',
    labels: {
      front: 'Предисловие',
      contents: 'Оглавление',
      about: 'Об этом издании',
      toc: 'Содержание',
      cover: 'Обложка',
      body: 'Текст',
    },
  },
  zh: {
    markers: {
      front: '## 这本书想回答的问题',
      toc: '## 目录',
      book: '## 正文',
    },
    title: '高性价比人生指南',
    typstLang: 'zh',
    typstRegion: 'CN',
    labels: {
      front: '前言',
      contents: '各节简介',
      about: '版本说明',
      toc: '目录',
      cover: '封面',
      body: '正文',
    },
  },
  es: {
    // README.es.md reuses the English section headings.
    markers: {
      front: '## Questions',
      toc: '## Table of contents',
      book: '## The book itself',
    },
    title: 'HowToLiveBetter',
    typstLang: 'es',
    typstRegion: 'MX',
    labels: {
      front: 'Prefacio',
      contents: 'Guía de secciones',
      about: 'Sobre esta edición',
      toc: 'Contenido',
      cover: 'Portada',
      body: 'Texto',
    },
  },
  pt: {
    markers: {
      front: '## Perguntas',
      toc: '## Índice',
      book: '## O livro em si',
    },
    title: 'HowToLiveBetter',
    typstLang: 'pt',
    typstRegion: 'BR',
    labels: {
      front: 'Prefácio',
      contents: 'Guia das seções',
      about: 'Sobre esta edição',
      toc: 'Sumário',
      cover: 'Capa',
      body: 'Texto',
    },
  },
  ar: {
    markers: {
      front: '## الأسئلة التي يحاول هذا الكتاب الإجابة عنها',
      toc: '## جدول المحتويات',
      book: '## الكتاب نفسه',
    },
    title: 'HowToLiveBetter',
    typstLang: 'ar',
    typstRegion: 'SA',
    labels: {
      front: 'مقدمة',
      contents: 'دليل الأقسام',
      about: 'عن هذه النسخة',
      toc: 'المحتويات',
      cover: 'الغلاف',
      body: 'النص',
    },
  },
};

export const read = (rel) => readFileSync(resolveRepoFile(rel), 'utf8').replace(/\r\n/g, '\n');

export const unique = (arr) => [...new Set(arr)];

export function loadLangs() {
  const raw = JSON.parse(read('translate/langs.json'));
  return raw.languages.map((row) => {
    const extra = LOCALE[row.code];
    if (!extra) throw new Error(`no ebook locale table for ${row.code}`);
    return {
      ...row,
      ...extra,
      site: `${SITE_BASE}/${row.code}/`,
      release: `${REPO}/releases/download/${RELEASE_TAG}/HowToLiveBetter-${row.code}`,
      dcLanguage: row.inLanguage,
    };
  });
}

export function localeFor(code) {
  const found = loadLangs().find((row) => row.code === code);
  if (!found) throw new Error(`unknown --lang ${code} (see translate/langs.json)`);
  return found;
}

export function parseLang(argv = process.argv.slice(2)) {
  const i = argv.indexOf('--lang');
  if (i < 0 || !argv[i + 1]) throw new Error('usage: --lang en|ru|zh|es|pt|ar');
  return argv[i + 1];
}

export function gitCommit() {
  try {
    return execSync('git rev-parse HEAD', { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return process.env.GITHUB_SHA ?? '';
  }
}

export function buildStamp() {
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai',
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date());
}

export function ensureH1(md) {
  if (/^# /m.test(md)) return md;
  if (!/^## /m.test(md)) throw new Error('document has no heading to promote');
  return md.replace(/^## /m, '# ');
}

const BACK_LINK_LINE = /^(?:[^\n\[]{0,40}?\s*)?\[←[^\]]*\]\([^)]*\)\s*$/;

export function stripBackLink(md) {
  const lines = md.split('\n');
  const out = lines.filter((line, i) => i >= 8 || !BACK_LINK_LINE.test(line));
  return out.join('\n').replace(/^\n+/, '');
}

function fenceMark(line) {
  const match = line.match(/^(`{3,}|~{3,})(.*)$/);
  if (!match) return null;
  return { char: match[1][0], rest: match[2].trim() };
}

// Locale source_label values from translate/rules/*.json — ebook drops these
// full citation bullets; Evidence grade and Notes stay.
const SOURCE_LINE =
  /^- (?:来源|Sources|Источники|Fuentes|Fontes|المصادر)\s*[：:].*$/;

export function stripSourceLines(md) {
  const lines = md.split('\n');
  let fence = '';
  const kept = [];
  for (const line of lines) {
    const mark = fenceMark(line);
    if (mark) {
      if (!fence) fence = mark.char;
      else if (mark.char === fence && mark.rest === '') fence = '';
      kept.push(line);
      continue;
    }
    if (!fence && SOURCE_LINE.test(line)) continue;
    kept.push(line);
  }
  return kept.join('\n').replace(/\n{3,}/g, '\n\n');
}

// Body field labels from translate/rules/*/labels (not source_label).
const FIELD_LABELS = [
  '成本',
  '说人话',
  '收益',
  '证据等级',
  '备注',
  'Cost',
  'In plain terms',
  'Benefit',
  'Evidence grade',
  'Notes',
  'Стоимость',
  'Простыми словами',
  'Эффект',
  'Уровень доказательности',
  'Примечания',
  'Costo',
  'En términos sencillos',
  'Beneficio',
  'Nivel de evidencia',
  'Notas',
  'Custo',
  'Em linguagem simples',
  'Benefício',
  'Nível de evidência',
  'التكلفة',
  'بعبارة بسيطة',
  'الفائدة',
  'مستوى الدليل',
  'ملاحظات',
].sort((a, b) => b.length - a.length);

const FIELD_LINE = new RegExp(
  `^- (${FIELD_LABELS.map((l) => l.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\s*[：:]\\s*(.*)$`,
);

function parseFieldLine(line) {
  const m = FIELD_LINE.exec(line);
  if (!m) return null;
  return { label: m[1], value: m[2] };
}

function renderFieldBlock(fields, kind) {
  if (kind === 'html') {
    const body = fields
      .map(
        ({ label, value }) =>
          `<dt>${xmlEscape(label)}</dt>\n<dd>${xmlEscape(value)}</dd>`,
      )
      .join('\n');
    return `<dl class="entry">\n${body}\n</dl>`;
  }
  return fields.map(({ label, value }) => `${label}\n: ${value}`).join('\n\n');
}

// Turn consecutive entry-field bullets into a description list (EPUB HTML or
// pandoc definition list for PDF). Leaves ordinary bullets and fences alone.
export function formatEntryFields(md, kind = 'deflist') {
  if (kind !== 'html' && kind !== 'deflist') {
    throw new Error(`formatEntryFields: unknown kind ${kind}`);
  }
  const lines = md.split('\n');
  let fence = '';
  const out = [];
  let pending = [];

  const flush = () => {
    if (pending.length === 0) return;
    if (out.length > 0 && out[out.length - 1] !== '') out.push('');
    out.push(renderFieldBlock(pending, kind));
    out.push('');
    pending = [];
  };

  for (const line of lines) {
    const mark = fenceMark(line);
    if (mark) {
      flush();
      if (!fence) fence = mark.char;
      else if (mark.char === fence && mark.rest === '') fence = '';
      out.push(line);
      continue;
    }
    if (!fence) {
      const field = parseFieldLine(line);
      if (field) {
        pending.push(field);
        continue;
      }
    }
    flush();
    out.push(line);
  }
  flush();
  return out.join('\n').replace(/\n{3,}/g, '\n\n');
}

// Item titles in chapters are ### under a lone H1. Lift those to ## so the
// outline does not skip a level. Stop at the first real ## (license footers
// in a few translations) and leave fenced examples alone.
export function promoteItemHeadings(md) {
  const lines = md.split('\n');
  let fence = '';
  let firstH2 = -1;
  for (let i = 0; i < lines.length; i++) {
    const mark = fenceMark(lines[i]);
    if (mark) {
      if (!fence) fence = mark.char;
      else if (mark.char === fence && mark.rest === '') fence = '';
      continue;
    }
    if (!fence && /^## /.test(lines[i])) {
      firstH2 = i;
      break;
    }
  }
  fence = '';
  return lines
    .map((line, i) => {
      const mark = fenceMark(line);
      if (mark) {
        if (!fence) fence = mark.char;
        else if (mark.char === fence && mark.rest === '') fence = '';
        return line;
      }
      if (fence) return line;
      if ((firstH2 < 0 || i < firstH2) && line.startsWith('### ')) return `## ${line.slice(4)}`;
      return line;
    })
    .join('\n');
}

export function prepareSection(md, kind = 'deflist') {
  return promoteItemHeadings(
    ensureH1(formatEntryFields(stripSourceLines(stripBackLink(md)), kind)),
  );
}

// Pandoc emits equal columns (`2` / `3` or `(50%, 50%)`). Bias known shapes so
// short label columns shrink to (at least) their header width and long text grows.
const QUESTION_HEADERS = new Set([
  'вопрос',
  'question',
  'pregunta',
  'pergunta',
  '问题',
  'السؤال',
]);
const WHERE_HEADERS = /посмотр|where to look|d[oó]nde|onde (ver|olhar)|在哪|去哪看|أين تنظر/i;
// Evidence grade: body is A/B/C — size to header only (RU «Уровень» is the widest).
const GRADE_HEADERS = new Set([
  'уровень',
  'grade',
  'grau',
  'nivel',
  'nível',
  'level',
  '等级',
  '证据等级',
  'الدرجة',
]);
const TERM_HEADERS = new Set([
  'термин',
  'term',
  'término',
  'termo',
  '术语',
  'المصطلح',
]);
const DIMENSION_HEADERS = new Set([
  'измерение',
  'dimension',
  'dimensión',
  'dimensão',
  '维度',
  'البعد',
]);
const HOW_SET_HEADERS =
  /как определяется|how it is set|cómo se (define|fija)|como (é|e) definido|怎么定|كيف يحدد/i;

function plainTypstCell(cell) {
  return String(cell ?? '')
    .replace(/#link\([^]]*\[([^\]]*)\]\)/g, '$1')
    .replace(/\[([^\]]*)\]/g, '$1')
    .replace(/[#*]/g, '')
    .trim();
}

function parseTypstHeaderCells(headerArgs) {
  return [...String(headerArgs).matchAll(/\[([^\]]*)\]/g)].map((m) => m[1]);
}

/** @returns {string[] | null} */
export function tableColumnFr(headers) {
  const plain = headers.map((h) => plainTypstCell(h));
  const left = (plain[0] ?? '').toLowerCase();
  if (headers.length === 2) {
    const right = plain[1] ?? '';
    if (QUESTION_HEADERS.has(left) || WHERE_HEADERS.test(right)) {
      // RU p90 "where" ≈154pt + chrome → ~36% → 1.8:1
      return ['1.8fr', '1fr'];
    }
    if (GRADE_HEADERS.has(left)) {
      // Header-limited (~50pt for «Уровень»); body is a single letter.
      return ['1fr', '7fr'];
    }
    if (TERM_HEADERS.has(left)) {
      return ['1fr', '2.5fr'];
    }
    return null;
  }
  if (headers.length === 3) {
    const right = plain[2] ?? '';
    if (DIMENSION_HEADERS.has(left) || HOW_SET_HEADERS.test(right)) {
      // Label / short values / long definition → ~22% / 24% / 54%
      return ['1.1fr', '1.2fr', '2.7fr'];
    }
  }
  return null;
}

/** @deprecated use tableColumnFr */
export function twoColumnTableFr(headerLeft, headerRight) {
  const fr = tableColumnFr([headerLeft, headerRight]);
  return fr ? /** @type {[string, string]} */ ([fr[0], fr[1]]) : null;
}

export function fitTypstTableColumns(typ) {
  let out = typ.replace(/columns:\s*(\d+),/g, (_, n) => `columns: ${n} * (1fr,),`);

  // Pandoc sometimes emits equal percentages instead of a count.
  out = out.replace(
    /columns:\s*\(\s*([\d.]+%\s*,\s*)+[\d.]+%\s*\),(\s*align:\s*\([^)]*\),\s*table\.header\(((?:\[[^\]]*\](?:,\s*)?)+)\))/g,
    (all, _pcts, rest, headerArgs) => {
      const headers = parseTypstHeaderCells(headerArgs);
      const fr = tableColumnFr(headers);
      if (!fr || fr.length !== headers.length) return all;
      return `columns: (${fr.join(', ')}),${rest}`;
    },
  );

  // After the numeric → equal-fr rewrite: bias by header texts.
  out = out.replace(
    /columns:\s*(\d+) \* \(1fr,\),(\s*align:\s*\([^)]*\),\s*table\.header\(((?:\[[^\]]*\](?:,\s*)?)+)\))/g,
    (all, n, rest, headerArgs) => {
      const headers = parseTypstHeaderCells(headerArgs);
      if (headers.length !== Number(n)) return all;
      const fr = tableColumnFr(headers);
      if (!fr || fr.length !== headers.length) return all;
      return `columns: (${fr.join(', ')}),${rest}`;
    },
  );
  return out;
}

function frToWidthPercents(frs) {
  const nums = frs.map((f) => Number.parseFloat(f));
  const sum = nums.reduce((a, b) => a + b, 0);
  return nums.map((n) => `${((100 * n) / sum).toFixed(1)}%`);
}

/** Insert <colgroup> widths for known front-matter table shapes (EPUB). */
export function fitEpubTableColumns(html) {
  return String(html).replace(/<table>(\s*<thead>\s*<tr>\s*)((?:<th>[^<]*<\/th>\s*)+)(<\/tr>)/g, (all, pre, ths, post) => {
    const headers = [...ths.matchAll(/<th>([^<]*)<\/th>/g)].map((m) => m[1]);
    const fr = tableColumnFr(headers);
    if (!fr || fr.length !== headers.length) return all;
    const cols = frToWidthPercents(fr)
      .map((w) => `<col style="width:${w}"/>`)
      .join('');
    return `<table>\n<colgroup>${cols}</colgroup>${pre}${ths}${post}`;
  });
}

const NAMED_ENTITIES = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
};

export function decodeEntities(text) {
  return text.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-z]+);/g, (all, body) => {
    if (body[0] !== '#') return NAMED_ENTITIES[body] ?? all;
    const code = body[1] === 'x' ? Number.parseInt(body.slice(2), 16) : Number(body.slice(1));
    if (!Number.isInteger(code) || code < 0 || code > 0x10ffff) return all;
    return String.fromCodePoint(code);
  });
}

export function xmlEscape(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// marked html renderer policy for EPUB: keep entry <dl> blocks we inject,
// drop HTML comments (cost tags) and any other raw HTML.
export function renderEpubHtmlToken(text) {
  const t = String(text ?? '').trim();
  if (!t) return '';
  if (t.startsWith('<!--')) return '';
  if (/^<dl\b[^>]*\bclass=(["'])entry\1/i.test(t)) return text;
  return '';
}

export function headingText(html) {
  return decodeEntities(html.replace(/<[^>]+>/g, ''));
}

export function navLabel(html) {
  return xmlEscape(headingText(html));
}

export function isChapterPath(rel, contentRoot) {
  const prefix = contentRoot.endsWith('/') ? contentRoot : `${contentRoot}/`;
  if (!rel.startsWith(prefix)) return false;
  return /^[0-9]{2}-[^/]+\.md$/.test(rel.slice(prefix.length));
}

export function isLongRead(rel, code) {
  if (!rel.endsWith('.md')) return false;
  if (rel.includes('核实记录')) return false;
  if (rel.startsWith('docs/pipeline/')) return false;
  if (code === 'zh') {
    if (/^docs\/research\/(en|ru|es|pt|ar)\//.test(rel)) return false;
    return /^docs\/[^/]+\.md$/.test(rel) || /^docs\/research\/[^/]+\.md$/.test(rel);
  }
  const prefix = `docs/research/${code}/`;
  return rel.startsWith(prefix) && !rel.slice(prefix.length).includes('/');
}

export function coverRel(code) {
  const local = `site/assets/og/${code}.png`;
  if (existsSync(resolve(ROOT, local))) return local;
  if (existsSync(resolve(ROOT, 'og.png'))) return 'og.png';
  throw new Error(`no cover image for ${code}`);
}

export function readBook(code) {
  const locale = localeFor(code);
  const readme = read(locale.readme);
  const lines = readme.split('\n');
  const between = (from, to) => {
    const a = lines.findIndex((l) => l.startsWith(from));
    const b = lines.findIndex((l, i) => i > a && l.startsWith(to));
    if (a < 0 || b < 0) throw new Error(`${locale.readme}: missing section ${from} → ${to}`);
    return lines.slice(a, b).join('\n');
  };
  const { markers } = locale;
  const description = descriptionFrom(lines);
  const frontMd = between(markers.front, markers.toc);
  const contentsMd = between(markers.toc, markers.book)
    .split('\n\n')
    .filter((p) => !p.includes('index.html'))
    .join('\n\n');
  const bookLinks = unique([...contentsMd.matchAll(/\]\((book\/[^)#]+\.md)\)/g)].map((m) => m[1]));
  const bookFiles = [];
  for (const rel of bookLinks) {
    if (!isChapterPath(rel, locale.contentRoot)) {
      throw new Error(`${locale.readme}: TOC link is not a ${code} chapter: ${rel}`);
    }
    resolveRepoFile(rel);
    bookFiles.push(rel);
  }
  if (bookFiles.length === 0) throw new Error(`${locale.readme}: TOC has no chapters`);
  const docLinks = unique([...readme.matchAll(/\]\((docs\/[^)#]+\.md)\)/g)].map((m) => m[1]));
  const docFiles = [];
  for (const rel of docLinks) {
    if (!isLongRead(rel, code)) continue;
    resolveRepoFile(rel);
    docFiles.push(rel);
  }
  if (docFiles.length === 0) throw new Error(`${locale.readme}: no long reads`);
  return { locale, readme, description, frontMd, contentsMd, bookFiles, docFiles };
}

export function aboutMd(locale, stamp, commit) {
  const short = commit ? commit.slice(0, 7) : '';
  const commitLine = short ? `- Commit: [${short}](${REPO}/commit/${commit})\n` : '';
  const epub = `${locale.release}.epub`;
  const pdf = `${locale.release}.pdf`;
  return `# ${locale.labels.about}

This file is generated from the Markdown in the repository.

- Built: ${stamp} (Asia/Shanghai)
${commitLine}- EPUB: ${epub}
- PDF: ${pdf}
- Site: ${locale.site}
- Repository: ${REPO}

Links to other chapters in this book jump inside the file. Links to files that are not part of the book point at GitHub.

Full source citations are on the website, not in this ebook.

The text is in the public domain under the Unlicense.`;
}

function descriptionFrom(lines) {
  const h = lines.findIndex((l) => /^# /.test(l));
  if (h < 0) throw new Error('README has no H1');
  const paras = [];
  for (const line of lines.slice(h + 1)) {
    if (/^#{1,6} /.test(line)) break;
    if (/^!\[/.test(line) || /^\[!\[/.test(line) || line.trim() === '---') break;
    const plain = line.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    if (!plain || plain.startsWith('<')) continue;
    paras.push(plain);
    if (paras.length >= 2) break;
  }
  if (paras.length === 0) throw new Error('README description is empty');
  return paras.join(' ');
}

export function requireRepoFile(rel) {
  return resolveRepoFile(rel);
}

function resolveRepoFile(rel) {
  for (const form of [rel, rel.normalize('NFC'), rel.normalize('NFD')]) {
    const abs = resolve(ROOT, form);
    if (existsSync(abs)) return abs;
  }
  throw new Error(`missing ${rel}`);
}
