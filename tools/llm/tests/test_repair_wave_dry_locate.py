#!/usr/bin/env python3
"""repair_wave --dry-locate: verify JSON mocked, locate_issues on temp units (no LLM)."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.llm import repair_wave
from tools.llm.tests.helpers import run_cli
from tools.test_paths import REPO_ROOT

_FAKE_FAIL_REPORT = {
    "ok": False,
    "fails": [{"kind": "number_absent", "value": "610000", "count": 1}],
}


class DryLocateNumberAbsent(unittest.TestCase):
    def test_dry_locate_prints_unit_for_610000(self):
        with tempfile.TemporaryDirectory() as d:
            workdir = Path(d) / "run"
            units = workdir / "units"
            units.mkdir(parents=True)
            digest = Path(d) / "digest_units"
            digest.mkdir()
            (digest / "07.md").write_text(
                "### 7. x\n- 收益：把 123 项试验、61 万余人合起来\n",
                encoding="utf-8",
            )
            (units / "07.md").write_text(
                "### 7. x\n- Эффект: 123 испытания, 61 тысяча человек\n",
                encoding="utf-8",
            )
            assembled = Path(d) / "assembled.md"
            assembled.write_text("# stub assembled\n", encoding="utf-8")

            with (
                patch.object(repair_wave, "run_verify_json", return_value=(1, _FAKE_FAIL_REPORT)),
                patch.object(repair_wave, "unit_dir", return_value=str(digest)),
                redirect_stdout(buf := io.StringIO()),
            ):
                rc = repair_wave.main(
                    [
                        "--nn",
                        "02",
                        "--lang",
                        "ru",
                        "--workdir",
                        str(workdir),
                        "--assembled",
                        str(assembled),
                        "--dry-locate",
                    ]
                )

            self.assertEqual(rc, 0)
            located = json.loads(buf.getvalue())
            self.assertIn("07", located)
            self.assertEqual(located["07"][0]["value"], "610000")

    def test_repair_wave_script_importable_via_repo_root(self):
        """Sanity: run_cli can invoke repair_wave --help from REPO_ROOT."""
        import sys

        r = run_cli(
            [sys.executable, str(Path(REPO_ROOT) / "tools" / "llm" / "repair_wave.py"), "--help"]
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("--dry-locate", r.stdout)


if __name__ == "__main__":
    unittest.main()
