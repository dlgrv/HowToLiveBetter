// 把 README + book/*.md + docs/*.md 打成一本 EPUB 3。
// 用法：node tools/epub/build.mjs [输出路径]   默认输出 dist/HowToLiveBetter.epub
// 只依赖 marked；zip 自己写（EPUB 要求 mimetype 第一个且不压缩，通用 zip 库不一定保证）。
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname, posix } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deflateRawSync } from 'node:zlib';
import { execSync } from 'node:child_process';
import { Marked } from 'marked';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const OUT = resolve(ROOT, process.argv[2] ?? 'dist/HowToLiveBetter.epub');
const REPO = 'https://github.com/eternity4719/HowToLiveBetter';
const SITE = 'https://eternity4719.github.io/HowToLiveBetter/';
const RELEASE = `${REPO}/releases/download/epub-latest/HowToLiveBetter.epub`;
const TITLE = '高性价比人生指南';
const BOOK_ID = 'urn:uuid:5c0c1c0e-6a5c-4d2b-9b1e-7d1f0a4e8c31';
const NOW = new Date();
const COMMIT = gitCommit();

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const read = p => readFileSync(resolve(ROOT, p), 'utf8');
const plain = html => html.replace(/<[^>]+>/g, '');

function gitCommit() {
  try {
    return execSync('git rev-parse HEAD', { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return process.env.GITHUB_SHA ?? '';
  }
}

// ---------- 从 README 取内容与文件清单 ----------
const readme = read('README.md');
const readmeLines = readme.split('\n');
const between = (from, to) => {
  const a = readmeLines.findIndex(l => l.startsWith(from));
  const b = readmeLines.findIndex((l, i) => i > a && l.startsWith(to));
  if (a < 0 || b < 0) throw new Error(`README 里找不到 ${from} 到 ${to} 这一段`);
  return readmeLines.slice(a, b).join('\n');
};
const description = between('# 高性价比人生指南', '[![')
  .split('\n').slice(1).map(l => l.replace(/<[^>]+>/g, '').trim()).filter(Boolean).join('');
const frontMd = between('## 这本书想回答的问题', '## 目录');
const contentsMd = between('## 目录', '## 正文')
  .replace(/^## 目录/, '# 各节简介')
  .split('\n\n').filter(p => !p.includes('index.html')).join('\n\n');
const unique = arr => [...new Set(arr)];
const bookFiles = unique([...contentsMd.matchAll(/\]\((book\/[^)#]+\.md)\)/g)].map(m => m[1]));
const docFiles = unique([...readme.matchAll(/\]\((docs\/[^)#/]+\.md)\)/g)].map(m => m[1]));
if (bookFiles.length === 0) throw new Error('README 目录里没找到 book/ 文件');

// ---------- 页面清单 ----------
// 每页：xhtml 文件名、来源 md 的仓库路径（用来解析相对链接）、md 正文
const pages = [
  { file: 'front.xhtml', src: 'README.md', title: '前言', md: `# ${TITLE}\n\n${description}\n\n${frontMd}` },
  { file: 'contents.xhtml', src: 'README.md', title: '各节简介', md: contentsMd },
  ...bookFiles.map((src, i) => ({ file: `ch${String(i + 1).padStart(2, '0')}.xhtml`, src, md: stripBackLink(read(src)) })),
  ...docFiles.map((src, i) => ({ file: `doc${i + 1}.xhtml`, src, md: stripBackLink(read(src)) })),
  { file: 'about.xhtml', src: 'README.md', title: '版本说明', md: aboutMd() },
];
const pageByPath = new Map(pages.map(p => [p.src, p.file]));
pageByPath.set('README.md', 'front.xhtml');

function stripBackLink(md) {
  return md.replace(/^\[← 回总目录\]\([^)]*\)\s*\n/, '');
}

function aboutMd() {
  const date = NOW.toISOString().slice(0, 10);
  const commitLine = COMMIT ? `- 对应提交：[${COMMIT.slice(0, 7)}](${REPO}/commit/${COMMIT})` : '';
  return `# 版本说明

这本电子书由仓库里的 Markdown 正文自动生成，正文一改就重新生成一本。手里这本的版本：

- 生成日期：${date}
${commitLine}
- 最新版下载：${RELEASE}
- 在线检索页（按关键词、章节、证据等级和成本筛选）：${SITE}
- 仓库、提意见、看每条来源的核实记录：${REPO}

正文里指向仓库内其他文件的链接已改成书内跳转；指向核实记录、许可证这类没收进书的文件的链接改成了 GitHub 网址。

全书以 Unlicense 发布，属于公有领域，可以随意复制、修改、分发。`;
}

// ---------- Markdown → XHTML ----------
let current = null; // 正在转换的页
let headingSeq = 0;
const marked = new Marked({ gfm: true });
marked.use({
  renderer: {
    heading({ tokens, depth }) {
      const html = this.parser.parseInline(tokens);
      const id = `h${++headingSeq}`;
      current.headings.push({ id, depth, text: plain(html) });
      return `<h${depth} id="${id}">${html}</h${depth}>\n`;
    },
    link({ href, title, tokens }) {
      const text = this.parser.parseInline(tokens);
      const t = title ? ` title="${esc(title)}"` : '';
      return `<a href="${esc(rewriteHref(href))}"${t}>${text}</a>`;
    },
    image: () => '',
    html: () => '',
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
  return `<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">
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
  const body = toXhtml(marked.parse(p.md));
  p.title ??= p.headings[0]?.text ?? p.file;
  p.xhtml = wrap(p.title, `<section epub:type="chapter">\n${body}</section>\n`);
}

// ---------- 导航 ----------
const navItems = pages.map(p => {
  const [first, ...rest] = p.headings;
  const top = first?.depth === 1 ? { href: `${p.file}#${first.id}`, text: p.title } : { href: p.file, text: p.title };
  const subs = (first?.depth === 1 ? rest : p.headings).filter(h => h.depth <= 3).map(h => ({ href: `${p.file}#${h.id}`, text: h.text }));
  return { ...top, subs };
});

const navXhtml = wrap('目录', `<nav epub:type="toc" id="toc">
<h1>目录</h1>
<ol>
${navItems.map(n => `<li><a href="${n.href}">${n.text}</a>${n.subs.length ? `\n<ol>\n${n.subs.map(s => `<li><a href="${s.href}">${s.text}</a></li>`).join('\n')}\n</ol>\n` : ''}</li>`).join('\n')}
</ol>
</nav>
<nav epub:type="landmarks" hidden="hidden">
<ol>
<li><a epub:type="cover" href="cover.xhtml">封面</a></li>
<li><a epub:type="bodymatter" href="${pages[2].file}">正文</a></li>
</ol>
</nav>
`);

let play = 0;
const navPoint = n => `<navPoint id="np${++play}" playOrder="${play}"><navLabel><text>${n.text}</text></navLabel><content src="${n.href}"/>${n.subs?.map(navPoint).join('') ?? ''}</navPoint>`;
const ncx = `<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="zh-CN">
<head>
<meta name="dtb:uid" content="${BOOK_ID}"/>
<meta name="dtb:depth" content="2"/>
<meta name="dtb:totalPageCount" content="0"/>
<meta name="dtb:maxPageNumber" content="0"/>
</head>
<docTitle><text>${TITLE}</text></docTitle>
<navMap>
${navItems.map(navPoint).join('\n')}
</navMap>
</ncx>
`;

// ---------- 封面、OPF、容器 ----------
const coverXhtml = wrap(TITLE, `<div class="cover"><img src="cover.png" alt="${esc(TITLE)}"/></div>\n`);
const modified = NOW.toISOString().replace(/\.\d{3}Z$/, 'Z');
const manifestPages = pages.map(p => `<item id="${p.file.replace('.xhtml', '')}" href="${p.file}" media-type="application/xhtml+xml"/>`);
const opf = `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="zh-CN">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="pub-id">${BOOK_ID}</dc:identifier>
<dc:title>${TITLE}</dc:title>
<dc:language>zh-CN</dc:language>
<dc:creator>eternity4719</dc:creator>
<dc:description>${esc(description)}</dc:description>
<dc:source>${REPO}</dc:source>
<dc:rights>Unlicense（公有领域）</dc:rights>
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
${pages.map(p => `<itemref idref="${p.file.replace('.xhtml', '')}"/>`).join('\n')}
</spine>
</package>
`;
const container = `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
`;

// ---------- 打 zip ----------
const entries = [
  { name: 'mimetype', data: Buffer.from('application/epub+zip'), store: true },
  { name: 'META-INF/container.xml', data: Buffer.from(container) },
  { name: 'OEBPS/content.opf', data: Buffer.from(opf) },
  { name: 'OEBPS/nav.xhtml', data: Buffer.from(navXhtml) },
  { name: 'OEBPS/toc.ncx', data: Buffer.from(ncx) },
  { name: 'OEBPS/style.css', data: readFileSync(resolve(ROOT, 'tools/epub/style.css')) },
  { name: 'OEBPS/cover.png', data: readFileSync(resolve(ROOT, 'og.png')) },
  { name: 'OEBPS/cover.xhtml', data: Buffer.from(coverXhtml) },
  ...pages.map(p => ({ name: `OEBPS/${p.file}`, data: Buffer.from(p.xhtml) })),
];
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, zip(entries));
const entryCount = pages.filter(p => p.file.startsWith('ch')).reduce((n, p) => n + p.headings.filter(h => h.depth === 3).length, 0);
console.log(`已生成 ${OUT}：${bookFiles.length} 节 ${entryCount} 条，附录 ${docFiles.length} 篇，${(entries.reduce((n, e) => n + e.data.length, 0) / 1024 | 0)} KB 未压缩`);

function zip(files) {
  const crcTable = new Int32Array(256).map((_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c;
  });
  const crc32 = buf => {
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
