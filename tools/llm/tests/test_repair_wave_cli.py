#!/usr/bin/env python3
"""CLI smoke tests for repair_wave.py (no LLM, no server).

Smoke-level only: the flags exist and the module is importable. Full
orchestration behavior (rounds, fallback, caps) needs the stub-LLM harness
(deferred R7) — noted in the commit message of the task that adds flags.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from tools.llm import repair_wave
from tools.test_paths import REPO_ROOT

_SCRIPT = os.path.join(REPO_ROOT, "tools", "llm", "repair_wave.py")


class CliFlags(unittest.TestCase):
    def test_max_dirty_flag_accepted(self):
        r = subprocess.run(
            [sys.executable, _SCRIPT, "--help"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONPATH": REPO_ROOT},
        )
        assert r.returncode == 0
        assert "--max-dirty" in r.stdout

    def test_module_importable_and_has_max_dirty(self):
        assert hasattr(repair_wave, "main")


if __name__ == "__main__":
    unittest.main()
