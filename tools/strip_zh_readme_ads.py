#!/usr/bin/env python3
"""Remove upstream author ad block from README.zh.md after sync.

Upstream README.md ends with a 「广告位」 section linking ads/. This fork does
not carry ads/; strip that section whenever README.zh.md is refreshed from
upstream so the next sync does not reintroduce it.
"""

from __future__ import annotations

import re
import sys

ADS_SECTION_RE = re.compile(
    r"\n## 广告位\n.*\Z",
    re.DOTALL,
)


def strip_ads(text: str) -> str:
    return ADS_SECTION_RE.sub("\n", text).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: strip_zh_readme_ads.py README.zh.md", file=sys.stderr)
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        original = f.read()
    cleaned = strip_ads(original)
    if cleaned != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print("stripped ads section from", path)
    else:
        print("no ads section in", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
