"""Unit tests for tools.pipeline.paths helpers."""

import os
import unittest

from tools.pipeline.config import unit_dir
from tools.pipeline.paths import (
    _nn,
    active_run_dir,
    active_units_dir,
    digest_dir,
    digest_units_dir,
)
from tools.test_paths import ROOT


class TestNn(unittest.TestCase):
    def test_pads(self):
        self.assertEqual(_nn(2), "02")
        self.assertEqual(_nn("01"), "01")
        self.assertEqual(_nn("3"), "03")


class TestDigestPaths(unittest.TestCase):
    def test_digest_dir_pads(self):
        root = os.path.join("fake", "htlb-root")
        self.assertEqual(
            digest_dir(root, 2),
            os.path.join(root, "tools", "digest", "02"),
        )
        self.assertEqual(
            digest_units_dir(root, "1"),
            os.path.join(root, "tools", "digest", "01", "units"),
        )


class TestActiveRunPaths(unittest.TestCase):
    def test_active_delegates_to_unit_dir(self):
        self.assertEqual(active_units_dir(ROOT, "ru", 2), unit_dir(ROOT, "ru", 2))
        self.assertEqual(
            active_run_dir(ROOT, "ru", 2),
            os.path.dirname(unit_dir(ROOT, "ru", 2)),
        )
        self.assertEqual(
            active_units_dir(ROOT, "es", "3"),
            os.path.join(ROOT, "tools", "runs", "active", "es", "03", "units"),
        )


if __name__ == "__main__":
    unittest.main()
