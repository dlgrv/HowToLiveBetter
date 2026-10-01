// Build one locale EPUB 3.
// Usage: node forge/ebook/epub/build.mjs --lang en
// marked only; the zip writer stores mimetype first and uncompressed.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname, posix } from 'node:path';
import { deflateRawSync } from 'node:zlib';
import { Marked, Tokenizer } from 'marked';
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
  headingText,
  renderEpubHtmlToken,
  fitEpubTableColumns,
  xmlEscape,
  parseLang,
  aboutMd,
  coverRel,
} from '../book.mjs';

const lang = parseLang();
const book = readBook(lang);
const { locale, description, frontMd, bookFiles, docFiles } = book;
const OUT = resolve(ROOT, `dist/HowToLiveBetter-${lang}.epub`);
const COMMIT = gitCommit();
const NOW = new Date();
const BOOK_IDS = {
  en: 'urn:uuid:6f0e2a10-7b21-4c3a-9d11-000000000001',
  ru: 'urn:uuid:6f0e2a10-7b21-4c3a-9d11-000000000002',
  zh: 'urn:uuid:6f0e2a10-7b21-4c3a-9d11-000000000003',
  es: 'urn:uuid:6f0e2a10-7b21-4c3a-9d11-000000000004',
  pt: 'urn:uuid:6f0e2a10-7b21-4c3a-9d11-000000000005',
};
const BOOK_ID = BOOK_IDS[lang];
const contentsMd = book.contentsMd.replace(/^## [^\n]+/, `# ${locale.labels.contents}`);

const esc = xmlEscape;

const pages = [
  {
    file: 'front.xhtml',
    src: locale.readme,
    title: locale.labels.front,
    md: `# ${locale.title}\n\n${description}\n\n${formatEntryFields(stripSourceLines(frontMd), 'html')}`,
  },
  { file: 'contents.xhtml', src: locale.readme, title: locale.labels.contents, md: contentsMd },
  ...bookFiles.map((src, i) => ({
    file: `ch${String(i + 1).padStart(2, '0')}.xhtml`,
    src,
    md: prepareSection(read(src), 'html'),
  })),
  ...docFiles.map((src, i) => ({
    file: `doc${i + 1}.xhtml`,
    src,
    md: prepareSection(read(src), 'html'),
  })),
  {
    file: 'about.xhtml',
    src: locale.readme,
    title: locale.labels.about,
    md: aboutMd(locale, buildStamp(), COMMIT),
  },
];
const pageByPath = new Map(pages.map((p) => [p.src, p.file]));
pageByPath.set(locale.readme, 'front.xhtml');

let current = null;
let headingSeq = 0;
const marked = new Marked({ gfm: true });
marked.use({
  tokenizer: {
    url(src) {
      const tok = Tokenizer.prototype.url.call(this, src);
      if (!tok || /^[\x21-\x7e]*$/.test(tok.raw)) return tok;
      return Tokenizer.prototype.url.call(this, tok.raw.match(/^[\x21-\x7e]*/)[0]);
    },
  },
  renderer: {
    heading({ tokens, depth }) {
      const html = this.parser.parseInline(tokens);
      const id = `h${++headingSeq}`;
      current.headings.push({ id, depth, text: headingText(html) });
      return `<h${depth} id="${id}">${html}</h${depth}>\n`;
    },
    link({ href, title, tokens }) {
      const text = this.parser.parseInline(tokens);
      const t = title ? ` title="${esc(title)}"` : '';
      return `<a href="${esc(rewriteHref(href))}"${t}>${text}</a>`;
    },
    image: () => '',
    html({ text }) {
      return renderEpubHtmlToken(text);
    },
  },
});

function rewriteHref(href) {
  if (/^(https?:|mailto:|#)/.test(href)) return href;
  const [pathPart, hash] = href.split('#');
  const target = posix.normalize(posix.join(posix.dirname(current.src), pathPart));
  const page = pageByPath.get(target);
  if (page) return hash ? `${page}#${hash}` : page;
  const kind = target.endsWith('/') ? 'tree' : 'blob';
  return `${REPO}/${kind}/main/${target}`;
}

function toXhtml(body) {
  return body
    .replace(/<(br|hr)>/g, '<$1/>')
    .replace(/<(img|input)\b([^>]*?)\s*\/?>/g, '<$1$2/>')
    .replace(/&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)/g, '&amp;');
}

function wrap(title, body) {
  const dc = locale.dcLanguage;
  const dir = locale.code === 'ar' ? ' dir="rtl"' : '';
  return `<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="${dc}" lang="${dc}"${dir}>
<head>
<meta charset="utf-8"/>
<title>${esc(title)}</title>
<link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
${body}</body>
</html>
`;
}

for (const p of pages) {
  current = p;
  p.headings = [];
  headingSeq = 0;
  const body = toXhtml(fitEpubTableColumns(marked.parse(p.md)));
  p.title ??= p.headings[0]?.text ?? p.file;
  p.xhtml = wrap(p.title, `<section epub:type="chapter">\n${body}</section>\n`);
}

const navItems = pages.map((p) => {
  const [first] = p.headings;
  const top = first?.depth === 1 ? { href: `${p.file}#${first.id}`, text: p.title } : { href: p.file, text: p.title };
  return { ...top, subs: [] };
});

const navXhtml = wrap(
  locale.labels.toc,
  `<nav epub:type="toc" id="toc">
<h1>${esc(locale.labels.toc)}</h1>
<ol>
${navItems.map((n) => `<li><a href="${n.href}">${esc(n.text)}</a>${n.subs.length ? `\n<ol>\n${n.subs.map((s) => `<li><a href="${s.href}">${esc(s.text)}</a></li>`).join('\n')}\n</ol>\n` : ''}</li>`).join('\n')}
</ol>
</nav>
<nav epub:type="landmarks" hidden="hidden">
<ol>
<li><a epub:type="cover" href="cover.xhtml">${esc(locale.labels.cover)}</a></li>
<li><a epub:type="bodymatter" href="${pages[2].file}">${esc(locale.labels.body)}</a></li>
</ol>
</nav>
`,
);

let play = 0;
const navPoint = (n) => {
  const id = `np${++play}`;
  return `<navPoint id="${id}" playOrder="${play}"><navLabel><text>${esc(n.text)}</text></navLabel><content src="${n.href}"/>${n.subs?.map(navPoint).join('') ?? ''}</navPoint>`;
};
const ncx = `<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="${locale.dcLanguage}">
<head>
<meta name="dtb:uid" content="${BOOK_ID}"/>
<meta name="dtb:depth" content="2"/>
<meta name="dtb:totalPageCount" content="0"/>
<meta name="dtb:maxPageNumber" content="0"/>
</head>
<docTitle><text>${esc(locale.title)}</text></docTitle>
<navMap>
${navItems.map(navPoint).join('\n')}
</navMap>
</ncx>
`;

const coverXhtml = wrap(locale.title, `<div class="cover"><img src="cover.png" alt="${esc(locale.title)}"/></div>\n`);
const modified = NOW.toISOString().replace(/\.\d{3}Z$/, 'Z');
const manifestPages = pages.map(
  (p) => `<item id="${p.file.replace('.xhtml', '')}" href="${p.file}" media-type="application/xhtml+xml"/>`,
);
const opf = `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="${locale.dcLanguage}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="pub-id">${BOOK_ID}</dc:identifier>
<dc:title>${esc(locale.title)}</dc:title>
<dc:language>${esc(locale.dcLanguage)}</dc:language>
<dc:creator>dlgrv</dc:creator>
<dc:description>${esc(description)}</dc:description>
<dc:source>${REPO}</dc:source>
<dc:rights>Unlicense</dc:rights>
<dc:date>${NOW.toISOString().slice(0, 10)}</dc:date>
<meta property="dcterms:modified">${modified}</meta>
<meta name="cover" content="cover-img"/>
</metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
<item id="css" href="style.css" media-type="text/css"/>
<item id="cover-img" href="cover.png" media-type="image/png" properties="cover-image"/>
<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>
${manifestPages.join('\n')}
</manifest>
<spine toc="ncx">
<itemref idref="cover"/>
${pages.map((p) => `<itemref idref="${p.file.replace('.xhtml', '')}"/>`).join('\n')}
</spine>
</package>
`;
const container = `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
`;

const entries = [
  { name: 'mimetype', data: Buffer.from('application/epub+zip'), store: true },
  { name: 'META-INF/container.xml', data: Buffer.from(container) },
  { name: 'OEBPS/content.opf', data: Buffer.from(opf) },
  { name: 'OEBPS/nav.xhtml', data: Buffer.from(navXhtml) },
  { name: 'OEBPS/toc.ncx', data: Buffer.from(ncx) },
  { name: 'OEBPS/style.css', data: readFileSync(resolve(ROOT, 'forge/ebook/epub/style.css')) },
  { name: 'OEBPS/cover.png', data: readFileSync(resolve(ROOT, coverRel(lang))) },
  { name: 'OEBPS/cover.xhtml', data: Buffer.from(coverXhtml) },
  ...pages.map((p) => ({ name: `OEBPS/${p.file}`, data: Buffer.from(p.xhtml) })),
];
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, zip(entries));
console.log(`wrote ${OUT}: ${bookFiles.length} chapters, ${docFiles.length} long reads`);

function zip(files) {
  const crcTable = new Int32Array(256).map((_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c;
  });
  const crc32 = (buf) => {
    let c = -1;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ -1) >>> 0;
  };
  const dosTime = (NOW.getHours() << 11) | (NOW.getMinutes() << 5) | (NOW.getSeconds() >> 1);
  const dosDate = ((NOW.getFullYear() - 1980) << 9) | ((NOW.getMonth() + 1) << 5) | NOW.getDate();
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const f of files) {
    const name = Buffer.from(f.name);
    const data = f.store ? f.data : deflateRawSync(f.data, { level: 9 });
    const method = f.store ? 0 : 8;
    const crc = crc32(f.data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6);
    local.writeUInt16LE(method, 8);
    local.writeUInt16LE(dosTime, 10);
    local.writeUInt16LE(dosDate, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(f.data.length, 22);
    local.writeUInt16LE(name.length, 26);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0800, 8);
    central.writeUInt16LE(method, 10);
    central.writeUInt16LE(dosTime, 12);
    central.writeUInt16LE(dosDate, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(f.data.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt32LE(offset, 42);
    locals.push(local, name, data);
    centrals.push(central, name);
    offset += local.length + name.length + data.length;
  }
  const cd = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(cd.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, cd, end]);
}
