#!/usr/bin/env python3
"""polish_wave: clarity loop mocked (no Laya, no LLM)."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from translate.llm.tests.helpers import run_cli
from translate.steps.polish import polish_wave
from translate.test_paths import REPO_ROOT

_OK_VERIFY = (0, {"ok": True})
_FAIL_VERIFY = (1, {"ok": False, "fails": [{"kind": "number_absent", "value": "1", "count": 1}]})


def _stub_run(_cmd):
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


def _workdir_with_unit(parent: Path) -> tuple[Path, Path]:
    workdir = parent / "run"
    units = workdir / "units"
    units.mkdir(parents=True)
    (units / "01.md").write_text(
        "- **Ходи.**\n- Простыми словами: Ходьба снижает риск.\n- Эффект: HR 0.8.\n",
        encoding="utf-8",
    )
    assembled = parent / "assembled.md"
    assembled.write_text("# stub assembled\n", encoding="utf-8")
    return workdir, assembled


def _main_args(workdir: Path, assembled: Path, *, max_rounds: int | None = None) -> list[str]:
    argv = [
        "--nn",
        "01",
        "--lang",
        "ru",
        "--workdir",
        str(workdir),
        "--assembled",
        str(assembled),
    ]
    if max_rounds is not None:
        argv.extend(["--max-rounds", str(max_rounds)])
    return argv


class PolishWaveClarityLoop(unittest.TestCase):
    def test_all_plain_exit_zero_no_simplify(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            workdir, assembled = _workdir_with_unit(Path(d))
            with (
                patch.object(polish_wave, "score_units", return_value=([], [], 0)),
                patch.object(polish_wave, "simplify_unit") as mock_simp,
                redirect_stdout(buf := io.StringIO()),
            ):
                rc = polish_wave.main(_main_args(workdir, assembled))
            self.assertEqual(rc, 0)
            mock_simp.assert_not_called()
            self.assertIn("CLARITY_OK", buf.getvalue())

    def test_max_rounds_leftover_exit_zero(self) -> None:
        always_dirty = (["01"], [{"unit": "01", "verdict": "непонятно"}], 0)
        with tempfile.TemporaryDirectory() as d:
            workdir, assembled = _workdir_with_unit(Path(d))
            with (
                patch.object(polish_wave, "score_units", return_value=always_dirty),
                patch.object(polish_wave, "simplify_unit", return_value=0),
                patch.object(polish_wave, "_run", side_effect=_stub_run),
                patch.object(polish_wave, "run_verify_json", return_value=_OK_VERIFY),
                redirect_stdout(buf := io.StringIO()),
            ):
                rc = polish_wave.main(_main_args(workdir, assembled, max_rounds=2))
            self.assertEqual(rc, 0)
            self.assertIn("LEFTOVER", buf.getvalue())

    def test_laya_down_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            workdir, assembled = _workdir_with_unit(Path(d))
            with (
                patch.object(polish_wave, "score_units", return_value=([], [], 2)),
                redirect_stderr(err := io.StringIO()),
            ):
                rc = polish_wave.main(_main_args(workdir, assembled))
            self.assertEqual(rc, 2)
            self.assertIn("LAYA_DOWN", err.getvalue())

    def test_verify_fail_after_simplify_exit_one_run_repair(self) -> None:
        dirty_once = (["01"], [], 0)
        with tempfile.TemporaryDirectory() as d:
            workdir, assembled = _workdir_with_unit(Path(d))
            with (
                patch.object(polish_wave, "score_units", return_value=dirty_once),
                patch.object(polish_wave, "simplify_unit", return_value=0),
                patch.object(polish_wave, "_run", side_effect=_stub_run),
                patch.object(polish_wave, "run_verify_json", return_value=_FAIL_VERIFY),
                redirect_stderr(err := io.StringIO()),
            ):
                rc = polish_wave.main(_main_args(workdir, assembled, max_rounds=3))
            self.assertEqual(rc, 1)
            self.assertIn("RUN_REPAIR", err.getvalue())

    def test_simplify_calls_bounded_by_max_rounds(self) -> None:
        always_dirty = (["01"], [], 0)
        max_rounds = 3
        with tempfile.TemporaryDirectory() as d:
            workdir, assembled = _workdir_with_unit(Path(d))
            with (
                patch.object(polish_wave, "score_units", return_value=always_dirty),
                patch.object(polish_wave, "simplify_unit", return_value=0) as mock_simp,
                patch.object(polish_wave, "_run", side_effect=_stub_run),
                patch.object(polish_wave, "run_verify_json", return_value=_OK_VERIFY),
            ):
                polish_wave.main(_main_args(workdir, assembled, max_rounds=max_rounds))
            self.assertLessEqual(mock_simp.call_count, max_rounds * 1)

    def test_dry_score_prints_json(self) -> None:
        cards = [{"line_no": 2, "verdict": "понятно", "text": "Ходьба снижает риск."}]
        with tempfile.TemporaryDirectory() as d:
            workdir, assembled = _workdir_with_unit(Path(d))
            with (
                patch.object(polish_wave, "score_lines", return_value=cards),
                redirect_stdout(buf := io.StringIO()),
            ):
                rc = polish_wave.main(
                    [*_main_args(workdir, assembled), "--dry-score"],
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["dirty"], [])
            self.assertEqual(payload["exit"], 0)
            self.assertEqual(len(payload["cards"]), 1)

    def test_polish_wave_script_importable_via_repo_root(self) -> None:
        """Sanity: run_cli can invoke polish_wave --help from REPO_ROOT."""
        r = run_cli(
            [
                sys.executable,
                str(Path(REPO_ROOT) / "translate" / "steps" / "polish" / "polish_wave.py"),
                "--help",
            ]
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("--dry-score", r.stdout)


if __name__ == "__main__":
    unittest.main()
