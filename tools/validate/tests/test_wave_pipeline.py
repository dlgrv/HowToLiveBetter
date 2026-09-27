"""Smoke test for tools/wave_pipeline.py main() (mocked assemble + verify)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import wave_pipeline
from tools.test_paths import REPO_ROOT


def _setup_temp_repo(tmp: str) -> None:
    """Minimal REPO mirror: chapter paths, project.json, active run units/."""
    rules_src = os.path.join(REPO_ROOT, "tools", "rules")
    rules_dst = os.path.join(tmp, "tools", "rules")
    os.makedirs(rules_dst, exist_ok=True)
    shutil.copy2(os.path.join(rules_src, "project.json"), os.path.join(rules_dst, "project.json"))
    shutil.copy2(
        os.path.join(REPO_ROOT, "tools", "langs.json"),
        os.path.join(tmp, "tools", "langs.json"),
    )

    stub = "# 2. stub\n\nMinimal chapter for wave_pipeline smoke test.\n"
    for lang in ("ru", "en", "es"):
        lang_dir = os.path.join(tmp, "book", lang)
        os.makedirs(lang_dir, exist_ok=True)
        with open(os.path.join(lang_dir, "02-stub.md"), "w", encoding="utf-8") as f:
            f.write(stub)

    for lang in ("ru", "en", "es"):
        units = os.path.join(tmp, "tools", "runs", "active", lang, "02", "units")
        os.makedirs(units, exist_ok=True)
        with open(os.path.join(units, "01.md"), "w", encoding="utf-8") as f:
            f.write("### 1. stub unit\n")


class TestWavePipelineMain(unittest.TestCase):
    def test_ch02_all_langs_green_with_mocked_subprocess(self):
        real_run = subprocess.run
        assemble_calls: list[list[str]] = []
        verify_calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            argv = [str(c) for c in cmd]
            joined = " ".join(argv)
            if joined.endswith("assemble.py") or "assemble.py" in joined:
                assemble_calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, stdout="OK\n", stderr="")
            if "verify.py" in joined:
                verify_calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, stdout="OK\n", stderr="")
            return real_run(cmd, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            _setup_temp_repo(tmp)

            with (
                patch.object(wave_pipeline, "REPO", tmp),
                patch.object(wave_pipeline.subprocess, "run", side_effect=fake_run),
            ):
                rc = wave_pipeline.main(["02"])

        self.assertEqual(rc, 0)
        self.assertEqual(len(assemble_calls), 3)
        self.assertEqual(len(verify_calls), 3)
        langs_assembled = {c[-1] for c in assemble_calls}
        langs_verified = {c[c.index("--lang") + 1] for c in verify_calls}
        self.assertEqual(langs_assembled, {"ru", "en", "es"})
        self.assertEqual(langs_verified, {"ru", "en", "es"})


if __name__ == "__main__":
    unittest.main()
