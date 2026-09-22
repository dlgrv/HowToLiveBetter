"""Tests for judge_blind_run: decode + parse + summary aggregation."""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) or ".", ""))

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from tools.validate.judge_blind_run import decode, parse_reply  # noqa: E402


class TestDecode(unittest.TestCase):
    def test_ab_slot1_is_a(self):
        self.assertEqual(decode("1", "AB"), "a")

    def test_ba_slot1_is_b(self):
        self.assertEqual(decode("1", "BA"), "b")

    def test_tie(self):
        self.assertEqual(decode("tie", "AB"), "tie")
        self.assertEqual(decode("=", "BA"), "tie")

    def test_unparsed(self):
        self.assertEqual(decode(None, "AB"), "unparsed")
        self.assertEqual(decode("maybe?", "AB"), "unparsed")


class TestParseReply(unittest.TestCase):
    def test_json_object(self):
        self.assertEqual(parse_reply('хм {"winner": "1", "reason": "r"}'), "1")

    def test_json_in_code_fence(self):
        self.assertEqual(parse_reply('```json\n{"winner": "tie"}\n```'), "tie")

    def test_no_json(self):
        self.assertIsNone(parse_reply("не понял вопрос"))


class TestSummaryShape(unittest.TestCase):
    def test_length_bias_counts(self):
        rows = [
            {"decoded": "a", "longer_is_a": True, "decoy": False, "pair_id": "g01"},
            {"decoded": "b", "longer_is_a": False, "decoy": False, "pair_id": "g01"},
            {"decoded": "b", "longer_is_a": False, "decoy": False, "pair_id": "g02"},
        ]
        dec = [r for r in rows if r["decoded"] != "tie"]
        picked = sum(1 for r in dec
                     if r["longer_is_a"] is not None
                     and ((r["decoded"] == "a") == r["longer_is_a"]))
        self.assertEqual(picked, 3)  # all three picked the longer side


if __name__ == "__main__":
    unittest.main()
