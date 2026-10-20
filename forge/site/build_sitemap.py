#!/usr/bin/env python3
"""Generate sitemap.xml over the assembled .publish/ tree.

Called from forge/site/pages_artifact.py after staging, so the sitemap always
matches the real URL space (locale hubs, chapters, per-language READMEs).

URL scheme on https://book.dlgrv.com:

  /                    language router (site/index.html)   priority 1.0
  /<lang>/             locale hub (site/<lang>/index.html) priority 0.9
  /README*.md          per-language front matter            priority 0.8
  /book/**.md          chapters (zh at /book/, others in /book/<lang>/) 0.7
  /docs/research/**    linked research notes                priority 0.3

Everything else (assets/, login/, privacy/, useful/, robots.txt, llms*.txt,
sitemap.xml itself) is excluded.
"""

from __future__ import annotations

import os
import subprocess
import sys
from xml.sax.saxutils import escape

HOST = "https://book.dlgrv.com"

EXCLUDED_DIRS = {"assets", "login", "privacy", "useful"}
EXCLUDED_FILES = {"robots.txt", "llms.txt", "llms-full.txt", "sitemap.xml", "404.html"}
MAX_URLS = 50_000  # sitemap protocol limit per file


def _git_lastmod(root: str, candidates: list[str]) -> str | None:
    """Last commit date (W3C) for the first existing source of a published file."""
    for rel in candidates:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        try:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%cI", "--", rel],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
        return None
    return None


def _priority(rel: str, langs: list[str]) -> str:
    if rel == "index.html":
        return "1.0"
    parts = rel.split("/")
    if len(parts) == 2 and parts[0] in langs and parts[1] == "index.html":
        return "0.9"
    if parts[0] == "README.md" or (parts[0].startswith("README.") and rel.endswith(".md")):
        return "0.8"
    if parts[0] == "book":
        return "0.7"
    return "0.3"


def collect_urls(publish_dir: str, root: str, langs: list[str]) -> list[dict]:
    """Walk the publish tree and return sitemap entries sorted by URL."""
    entries: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(publish_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, publish_dir)
            if rel in EXCLUDED_FILES:
                continue
            if name.endswith(".md"):
                pass  # chapters, READMEs, research — all indexable
            elif rel.endswith("/index.html") or rel == "index.html":
                pass  # router + locale hubs
            else:
                continue  # non-content files (html subpages, misc)
            candidates = [rel, os.path.join("site", rel)]
            url_rel = "" if rel == "index.html" else rel
            if url_rel.endswith("/index.html"):
                url_rel = url_rel[: -len("index.html")]
            entries.append(
                {
                    "loc": f"{HOST}/{url_rel}",
                    "priority": _priority(rel, langs),
                    "lastmod": _git_lastmod(root, candidates),
                }
            )
    entries.sort(key=lambda e: e["loc"])
    return entries[:MAX_URLS]


def render_sitemap(entries: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for e in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(e['loc'])}</loc>")
        if e["lastmod"]:
            lines.append(f"    <lastmod>{e['lastmod']}</lastmod>")
        lines.append(f"    <priority>{e['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def write_sitemap(publish_dir: str, root: str, langs: list[str]) -> int:
    entries = collect_urls(publish_dir, root, langs)
    if not entries:
        sys.exit("sitemap: no URLs collected — refusing to write an empty sitemap")
    out_path = os.path.join(publish_dir, "sitemap.xml")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_sitemap(entries))
    print(f"sitemap: {len(entries)} urls → {out_path}")
    return len(entries)
