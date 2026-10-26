// Build one locale single-file offline HTML (whole book + search + grade filter).
// Usage: node forge/ebook/offline/build.mjs --lang en
// Output: dist/HowToLiveBetter-<lang>.html — double-click to open, no server.
import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname, posix, basename } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Marked } from 'marked';
import {
  ROOT,
  REPO,
  SITE_BASE,
  read,
  readBook,
  parseLang,
  isRtl,
  gitCommit,
  buildStamp,
  formatEntryFields,
  stripSourceLines,
  aboutMd,
} from '../book.mjs';

const GRADE_RE =
  /^- (?:证据等级|Уровень доказательности|Evidence grade|Nivel de evidencia|Nível de evidência|مستوى الدليل|Tingkat bukti)[：:]\s*\(?([ABC])\)?/;

const SEARCH_LABELS = {
  en: 'Search…', ru: 'Поиск…', zh: '搜索…', es: 'Buscar…', pt: 'Buscar…',
  ar: 'بحث…', id: 'Cari…',
};

/** Split a raw chapter into { n, title, intro, items: [{n, title, grade, body}] }. */
export function splitChapter(md) {
  const lines = md.split('\n');
  let n = '';
  let title = '';
  let intro = [];
  const items = [];
  let cur = null;
  const flush = () => {
    if (cur) {
      while (cur.body.length && cur.body[cur.body.length - 1].trim() === '') cur.body.pop();
      items.push(cur);
    }
    cur = null;
  };
  for (const line of lines) {
    let m;
    if ((m = /^# (\d+)\. (.+)$/.exec(line))) {
      flush();
      n = m[1];
      title = m[2].trim();
      intro = [];
      continue;
    }
    if ((m = /^### (\d+)\. (.+)$/.exec(line))) {
      flush();
      cur = { n: m[1], title: m[2].trim(), grade: '', body: [] };
      continue;
    }
    if (/^#{1,6} /.test(line)) {
      flush();
      continue;
    }
    if (cur) {
      if (!cur.grade) {
        const g = GRADE_RE.exec(line);
        if (g) cur.grade = g[1];
      }
      cur.body.push(line);
      continue;
    }
    // Intro collects only before the first item; chapter tails are noise.
    if (n && items.length === 0 && line.trim() && !line.startsWith('[←') && !line.startsWith('>')) intro.push(line);
  }
  flush();
  return { n, title, intro: intro.join('\n'), items };
}

export function escHtml(s) {
  return s.replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
}

const CSS = `
:root{--bg:#fff;--ink:#1a1a1a;--mut:#666;--faint:#999;--line:#e5e5e5;--soft:#f6f6f7;--accent:#3451b2;--serif:Georgia,'Times New Roman',serif;--sans:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,'PingFang SC','Noto Sans SC',sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#111;--ink:#d0d0d0;--mut:#999;--faint:#6c6c6c;--line:#2e2e32;--soft:#1b1b1f;--accent:#a8b1ff;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 var(--serif)}
.top{position:sticky;top:0;z-index:5;display:flex;gap:8px;align-items:center;padding:10px 16px;background:var(--bg);border-bottom:1px solid var(--line);font-family:var(--sans);font-size:13px;flex-wrap:wrap}
.brand{font-weight:700;color:var(--ink);text-decoration:none;margin-right:auto}
#q{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-width:10ch;flex:1;max-width:34ch}
#grade{font:inherit;padding:6px 6px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--mut)}
#cnt{color:var(--faint);white-space:nowrap}
#nav{padding:10px 16px;border-bottom:1px solid var(--line);font-family:var(--sans);font-size:13px;display:flex;flex-wrap:wrap;gap:4px 14px}
#nav a{color:var(--mut);text-decoration:none}
#nav a:hover{color:var(--accent)}
main{max-width:46rem;margin:0 auto;padding:24px 16px 64px}
.sec{margin:40px 0}
.sec>h2{font-family:var(--sans);font-size:22px;line-height:1.3;border-bottom:1px solid var(--line);padding-bottom:8px}
.intro{color:var(--mut)}
.item{padding:14px 0;border-bottom:1px solid var(--line)}
.item>h3{font-family:var(--sans);font-size:16px;line-height:1.4;margin:0 0 8px}
dl.entry{margin:0;display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:14px}
dl.entry dt{color:var(--faint);font-family:var(--sans);font-size:12px;white-space:nowrap}
dl.entry dd{margin:0;color:var(--mut)}
a{color:var(--accent)}
footer{max-width:46rem;margin:0 auto;padding:0 16px 48px;color:var(--faint);font-family:var(--sans);font-size:12px;line-height:1.6}
`;

const FILTER_JS = `
(function(){
  var q=document.getElementById('q'),g=document.getElementById('grade'),cnt=document.getElementById('cnt');
  function apply(){
    var t=(q.value||'').trim().toLowerCase(),gv=g.value,shown=0;
    var items=document.querySelectorAll('.item');
    for(var i=0;i<items.length;i++){
      var it=items[i];
      var ok=(!t||it.getAttribute('data-hay').indexOf(t)>=0)&&(!gv||it.getAttribute('data-grade')===gv);
      it.hidden=!ok; if(ok)shown++;
    }
    var secs=document.querySelectorAll('.sec');
    for(var j=0;j<secs.length;j++){
      var s=secs[j];
      var vis=s.querySelectorAll('.item:not([hidden])').length;
      s.hidden=(t||gv)&&vis===0;
    }
    cnt.textContent=shown+'/'+items.length;
  }
  q.addEventListener('input',apply);
  g.addEventListener('change',apply);
  apply();
})();
`;

/** Build one locale into outPath; returns { lang, sections, items, bytes }. */
export function buildOffline(code, outPath) {
  const book = readBook(code);
  const { locale, description, frontMd, bookFiles, docFiles } = book;
  const RTL = isRtl(code);
  const STAMP = buildStamp();
  const COMMIT = gitCommit();

  const anchorOf = new Map();
  bookFiles.forEach((f) => anchorOf.set(f, `sec-${basename(f).match(/^\d+/)?.[0] ?? anchorOf.size + 1}`));
  docFiles.forEach((f, i) => anchorOf.set(f, `doc-${i + 1}`));
  anchorOf.set(locale.readme, 'front');

  const marked = new Marked({ gfm: true });
  marked.use({
    renderer: {
      link({ href, title, tokens }) {
        const text = this.parser.parseInline(tokens);
        const t = title ? ` title="${escHtml(title)}"` : '';
        return `<a href="${escHtml(rewriteHref(href))}"${t}>${text}</a>`;
      },
      image: () => '',
    },
  });

  function rewriteHref(href) {
    if (/^(https?:|mailto:|#)/.test(href)) return href;
    const [pathPart, hash] = href.split('#');
    const target = posix.normalize(posix.join(posix.dirname(currentSrc), pathPart));
    if (anchorOf.has(target)) return `#${anchorOf.get(target)}${hash ? '#' + hash : ''}`;
    const kind = target.endsWith('/') ? 'tree' : 'blob';
    return `${REPO}/${kind}/main/${target}`;
  }

  let currentSrc = locale.readme;

  const render = (md) => {
    const raw = marked.parse(md);
    return raw.replace(/<!--[\s\S]*?-->/g, '');
  };

  const navLinks = [];
  const mainParts = [];

  mainParts.push(`<section class="sec" id="front"><h2>${escHtml(locale.labels.front)}</h2>${render(formatEntryFields(stripSourceLines(frontMd), 'html'))}</section>`);
  navLinks.push(`<a href="#front">${escHtml(locale.labels.front)}</a>`);

  let totalItems = 0;
  for (const src of bookFiles) {
    currentSrc = src;
    const ch = splitChapter(read(src));
    const secId = anchorOf.get(src);
    const itemsHtml = ch.items.map((it) => {
      const hay = escHtml((it.title + '\n' + it.body.join('\n')).toLowerCase());
      const body = render(formatEntryFields(stripSourceLines(it.body.join('\n')), 'html'));
      return `<article class="item" data-grade="${it.grade}" data-hay="${hay}"><h3>${it.n}. ${render(it.title).replace(/<\/?p>/g, '')}</h3>${body}</article>`;
    }).join('\n');
    totalItems += ch.items.length;
    mainParts.push(`<section class="sec" id="${secId}" data-sec="${ch.n}"><h2>${ch.n}. ${escHtml(ch.title)}</h2><p class="intro">${render(ch.intro).replace(/<\/?p>/g, '')}</p>${itemsHtml}</section>`);
    navLinks.push(`<a href="#${secId}">${ch.n}. ${escHtml(ch.title)}</a>`);
  }

  docFiles.forEach((src, i) => {
    currentSrc = src;
    const md = read(src).replace(/^# (.+)$/, (all, h) => `# ${h}`);
    const text = render(stripSourceLines(formatEntryFields(md, 'html')));
    mainParts.push(`<section class="sec" id="doc-${i + 1}">${text}</section>`);
    const h = /<h1[^>]*>(.*?)<\/h1>/.exec(text);
    navLinks.push(`<a href="#doc-${i + 1}">${h ? h[1] : 'doc'}</a>`);
  });

  currentSrc = locale.readme;
  mainParts.push(`<section class="sec" id="about">${render(aboutMd(locale, STAMP, COMMIT))}</section>`);
  navLinks.push(`<a href="#about">${escHtml(locale.labels.about)}</a>`);

  const short = COMMIT ? COMMIT.slice(0, 7) : '';
  const html = `<!doctype html>
<html lang="${code}"${RTL ? ' dir="rtl"' : ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escHtml(locale.title)}</title>
<meta name="description" content="${escHtml(description)}">
<meta name="generator" content="HowToLiveBetter offline builder (${short})">
<style>${CSS}</style>
</head>
<body id="top">
<header class="top"><a class="brand" href="#top">${escHtml(locale.title)}</a><input id="q" type="search" placeholder="${escHtml(SEARCH_LABELS[code] ?? 'Search…')}" aria-label="search"><select id="grade" aria-label="grade"><option value="">A·B·C</option><option value="A">A</option><option value="B">B</option><option value="C">C</option></select><span id="cnt"></span></header>
<nav id="nav">${navLinks.join(' ')}</nav>
<main id="main">
${mainParts.join('\n')}
</main>
<footer><p>${escHtml(locale.title)} · <a href="${SITE_BASE}/${code}/">${SITE_BASE}/${code}/</a> · <a href="${REPO}">${REPO}</a></p><p>${escHtml(STAMP)} · ${escHtml(short)}</p></footer>
<script>${FILTER_JS}</script>
</body>
</html>
`;

  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, html);
  return { lang: code, sections: bookFiles.length, items: totalItems, bytes: Buffer.byteLength(html) };
}

const isMain =
  process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;
if (isMain) {
  const lang = parseLang();
  const out = resolve(ROOT, `dist/HowToLiveBetter-${lang}.html`);
  const stats = buildOffline(lang, out);
  console.log(`offline: ${stats.lang} → ${out} (${stats.sections} sections, ${stats.items} items, ${(stats.bytes / 1048576).toFixed(2)} MB)`);
}
