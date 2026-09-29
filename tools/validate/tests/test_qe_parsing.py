"""Task 3 tests: QE output parsing, tau computation, SKIPPED degradation.

The COMET stack only runs on the Mac (venv ~/.venvs/qe); everything tested
here is offline-pure: parsing fixed output samples and threshold math.
"""

import os
import unittest

import pytest
from tools.pipeline import qe as pqe
from tools.test_paths import REPO_ROOT


class TestOutputParsing(unittest.TestCase):
    RUNNER_SAMPLE = (
        "Predicting DataLoader 0: 100%|##########| 2/2 [00:01<00:00]\n"
        '{"scores": [0.8123, -0.1050]}\n'
    )

    def test_parse_runner_json(self):
        self.assertEqual(pqe.parse_scores(self.RUNNER_SAMPLE), [0.8123, -0.105])

    def test_parse_garbage_returns_none(self):
        self.assertIsNone(pqe.parse_scores("total garbage"))

    def test_parse_tolerates_progress_noise(self):
        noisy = self.RUNNER_SAMPLE.replace("0.8123", "0.8123", 1)
        self.assertEqual(pqe.parse_scores(noisy)[-1], -0.105)


class TestTau(unittest.TestCase):
    def test_floor(self):
        self.assertEqual(pqe.compute_tau(sigma=0.0), 0.01)

    def test_three_sigma(self):
        assert pqe.compute_tau(sigma=0.005) == pytest.approx(0.015)
        assert pqe.compute_tau(sigma=0.02) == pytest.approx(0.06)


class TestConfig(unittest.TestCase):
    def test_load_qe_config(self):
        cfg = pqe.load_qe_config(REPO_ROOT)
        self.assertEqual(cfg["model"], "Unbabel/wmt20-comet-qe-da")
        self.assertIn("max_tokens_per_segment", cfg)

    def test_project_json_backend_matches(self):
        import json

        proj = json.load(
            open(os.path.join(REPO_ROOT, "tools", "rules", "project.json"), encoding="utf-8")
        )
        self.assertEqual(proj["qe"]["model"], pqe.load_qe_config(REPO_ROOT)["model"])


class TestSkippedDegradation(unittest.TestCase):
    def test_venv_python_is_path_or_none(self):
        exe = pqe.venv_python(REPO_ROOT)
        self.assertTrue(exe is None or isinstance(exe, str))

    def test_run_scores_without_venv_raises_unavailable(self):
        if pqe.venv_python(REPO_ROOT) is not None:
            self.skipTest("qe venv present on this machine")
        with self.assertRaises(pqe.QeUnavailableError):
            pqe.run_scores([{"src": "你好", "mt": "Привет"}], root=REPO_ROOT)

    def test_noise_report_skipped_shape(self):
        from tools.validate.research import qe_noise

        report = qe_noise.build_report(root=REPO_ROOT, force_skip=True)
        self.assertEqual(report["status"], "skipped")
        self.assertIn("reason", report)


if __name__ == "__main__":
    unittest.main()
