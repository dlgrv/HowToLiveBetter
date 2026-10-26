#!/usr/bin/env python3
"""Generate .publish/updates.json — per-item add/change history from git.

Only the Chinese source chapters (book/NN-*.md) are tracked: they are the
content of record, and item ids (sec-n) are shared across locales by the
PARITY gate. Locale translation churn is not surfaced as content updates.

Output shape (consumed by the site "fresh" chips, ?upd=added|changed&days=N):

  {"generated": "YYYY-MM-DD",
   "items": {"1-14": {"added": "2026-10-01",
                      "changed": "2026-10-14",
                      "fields": ["gain", "notes"]}}}

"added" is the date the item first appeared after the import commit (the
single oldest commit that introduced the chapters); items already present in
that commit are baseline and carry no "added" — like upstream's manual
"since" cutoff. "changed"/"fields" reflect the last commit that altered the
item's title or any of its field lines.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime

ITEM_HEAD = re.compile(r"^### (\d+)\. +(.*)$", re.MULTILINE)
FIELD_LINE = re.compile(r"^- (成本|说人话|收益|证据等级|来源|备注)[：:](.*)$")
FIELD_NAMES = {
    "成本": "cost",
    "说人话": "plain",
    "收益": "gain",
    "证据等级": "grade",
    "来源": "sources",
    "备注": "notes",
}
# Canonical field order in the "fields" list.
FIELD_ORDER = ["title", "cost", "plain", "gain", "grade", "sources", "notes"]


def split_items(md: str) -> dict[str, str]:
    """Chapter markdown → {item number: block}, block spans to the next heading."""
    out: dict[str, str] = {}
    matches = list(ITEM_HEAD.finditer(md))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        out[m.group(1)] = md[m.start() : end]
    return out


def item_state(block: str) -> tuple[str, dict[str, str]]:
    """(title, per-field text) of one item block, whitespace-normalized."""
    head = ITEM_HEAD.search(block)
    title = head.group(2).strip() if head else ""
    fields: dict[str, str] = {}
    for line in block.splitlines():
        fm = FIELD_LINE.match(line)
        if fm:
            fields[FIELD_NAMES[fm.group(1)]] = fm.group(2).strip()
    return title, fields


def diff_items(old_md: str, new_md: str) -> dict:
    """Item-level diff of two revisions of one chapter."""
    old, new = split_items(old_md), split_items(new_md)
    changed = []
    for n in sorted(set(old) & set(new), key=int):
        ot, of = item_state(old[n])
        nt, nf = item_state(new[n])
        fields = []
        if ot != nt:
            fields.append("title")
        fields += [f for f in FIELD_ORDER[1:] if of.get(f) != nf.get(f)]
        if fields:
            changed.append({"n": n, "fields": fields})
    return {
        "added": sorted(set(new) - set(old), key=int),
        "removed": sorted(set(old) - set(new), key=int),
        "changed": changed,
    }


def _git(root: str, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=60, check=False
    )
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {out.stderr.strip()[:200]}")
    return out.stdout


def chapter_files(root: str) -> list[str]:
    """zh source chapters: book/NN-*.md at the top level of book/."""
    book = os.path.join(root, "book")
    return sorted(
        f"book/{name}" for name in os.listdir(book) if re.fullmatch(r"\d{2}-.+\.md", name)
    )


def collect_history(root: str) -> dict[str, dict]:
    """Walk git history of every zh chapter → {item id: {added?, changed?, fields?}}.

    Items present in the import commit (the single oldest commit that first
    introduced the chapters) are baseline: recorded without "added", exactly
    like upstream's manual "since" cutoff — otherwise the whole book would
    light up as "new" right after the fork import.
    """
    logs: dict[str, list[tuple[str, str]]] = {}
    for rel in chapter_files(root):
        out = _git(root, "log", "--reverse", "--format=%H%x01%cI", "--", rel).strip()
        if out:
            logs[rel] = [tuple(line.split("\x01", 1)) for line in out.splitlines()]
    if not logs:
        return {}

    dates = {h: d for lines in logs.values() for h, d in lines}
    import_hash = min({lines[0][0] for lines in logs.values()}, key=lambda h: dates[h])

    items: dict[str, dict] = {}
    for rel, lines in logs.items():
        sec = os.path.basename(rel)[:2]
        baseline = lines[0][0] == import_hash
        prev_md: str | None = None
        for commit, cdate in lines:
            date = cdate[:10]
            md = _git(root, "show", f"{commit}:{rel}")
            if prev_md is None:
                if not baseline:
                    for n in split_items(md):
                        items.setdefault(f"{sec}-{n}", {"added": date})
            else:
                d = diff_items(prev_md, md)
                for n in d["added"]:
                    items.setdefault(f"{sec}-{n}", {"added": date})
                for c in d["changed"]:
                    # Baseline items may get their first record here — no "added".
                    rec = items.setdefault(f"{sec}-{c['n']}", {})
                    rec["changed"] = date
                    rec["fields"] = c["fields"]
            prev_md = md
    return items


def write_updates(publish_dir: str, root: str) -> int:
    """Collect history and write <publish_dir>/updates.json. Never raises on git failure."""
    try:
        items = collect_history(root)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        print(f"updates: git history unavailable ({exc}); writing an empty feed")
        items = {}
    items = dict(sorted(items.items(), key=lambda kv: tuple(int(x) for x in kv[0].split("-"))))
    payload = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "items": items,
    }
    out = os.path.join(publish_dir, "updates.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(f"updates: {len(items)} items → {out}")
    return len(items)
