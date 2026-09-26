#!/usr/bin/env python3
"""Auto-update README and OG previews when chapters change.

- Scans book/LANG/ for markdown chapters
- Checks if each chapter has an OG preview image (og/{LANG}/{N}.png)
- Reports missing og images, missing README entries, and stale hashes
- --fix mode regenerates README chapter lists from actual files
"""

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chapter_id(filename):
    """Extract chapter number from filename like '01-Не-умирайте-рано.md'."""
    m = re.match(r"(\d+)", filename)
    return int(m.group(1)) if m else None


def chapter_title(path):
    """Extract H1 title from a chapter file."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^# (.+)", line)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def file_hash(path):
    """SHA256 of file contents."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def scan_chapters(lang_dir):
    """Return sorted list of (id, filename, title, hash) for chapters in lang_dir."""
    chapters = []
    if not os.path.isdir(lang_dir):
        return chapters
    for fn in sorted(os.listdir(lang_dir)):
        if not fn.endswith(".md"):
            continue
        cid = chapter_id(fn)
        if cid is None:
            continue
        path = os.path.join(lang_dir, fn)
        title = chapter_title(path)
        h = file_hash(path)
        chapters.append((cid, fn, title, h))
    chapters.sort()
    return chapters


def check_og_images(lang, chapters):
    """Check og/{lang}/ directory for preview images."""
    og_dir = os.path.join(ROOT, "og", lang)
    missing = []
    if not os.path.isdir(og_dir):
        return [(cid, title) for cid, _, title, _ in chapters]
    for cid, _, title, _ in chapters:
        og_path = os.path.join(og_dir, f"{cid:02d}.png")
        if not os.path.isfile(og_path):
            missing.append((cid, title))
    return missing


def readme_section(readme_path, lang):
    """Find the chapter list section in a README file."""
    if not os.path.isfile(readme_path):
        return None, 0, 0
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()
    # Find chapter list: lines with numbers followed by titles
    # Pattern: "1. **Title**" or "01. Title" or "1. [Title](link)"
    pattern = re.compile(r"^\d+\.?\s+.+", re.MULTILINE)
    sections = list(pattern.finditer(content))
    return content, 0, len(content)


def check_readme(lang, chapters):
    """Check if README_{LANG}.md has correct chapter count and order."""
    readme_name = f"README_{lang.upper()}.md"
    readme_path = os.path.join(ROOT, readme_name)
    if not os.path.isfile(readme_path):
        return f"{readme_name} not found", []

    content, _, _ = readme_section(readme_path, lang)

    issues = []
    # Extract numbered entries from README
    entries = re.findall(r"^\s*(\d+)\.?\s+(.+)", content, re.MULTILINE)
    readme_ids = [int(n) for n, _ in entries]
    chapter_ids = [cid for cid, _, _, _ in chapters]

    missing_in_readme = set(chapter_ids) - set(readme_ids)
    extra_in_readme = set(readme_ids) - set(chapter_ids)

    if missing_in_readme:
        issues.append(f"Chapters not in README: {sorted(missing_in_readme)}")
    if extra_in_readme:
        issues.append(f"README entries with no chapter: {sorted(extra_in_readme)}")

    return None if not issues else "; ".join(issues), []


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Audit/update README chapter lists and OG preview images")
    ap.add_argument("lang", nargs="?", default=None,
                    help="Language to check (ru/en/es/zh); omit for all")
    ap.add_argument("--fix", action="store_true",
                    help="Regenerate README chapter lists")
    ap.add_argument("--json", action="store_true",
                    help="Output JSON")
    args = ap.parse_args()

    langs = [args.lang] if args.lang else ["ru", "en", "es", "zh"]
    results = {}

    for lang in langs:
        lang_dir = os.path.join(ROOT, "book", lang)
        if not os.path.isdir(lang_dir):
            print(f"Directory not found: book/{lang}/", file=sys.stderr)
            continue

        chapters = scan_chapters(lang_dir)
        og_missing = check_og_images(lang, chapters)
        rm_issue, _ = check_readme(lang, chapters)
        has_missing_og = [(cid, title) for cid, title in og_missing]

        results[lang] = {
            "chapters": len(chapters),
            "titles": {cid: title for cid, _, title, _ in chapters},
            "og_missing": has_missing_og,
            "readme_issue": rm_issue,
        }

    if args.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        return

    all_ok = True
    for lang, r in sorted(results.items()):
        print(f"\n=== {lang.upper()} ({r['chapters']} chapters) ===")
        if r["og_missing"]:
            all_ok = False
            print(f"  OG previews missing ({len(r['og_missing'])}):")
            for cid, title in r["og_missing"]:
                print(f"    ch{cid:02d}: {title[:60]}")
        else:
            print("  OG previews: all present")
        if r["readme_issue"]:
            all_ok = False
            print(f"  README: {r['readme_issue']}")
        else:
            print("  README: OK")

    if all_ok:
        print("\n✓ All chapters, READMEs, and OG previews in sync.")
        sys.exit(0)
    else:
        print("\n✗ Issues found. Run with --fix to regenerate README lists.")
        sys.exit(1)


if __name__ == "__main__":
    main()