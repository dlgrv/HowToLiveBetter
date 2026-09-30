"""Empty glossary must not compile RegExp('').

PT README shipped without a glossary table; parseGlossary still built
GLOSS_RE = new RegExp('', 'g'), and termify then matched every offset on
~2MB of chapter text — the /pt/ page looked like infinite loading.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from translate.lib.config import default_root

ROOT = Path(default_root())
INDEX = ROOT / "site" / "index.html"


class TestGlossaryEmptyGuard(unittest.TestCase):
    def test_empty_parts_sets_gloss_re_null(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r"GLOSS_RE\s*=\s*parts\.length\s*\?\s*new RegExp\(parts\.join\('\|'\),\s*'g'\)\s*:\s*null",
            "parseGlossary must not compile RegExp('') when the glossary table is empty",
        )

    def test_not_unconditional_empty_regexp(self):
        text = INDEX.read_text(encoding="utf-8")
        # The old hang: GLOSS_RE = new RegExp(parts.join('|'), 'g') with no parts.length guard.
        bad = re.search(
            r"GLOSS_RE\s*=\s*new RegExp\(parts\.join\('\|'\),\s*'g'\)\s*;",
            text,
        )
        self.assertIsNone(bad, "unconditional RegExp(parts.join) regresses the empty-glossary hang")


if __name__ == "__main__":
    unittest.main()
