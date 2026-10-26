// Build one locale Anki deck (.apkg): one note per book item.
// Usage: node forge/ebook/anki/build.mjs --lang en [--out path.apkg]
// Front = item title; Back = plain terms / cost / benefit / evidence grade / notes.
// Subdecks per chapter; stable GUIDs (sha1 of lang+entryId) so re-imports update
// cards in place instead of duplicating (scheduling history is preserved).
import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import initSqlJs from 'sql.js';
import { ROOT, read, readBook, parseLang } from '../book.mjs';
import { splitChapter } from '../offline/build.mjs';

const KIND_LABELS = {
  cost: ['成本', 'Cost', 'Стоимость', 'Costo', 'Custo', 'التكلفة', 'Biaya'],
  plain: ['说人话', 'In plain terms', 'Простыми словами', 'En términos sencillos', 'Em linguagem simples', 'بعبارة بسيطة', 'Singkatnya'],
  gain: ['收益', 'Benefit', 'Эффект', 'Beneficio', 'Benefício', 'الفائدة', 'Manfaat'],
  grade: ['证据等级', 'Evidence grade', 'Уровень доказательности', 'Nivel de evidencia', 'Nível de evidência', 'مستوى الدليل', 'Tingkat bukti'],
  notes: ['备注', 'Notes', 'Примечания', 'Notas', 'ملاحظات', 'Catatan'],
};

const LABEL_TO_KIND = new Map(
  Object.entries(KIND_LABELS).flatMap(([kind, labels]) => labels.map((l) => [l, kind])),
);

/** Map an item body (raw md lines) to canonical field values. */
export function itemFields(body) {
  const out = { plain: '', cost: '', gain: '', grade: '', notes: '' };
  for (const line of body) {
    const m = /^- ([^：:]+)[：:]\s*(.*)$/.exec(line);
    if (!m) continue;
    const kind = LABEL_TO_KIND.get(m[1].trim());
    if (kind && !out[kind]) out[kind] = m[2].trim();
  }
  return out;
}

export function guidFor(lang, entryId) {
  return createHash('sha1').update(`${lang}:${entryId}`).digest('hex').slice(0, 20);
}

/** Minimal stored-entry zip writer (Anki accepts uncompressed members). */
export function zipStore(entries) {
  const enc = new TextEncoder();
  const blob = []; // [Uint8Array, ...]
  const central = [];
  let offset = 0;
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[i] = c >>> 0;
  }
  const crc32 = (bytes) => {
    let c = 0xffffffff;
    for (const b of bytes) c = table[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const u16 = (v) => new Uint8Array([v & 0xff, (v >>> 8) & 0xff]);
  const u32 = (v) => new Uint8Array([v & 0xff, (v >>> 8) & 0xff, (v >>> 16) & 0xff, (v >>> 24) & 0xff]);
  const cat = (arrs) => {
    const total = arrs.reduce((n, a) => n + a.length, 0);
    const outBuf = new Uint8Array(total);
    let p = 0;
    for (const a of arrs) {
      outBuf.set(a, p);
      p += a.length;
    }
    return outBuf;
  };
  for (const { name, data } of entries) {
    const nameB = enc.encode(name);
    const bytes = typeof data === 'string' ? enc.encode(data) : data;
    const crc = crc32(bytes);
    blob.push(u32(0x04034b50), u16(20), u16(0), u16(0), u16(0), u16(0), u32(crc), u32(bytes.length), u32(bytes.length), u16(nameB.length), u16(0), nameB, bytes);
    central.push({ nameB, crc, size: bytes.length, offset });
    offset += 30 + nameB.length + bytes.length;
  }
  const centralStart = offset;
  for (const c of central) {
    blob.push(u32(0x02014b50), u16(20), u16(20), u16(0), u16(0), u16(0), u16(0), u32(c.crc), u32(c.size), u32(c.size), u16(c.nameB.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(c.offset), c.nameB);
    offset += 46 + c.nameB.length;
  }
  blob.push(u32(0x06054b50), u16(0), u16(0), u16(central.length), u16(central.length), u32(offset - centralStart), u32(centralStart), u16(0));
  return Buffer.from(cat(blob));
}

const SCHEMA = `
CREATE TABLE col (id integer primary key, crt integer, mod integer, scm integer, ver integer, dty integer, usn integer, ls integer, conf text, models text, decks text, dconf text, tags text);
CREATE TABLE notes (id integer primary key, guid text, mid integer, mod integer, usn integer, tags text, flds text, sfld text, csum integer, flags integer, data text);
CREATE TABLE cards (id integer primary key, nid integer, did integer, ord integer, type integer, queue integer, due integer, ivl integer, factor integer, reps integer, lapses integer, left integer, odue integer, odid integer, flags integer, data text);
CREATE TABLE revlog (id integer primary key, cid integer, usn integer, ease integer, ivl integer, lastIvl integer, factor integer, time integer, type integer);
CREATE TABLE graves (usn integer, oid integer, type integer);
CREATE INDEX ix_notes_usn on notes (usn);
CREATE INDEX ix_revlog_usn on revlog (usn);
CREATE INDEX ix_cards_nid on cards (nid);
CREATE INDEX ix_revlog_cid on revlog (cid);
CREATE INDEX ix_notes_csum on notes (csum);
`;

/** Build one locale .apkg into outPath; returns { lang, chapters, notes, bytes }. */
export async function buildAnki(code, outPath) {
  const { locale, bookFiles } = readBook(code);
  const lang = code;
  const deckRoot = `HowToLiveBetter ${lang}`;
  const now = Date.now();
  const nowSec = Math.floor(now / 1000);
  const mid = 1740000000000 + (lang.charCodeAt(0) << 8) + lang.charCodeAt(1);
  const model = {
    [String(mid)]: {
      id: mid,
      name: `HTLB Item (${lang})`,
      type: 0,
      mod: nowSec,
      usn: 0,
      sortf: 0,
      did: 1,
      tmpls: [{ name: 'Card 1', ord: 0, qfmt: '{{Front}}', afmt: '{{FrontSide}}<hr id=answer>{{Back}}', bqfmt: '', bafmt: '', tags: [] }],
      flds: [
        { name: 'Front', ord: 0, sticky: false, rtl: false, font: 'Arial', size: 20, media: [] },
        { name: 'Back', ord: 1, sticky: false, rtl: false, font: 'Arial', size: 20, media: [] },
      ],
      req: [[0, 'any', [0]]],
      tags: [],
      vers: [],
    },
  };
  const deckJson = (id, name) => ({
    id,
    name,
    mod: nowSec,
    usn: 0,
    lrnToday: [0, 0],
    revToday: [0, 0],
    newToday: [0, 0],
    timeToday: [0, 0],
    collapsed: false,
    browserCollapsed: false,
    desc: '',
    dyn: 0,
    conf: 1,
    extendNew: 10,
    extendRev: 50,
  });
  const decks = { '1': deckJson(1, 'Default') };
  let deckSeq = 2000000000000;
  const deckOf = new Map(); // chapter NN → deck id

  const notesRows = [];
  const cardsRows = [];
  let noteSeq = 3000000000000;
  let cardSeq = 4000000000000;
  let due = 1;

  for (const src of bookFiles) {
    const ch = splitChapter(read(src));
    const deckId = ++deckSeq;
    decks[String(deckId)] = deckJson(deckId, `${deckRoot}::${ch.n}. ${ch.title}`);
    deckOf.set(ch.n, deckId);
    for (const it of ch.items) {
      const f = itemFields(it.body);
      const backParts = [];
      if (f.plain) backParts.push(f.plain);
      if (f.cost) backParts.push(`— ${f.cost}`);
      if (f.gain) backParts.push(`→ ${f.gain}`);
      const grade = f.grade || it.grade || '';
      const back = [backParts.join('\n'), grade ? `[${grade}]` : ''].filter(Boolean).join('\n');
      const sfld = it.title;
      const csum = parseInt(createHash('sha1').update(sfld).digest('hex').slice(0, 8), 16);
      const nid = ++noteSeq;
      notesRows.push([nid, guidFor(lang, `${ch.n}-${it.n}`), mid, nowSec, 0, '', [sfld, back].join('\u001f'), sfld, csum, 0, '']);
      cardsRows.push([++cardSeq, nid, deckId, 0, 0, 0, due++, 0, 2500, 0, 0, 0, 0, 0, 0, '']);
    }
  }

  const SQL = await initSqlJs();
  const db = new SQL.Database();
  db.run(SCHEMA);
  db.run(
    'INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
    [
      now,
      Math.floor(nowSec / 86400) * 86400,
      nowSec,
      0,
      11,
      0,
      0,
      0,
      JSON.stringify({
        nextPos: 1, estTimes: true, activeDecks: [1], sortType: 'noteFld',
        timeLim: 0, sortBackwards: false, addToCur: true, curDeck: 1,
        newBury: true, newSpread: 0, dueCounts: true, curModel: mid,
        collapseTime: 1200,
      }),
      JSON.stringify(model),
      JSON.stringify(decks),
      JSON.stringify({
        1: {
          id: 1, name: 'Default', replayq: true, mod: nowSec, usn: 0, autoplay: true, timer: 0, maxTaken: 60,
          lapse: { delays: [10, 60, 3600], mult: 0, minInt: 1, leechFails: 8, leechAction: 0 },
          rev: { perDay: 200, fuzz: 0.05, ivlFct: 1, maxIvl: 36500, ease4: 1.3, bury: true, minSpace: 1 },
          new: { perDay: 20, delays: [1, 10], separate: true, ints: [1, 4, 7], initialFactor: 2500, bury: true, order: 1 },
        },
      }),
      JSON.stringify({}),
    ],
  );
  for (const r of notesRows) db.run('INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)', r);
  for (const r of cardsRows) db.run('INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', r);
  const collection = Buffer.from(db.export());
  db.close();

  const apkg = zipStore([
    { name: 'collection.anki2', data: collection },
    { name: 'media', data: '{}' },
  ]);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, apkg);
  return { lang: code, chapters: bookFiles.length, notes: notesRows.length, bytes: apkg.length, locale };
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;
if (isMain) {
  const args = process.argv.slice(2);
  const outIdx = args.indexOf('--out');
  const lang = parseLang();
  const out = outIdx >= 0 ? resolve(args[outIdx + 1]) : resolve(ROOT, `dist/HowToLiveBetter-${lang}.apkg`);
  const stats = await buildAnki(lang, out);
  console.log(`anki: ${stats.lang} → ${out} (${stats.chapters} subdecks, ${stats.notes} notes, ${(stats.bytes / 1024).toFixed(0)} KB)`);
}
