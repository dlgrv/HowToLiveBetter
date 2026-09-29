#!/usr/bin/env python3
"""Deprecated shim — use tools/style_check.py --book --lang <lang> [--strict].

Kept so older Makefile/docs invocations keep working for one release.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from tools.style_check import main as style_main

    args = list(sys.argv[1:] if argv is None else argv)
    # Legacy: bureaucratese.py [lang] [--dir D] [--json] [--strict]
    lang = "ru"
    rest: list[str] = []
    if args and not args[0].startswith("-"):
        lang = args[0]
        args = args[1:]
    rest = ["--book", "--lang", lang, *args]
    print(
        "WARN: tools/bureaucratese.py is deprecated; "
        f"use: python3 tools/style_check.py --book --lang {lang} …",
        file=sys.stderr,
    )
    return style_main(rest)


if __name__ == "__main__":
    sys.exit(main())
