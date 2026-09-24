#!/usr/bin/env python3
"""Tests for tools/llm/verify_issues.py — locator + JSON parsing (no LLM)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.llm.verify_issues import locate_issues, parse_verify_json  # noqa: E402


class Locate(unittest.TestCase):
    def test_maps_610000_to_unit_with_61_wan(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text(
                "### 7. x\n- 收益：把 123 项试验、61 万余人合起来\n", encoding="utf-8")
            # wrong-scale TR: «61 тысяча» = 61000, value 610000 truly absent
            (tr / "07.md").write_text(
                "### 7. x\n- Эффект: 123 испытания, 61 тысяча человек\n",
                encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "610000", "count": 1}],
            )
            self.assertIn("07", located)
            self.assertEqual(located["07"][0]["value"], "610000")

    def test_value_present_in_tr_not_attached(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text("### 7.\n- 收益：61 万人\n", encoding="utf-8")
            (tr / "07.md").write_text("### 7.\n- Эффект: 610 000 человек\n",
                                      encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "610000", "count": 1}],
            )
            self.assertNotIn("07", located)
            self.assertNotIn("_unlocated", located)

    def test_number_absent_duplicate_in_cn_locates_correctly(self):
        """CN has the value twice, TR has it once → per-unit deficit (cn>tr);
        locator must attach the unit — the set-based comparison silently
        swallowed this deficit (review A1 false-UNLOCATED bug)."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text(
                "### 7. x\n- 收益：61万人受益，另一组也有61万人\n", encoding="utf-8")
            (tr / "07.md").write_text(
                "### 7. x\n- Эффект: 610 000 человек\n", encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "610000", "count": 1}],
            )
            self.assertIn("07", located)
            self.assertEqual(located["07"][0]["value"], "610000")

    def test_calque_over_attach_only_offender_units(self):
        """count=3 with 2 occurrences in unit 14 and a legit single gloss in
        unit 15 → only the offending unit (own stem count > 1) is attached."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "14.md").write_text("### 14.\n", encoding="utf-8")
            (tr / "14.md").write_text("популяция растёт, популяция стареет\n",
                                      encoding="utf-8")
            (tr / "15.md").write_text("в популяции (population) вирус\n",
                                      encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "banned_calque", "stem": "популяц", "count": 3}],
            )
            self.assertIn("14", located)
            self.assertNotIn("15", located)

    def test_unlocated_when_no_cn_unit_matches(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text("### 7.\n- 收益：61 万人\n", encoding="utf-8")
            (tr / "07.md").write_text("### 7.\n- Эффект: много людей\n",
                                      encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "999", "count": 1}],
            )
            self.assertIn("_unlocated", located)

    def test_calque_stem_to_units(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "14.md").write_text("### 14.\n", encoding="utf-8")
            (tr / "14.md").write_text("в популяции вирус\n", encoding="utf-8")
            (tr / "15.md").write_text("Популяция растёт\n", encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "banned_calque", "stem": "популяц", "count": 2}],
            )
            self.assertIn("14", located)
            self.assertIn("15", located)

    def test_non_repairable_kinds_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[
                    {"kind": "headings_mismatch", "got": 1, "want": 2},
                    {"kind": "number_absent", "value": "0", "count": 1},
                ],
            )
            # "0" may not map anywhere in empty dirs → _unlocated at most;
            # headings_mismatch must never appear anywhere
            for unit, issues in located.items():
                for iss in issues:
                    self.assertNotEqual(iss["kind"], "headings_mismatch")


class ParseVerifyJson(unittest.TestCase):
    def test_last_object_line_wins(self):
        stdout = (
            "verify assembled.md vs src\n"
            "  WARN: numbers added (check) {\"kind\": \"x\"}\n"
            "FAIL\n"
            "  - numbers absent\n"
            '{"ok": false, "chapter": "01", "lang": "ru", "file": "f", '
            '"fails": [], "warns": []}\n'
        )
        data = parse_verify_json(stdout)
        self.assertIn("ok", data)
        self.assertEqual(data["chapter"], "01")

    def test_raises_when_no_json(self):
        with self.assertRaises(ValueError):
            parse_verify_json("no json here at all\n")


if __name__ == "__main__":
    unittest.main()
