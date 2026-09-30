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
  if (i < 0 || !argv[i + 1]) throw new Error('usage: --lang en|ru|zh|es|pt');
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

export function stripBackLink(md) {
  const lines = md.split('\n');
  const out = lines.filter((line, i) => i >= 8 || !/^\[←[^\]]*\]\([^)]*\)\s*$/.test(line));
  return out.join('\n').replace(/^\n+/, '');
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
    if (/^docs\/research\/(en|ru|es|pt)\//.test(rel)) return false;
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
