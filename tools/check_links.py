#!/usr/bin/env python3
"""Repo-wide markdown link checker for user-facing content.

Scope: root *.md, book/**, docs/** — everything a reader can open on GitHub
or the site. tools/ is excluded: tools/digest/*/units mirror source snippets
whose relative links resolve at assembly time (byte-identity required by
TRANSLATION.md), and tools/validate/results are QA logs, not reader content.

Every relative link target is resolved FROM THE FILE'S directory (not repo
root — resolving from root is how a broken docs/en/ -> ../核实记录 link once
passed a naive check). Links inside fenced code blocks (``` / ~~~) and
inline code spans are skipped: they are examples, not real links.

Exit codes: 0 = clean, 1 = broken links found.
"""
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK = re.compile(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "data:", "#")
SCOPE_DIRS = ("book", "docs")


def md_files():
    out = [os.path.join(ROOT, f) for f in sorted(os.listdir(ROOT))
           if f.endswith(".md") and os.path.isfile(os.path.join(ROOT, f))]
    for d in SCOPE_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in (".git", "node_modules")]
            for name in filenames:
                if name.endswith(".md"):
                    out.append(os.path.join(dirpath, name))
    return sorted(out)


def effective_text(path):
    """Strip code fences and inline code spans — links there are examples."""
    text = open(path, encoding="utf-8").read()
    text = FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text


def check():
    broken = []
    files = md_files()
    for path in files:
        rel = os.path.relpath(path, ROOT)
        base = os.path.dirname(path)
        for m in LINK.finditer(effective_text(path)):
            target = m.group(1).strip().lstrip("<").rstrip(">")
            if target.startswith(SKIP_PREFIXES):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = urllib.parse.unquote(
                os.path.normpath(os.path.join(base, target))
            )
            if not os.path.exists(resolved):
                broken.append((rel, target, os.path.relpath(resolved, ROOT)))
    return files, broken


def main():
    files, broken = check()
    print(f"checked {len(files)} markdown files (scope: root, book/, docs/)")
    if broken:
        print(f"BROKEN LINKS: {len(broken)}")
        for rel, target, resolved in broken:
            print(f"  {rel} -> {target} (resolved: {resolved})")
        return 1
    print("all relative links resolve: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
