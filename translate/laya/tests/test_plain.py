"""Clarity pass — mock HTTP; no live Laya."""

from __future__ import annotations

import unittest
from unittest import mock

from translate.laya import plain, questions


class TestClarityQuestion(unittest.TestCase):
    def test_two_way(self) -> None:
        criteria = questions.CLARITY_QUESTIONS["clarity"]["criteria"]
        self.assertEqual(set(criteria), {"plain", "not_plain"})

    def test_interpret(self) -> None:
        self.assertEqual(
            questions.interpret_clarity(
                {"answers": {"clarity": {"type": "choice", "answer": "plain"}}}
            ),
            "понятно",
        )
        self.assertEqual(
            questions.interpret_clarity(
                {"answers": {"clarity": {"type": "choice", "answer": "not_plain"}}}
            ),
            "непонятно",
        )


class TestPlainLines(unittest.TestCase):
    def test_extracts_ru_plain_only(self) -> None:
        text = "- **Ходи.**\n- Простыми словами: Ходьба снижает риск.\n- Эффект: HR 0.8.\n"
        rows = plain.plain_terms_lines(text, "ru")
        self.assertEqual(len(rows), 1)
        self.assertIn("Ходьба", rows[0]["text"])

    def test_server_down_exit_two(self) -> None:
        lines = [{"line_no": 2, "text": "Ходьба снижает риск."}]
        with mock.patch("translate.laya.client.healthz", return_value=None):
            cards = plain.score_lines(lines, base_url="http://127.0.0.1:1")
        self.assertEqual(cards[0]["verdict"], "skip_server_down")
        self.assertEqual(plain.exit_code_for_cards(cards), 2)

    def test_not_plain_is_advisory(self) -> None:
        lines = [{"line_no": 2, "text": "В соответствии с вышеуказанным."}]
        payload = {"answers": {"clarity": {"type": "choice", "answer": "not_plain"}}}
        with (
            mock.patch("translate.laya.client.healthz", return_value={"ok": True}),
            mock.patch("translate.laya.client.systemone", return_value=payload),
        ):
            cards = plain.score_lines(lines, base_url="http://127.0.0.1:8090")
        self.assertEqual(cards[0]["verdict"], "непонятно")
        self.assertEqual(plain.exit_code_for_cards(cards), 0)


if __name__ == "__main__":
    unittest.main()
