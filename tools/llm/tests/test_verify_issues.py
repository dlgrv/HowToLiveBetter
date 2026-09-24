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

    def test_cn_context_enriched_per_unit_shared_fail_unmutated(self):
        """cn_context is attached PER UNIT on a copy: two units mapping the
        same value must each get the anchor line from THEIR OWN CN text, and
        the shared fail dict must stay unmutated (repair_unit serializes the
        per-unit list into --issues-json; a mutated shared dict would leak
        unit A's anchor into unit B's prompt)."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text("### 7.\n- 收益：线A 61万人\n", encoding="utf-8")
            (dig / "08.md").write_text("### 8.\n- 收益：线B 61万人\n", encoding="utf-8")
            (tr / "07.md").write_text("### 7.\n- Эффект: нет\n", encoding="utf-8")
            (tr / "08.md").write_text("### 8.\n- Эффект: нет\n", encoding="utf-8")
            fail = {"kind": "number_absent", "value": "610000", "count": 2}
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr, fails=[fail],
            )
            self.assertEqual(located["07"][0]["cn_context"], "- 收益：线A 61万人")
            self.assertEqual(located["08"][0]["cn_context"], "- 收益：线B 61万人")
            self.assertNotIn("cn_context", fail)

    def test_value_in_other_tr_unit_does_not_suppress_own_unit_attach(self):
        """TR unit 08 holding the value must not mask unit 07's own cn>tr
        deficit: matched is computed per unit BEFORE the chapter-wide
        fallback (which is the only place a TR hit anywhere suppresses)."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text("### 7.\n- 收益：61万人\n", encoding="utf-8")
            (dig / "08.md").write_text("### 8.\n- 收益：别的\n", encoding="utf-8")
            (tr / "07.md").write_text("### 7.\n- Эффект: много людей\n", encoding="utf-8")
            (tr / "08.md").write_text("### 8.\n- Эффект: 610 000 человек\n", encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "610000", "count": 1}],
            )
            self.assertIn("07", located)
            self.assertNotIn("_unlocated", located)

    def test_missing_tr_unit_failsafe_matches_on_cn(self):
        """TR unit file missing entirely (partial translation output): the
        cn>tr comparison must still match via tr_counters.get(u, Counter())
        — a missing TR side is maximal deficit, never a skip."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text("### 7.\n- 收益：61万人\n", encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "number_absent", "value": "610000", "count": 1}],
            )
            self.assertIn("07", located)

    def test_calque_spread_single_occurrences_attaches_all(self):
        """Stem spread as 1+1+1 across units (chapter count 3): no unit has
        >1, so the count>1 fallback attaches EVERY unit containing the stem.
        Pins the locator/assert granularity: the assert allows ≤1 gloss PER
        UNIT while verify.py fails >1 PER CHAPTER (tools/verify.py:380-387)
        — convergence then relies on the repair prompt's 'prefer replacing
        ALL of them'; worst case is EXHAUSTED, never a false-green."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "14.md").write_text("### 14.\n", encoding="utf-8")
            (tr / "14.md").write_text("популяция одна\n", encoding="utf-8")
            (tr / "15.md").write_text("популяция две\n", encoding="utf-8")
            (tr / "16.md").write_text("популяция три\n", encoding="utf-8")
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr,
                fails=[{"kind": "banned_calque", "stem": "популяц", "count": 3}],
            )
            self.assertEqual(sorted(located), ["14", "15", "16"])


class IssuesStillPresent(unittest.TestCase):
    def test_accepts_space_grouped_and_nbsp_thousands(self):
        """The assert works in norm_numbers value-space: «610 000» (plain
        space), NBSP-grouped and bare «610000» all count as value 610000."""
        from tools.llm.verify_issues import issues_still_present
        issue = {"kind": "number_absent", "value": "610000"}
        for text in ("610 000 человек", "610\u00a0000 человек", "610000 человек"):
            self.assertEqual(issues_still_present(text, [issue], "ru"), [],
                             msg=f"failed on: {text!r}")

    def test_value_via_scale_word_counts(self):
        """The assert works in the same value-space as verify: «61 тысяча»
        folds to 61000 (not 610000!) — i.e. a wrong-scale «61 тысяча» left in
        the text correctly still counts the 610000 value as absent, and the
        repair prompt's scale table (万 = ×10,000) is what prevents it."""
        from tools.llm.verify_issues import issues_still_present
        issue = {"kind": "number_absent", "value": "610000"}
        self.assertEqual(
            issues_still_present("61 тысяча человек", [issue], "ru"),
            ["number 610000 still absent"])

    def test_calque_single_gloss_passes_assert(self):
        """≤1 stem occurrence per unit passes the assert (one first-use
        gloss allowed) — per-UNIT granularity, by design (see the
        chapter-wide caveat on the spread test above)."""
        from tools.llm.verify_issues import issues_still_present
        issue = {"kind": "banned_calque", "stem": "популяц"}
        self.assertEqual(
            issues_still_present("в популяции (population) вирус", [issue], "ru"), [])

    def test_unlocated_fail_dict_not_enriched(self):
        """_unlocated carries the raw fail (no cn_context — there is no unit
        to anchor it to)."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dig = Path(d) / "digest"
            tr = Path(d) / "tr"
            dig.mkdir()
            tr.mkdir()
            (dig / "07.md").write_text("### 7.\n- 收益：61 万人\n", encoding="utf-8")
            (tr / "07.md").write_text("### 7.\n- Эффект: много людей\n", encoding="utf-8")
            fail = {"kind": "number_absent", "value": "999", "count": 1}
            located = locate_issues(
                root=Path(d), nn="01", lang="ru",
                digest_units_dir=dig, tr_units_dir=tr, fails=[fail],
            )
            self.assertNotIn("cn_context", located["_unlocated"][0])
            self.assertNotIn("cn_context", fail)

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
