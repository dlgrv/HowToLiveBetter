"""Locale-link gate: translated chapters must not link to foreign-language files.

Guards the class of bugs found in ch10 (raw Chinese doc path as label+href)
and id-ch02 (link to docs/ root, which the Pages artifact does not even ship):

1. On body lines (attribution quotes ``>`` are exempt — they deliberately
   point at the Chinese original), a link target may contain CJK only if it
   is a known untranslated fallback doc (生物钟和夜班.md has no translation
   in any locale yet) — and its label must not be a raw ``docs/...`` path.
2. Body links must not point at ``docs/<zh>.md`` (repo root docs): the site
   artifact ships only ``docs/research/**`` — those links 404 on the site.
3. ``docs/research/<lang>/...`` targets must match the chapter's own locale.
4. Chapter cross-references ``../NN-*.md`` on body lines must be locale files
   (no CJK) — same-language navigation.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCALES = ["en", "ru", "es", "pt", "ar", "id"]
CJK = re.compile(r"[\u4e00-\u9fff]")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
# zh long-reads that have no translated counterpart yet — CJK href allowed,
# but the label must be a readable localized one, not a raw path.
FALLBACK_DOCS = {"生物钟和夜班.md"}


def violations() -> list[str]:
    bad: list[str] = []
    for lang in LOCALES:
        for p in sorted((ROOT / "book" / lang).glob("*.md")):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith(">"):
                    continue  # attribution header — intentionally points at zh
                for m in LINK.finditer(line):
                    label, href = m.group(1), m.group(2)
                    if href.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    where = f"{p.relative_to(ROOT)}:{i}"
                    if href.startswith("../") and CJK.search(href):
                        if not (
                            href.startswith("../../docs/research/")
                            and Path(href.rsplit("/", 1)[-1]).name in FALLBACK_DOCS
                        ):
                            bad.append(f"{where}: body link to CJK path {href!r}")
                        if label.startswith("docs/") or CJK.search(label):
                            bad.append(f"{where}: raw/CJK label {label!r} for fallback link")
                    if re.match(r"(?:\.\./)+docs/[^/]+\.md$", href):
                        bad.append(
                            f"{where}: link to docs/ root (not shipped on the site): {href!r}"
                        )
                    dm = re.match(r"(?:\.\./)+docs/research/([a-z]+)/", href)
                    if dm and dm.group(1) != lang:
                        bad.append(f"{where}: {lang} chapter links {dm.group(1)} doc {href!r}")
    return bad


def test_translated_chapters_have_no_foreign_language_links():
    bad = violations()
    assert not bad, "foreign-language links in translated chapters:\n" + "\n".join(bad)
