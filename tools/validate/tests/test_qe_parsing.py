"""Task 3 tests: QE output parsing, tau computation, SKIPPED degradation.

The COMET stack only runs on the Mac (venv ~/.venvs/qe); everything tested
here is offline-pure: parsing fixed output samples and threshold math.
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.pipeline import qe as pqe  # noqa: E402


class TestOutputParsing(unittest.TestCase):
    RUNNER_SAMPLE = (
        "Predicting DataLoader 0: 100%|##########| 2/2 [00:01<00:00]\n"
        '{"scores": [0.8123, -0.1050]}\n'
    )
    CLI_SAMPLE = (
        "Some progress bar noise...\n"
        "wmt20-comet-qe-da: 0.8123\n"
    )

    def test_parse_runner_json(self):
        self.assertEqual(pqe.parse_scores(self.RUNNER_SAMPLE), [0.8123, -0.105])

    def test_parse_comet_cli_line(self):
        self.assertEqual(pqe.parse_comet_cli(self.CLI_SAMPLE), 0.8123)

    def test_parse_garbage_returns_none(self):
        self.assertIsNone(pqe.parse_scores("total garbage"))
        self.assertIsNone(pqe.parse_comet_cli("no numbers here"))

    def test_parse_tolerates_progress_noise(self):
        noisy = self.RUNNER_SAMPLE.replace("0.8123", "0.8123", 1)
        self.assertEqual(pqe.parse_scores(noisy)[-1], -0.105)


class TestTau(unittest.TestCase):
    def test_floor(self):
        self.assertEqual(pqe.compute_tau(sigma=0.0), 0.01)

    def test_three_sigma(self):
        self.assertAlmostEqual(pqe.compute_tau(sigma=0.005), 0.015)
        self.assertAlmostEqual(pqe.compute_tau(sigma=0.02), 0.06)


class TestConfig(unittest.TestCase):
    def test_load_qe_config(self):
        cfg = pqe.load_qe_config(ROOT)
        self.assertEqual(cfg["model"], "Unbabel/wmt20-comet-qe-da")
        self.assertIn("max_tokens_per_segment", cfg)

    def test_project_yaml_backend_matches(self):
        import yaml
        proj = yaml.safe_load(open(os.path.join(ROOT, "tools", "rules", "project.yaml")))
        self.assertEqual(proj["qe"]["model"], pqe.load_qe_config(ROOT)["model"])


class TestSkippedDegradation(unittest.TestCase):
    def test_available_is_bool(self):
        self.assertIsInstance(pqe.available(ROOT), bool)

    def test_run_scores_without_venv_raises_unavailable(self):
        if pqe.available(ROOT):
            self.skipTest("qe venv present on this machine")
        with self.assertRaises(pqe.QeUnavailable):
            pqe.run_scores([{"src": "你好", "mt": "Привет"}], root=ROOT)

    def test_noise_report_skipped_shape(self):
        from tools.validate import qe_noise
        report = qe_noise.build_report(root=ROOT, force_skip=True)
        self.assertEqual(report["status"], "skipped")
        self.assertIn("reason", report)


if __name__ == "__main__":
    unittest.main()
