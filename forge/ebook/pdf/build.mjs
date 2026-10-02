// Build one locale PDF via pandoc (typst writer) and typst.
// Usage: node forge/ebook/pdf/build.mjs --lang en
// Needs pandoc >= 3.1 and typst >= 0.13, or PANDOC / TYPST env paths.
import { readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { resolve, dirname, posix, basename } from 'node:path';
import { execFileSync } from 'node:child_process';
import {
  ROOT,
  REPO,
  read,
  readBook,
  gitCommit,
  buildStamp,
  prepareSection,
  stripSourceLines,
  formatEntryFields,
  fitTypstTableColumns,
  parseLang,
  aboutMd,
  coverRel,
  isRtl,
} from '../book.mjs';

const lang = parseLang();
const { locale, description, frontMd, bookFiles, docFiles } = readBook(lang);
const OUT = resolve(ROOT, `dist/HowToLiveBetter-${lang}.pdf`);
const WORK = resolve(ROOT, `dist/pdf-build-${lang}.md`);
const PANDOC = process.env.PANDOC ?? 'pandoc';
const TYPST = process.env.TYPST ?? 'typst';
const STAMP = buildStamp();
const COMMIT = gitCommit();

const anchorOf = new Map();
bookFiles.forEach((f) => anchorOf.set(f, `sec-${basename(f).match(/^\d+/)?.[0] ?? anchorOf.size + 1}`));
docFiles.forEach((f, i) => anchorOf.set(f, `doc-${i + 1}`));

const pages = [
  {
    src: locale.readme,
    md: `# ${locale.labels.front}\n\n${description}\n\n${formatEntryFields(stripSourceLines(frontMd), 'deflist')}`,
    anchor: 'front',
  },
  ...[...bookFiles, ...docFiles].map((src) => ({
    src,
    md: prepareSection(read(src), 'deflist'),
    anchor: anchorOf.get(src),
  })),
  { src: locale.readme, md: aboutMd(locale, STAMP, COMMIT), anchor: 'about' },
];

function rewriteLinks(md, src) {
  return md.replace(/\]\(([^)\s]+)(\s+"[^"]*")?\)/g, (all, href, title) => {
    if (/^(https?:|mailto:)/.test(href)) return all;
    if (href.startsWith('#')) return `](${REPO}/blob/main/${locale.readme}${href}${title ?? ''})`;
    const [path] = href.split('#');
    const target = posix.normalize(posix.join(posix.dirname(src), path));
    const anchor = anchorOf.get(target);
    if (anchor) return `](#${anchor}${title ?? ''})`;
    const kind = target.endsWith('/') ? 'tree' : 'blob';
    return `](${REPO}/${kind}/main/${target}${title ?? ''})`;
  });
}

const body = pages
  .map((p) => {
    const md = rewriteLinks(p.md, p.src)
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/^(# .+?)\s*$/m, `$1 {#${p.anchor}}`);
    if (!md.includes(`{#${p.anchor}}`)) throw new Error(`${p.src}: no H1 for anchor ${p.anchor}`);
    return md.trim();
  })
  .join('\n\n');

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(WORK, body);

const run = (cmd, args) => {
  try {
    return execFileSync(cmd, args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error(`missing ${cmd}; install it or set ${cmd === PANDOC ? 'PANDOC' : 'TYPST'}`);
    }
    throw new Error(`${cmd} failed:\n${err.stderr || err.stdout || err.message}`);
  }
};

const typstArg = (value) => value.replaceAll('\\', '\\\\').replaceAll('"', '\\"');
const typFile = resolve(ROOT, `dist/pdf-build-${lang}.typ`);
const cover = `/${coverRel(lang)}`;
run(PANDOC, [
  '--from=gfm+attributes+definition_lists',
  '--to=typst',
  '--wrap=none',
  `--template=${resolve(ROOT, 'forge/ebook/pdf/template.typ')}`,
  '-V', `booktitle=${typstArg(locale.title)}`,
  '-V', `ebooklang=${locale.typstLang}`,
  '-V', `ebookregion=${locale.typstRegion}`,
  '-V', `cover=${cover}`,
  '-V', `outlinetitle=${typstArg(locale.labels.toc)}`,
  '-V', `coverline1=${typstArg(`Built ${STAMP} (Asia/Shanghai)`)}`,
  '-V', `coverline2=${typstArg(`Commit ${COMMIT.slice(0, 7) || 'unknown'}`)}`,
  '-V', `coverline3=${typstArg(locale.site)}`,
  // Omitted (not "false") when LTR: pandoc $if() treats any set value as true.
  ...(isRtl(lang) ? ['-V', 'rtl=true'] : []),
  '-o',
  typFile,
  WORK,
]);
writeFileSync(typFile, fitTypstTableColumns(readFileSync(typFile, 'utf8')));
const log = run(TYPST, ['compile', typFile, OUT, '--root', ROOT]);
if (log.trim()) console.log(log.trim());
const size = statSync(OUT).size;
console.log(`wrote ${OUT}: ${bookFiles.length} chapters, ${docFiles.length} long reads, ${(size / 1048576).toFixed(1)} MB`);
