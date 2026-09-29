"""Unit tests for Laya questions + triage (mocked HTTP; no live server)."""

from __future__ import annotations

import io
import unittest
from unittest import mock

from tools.laya import questions, triage


class TestQuestions(unittest.TestCase):
    def test_three_labels_covered(self) -> None:
        self.assertEqual(len(questions.TRIAGE_LABELS), 3)
        for label in questions.TRIAGE_LABELS:
            qs = questions.questions_for_label(label)
            self.assertIsNotNone(qs)
            assert qs is not None
            self.assertIn("verdict", qs)
            self.assertEqual(qs["verdict"]["type"], "choice")
            self.assertEqual(
                set(qs["verdict"]["criteria"]),
                {"bug", "ok", "unclear"},
            )

    def test_unknown_label(self) -> None:
        self.assertIsNone(questions.questions_for_label("причастная цепочка"))

    def test_interpret_choice(self) -> None:
        self.assertEqual(
            questions.interpret_answer(
                {"answers": {"verdict": {"type": "choice", "answer": "bug"}}}
            ),
            "bug",
        )
        self.assertEqual(questions.interpret_answer(None), "unclear")


class TestTriage(unittest.TestCase):
    SAMPLE = "# t\n\n- Простыми словами: Согласно законом штраф неизбежен.\n- Примечания: ok\n"

    def test_server_down_skip(self) -> None:
        fake_findings = [
            {
                "label": "согласно-творительный",
                "line_no": 3,
                "span": "Согласно законом",
                "zone": "body",
            }
        ]
        with (
            mock.patch("tools.laya.triage.check_text", return_value=fake_findings),
            mock.patch("tools.laya.client.healthz", return_value=None),
        ):
            cards = triage.triage_text(self.SAMPLE, "ru", base_url="http://127.0.0.1:1")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["verdict"], "skip_server_down")

    def test_predict_bug(self) -> None:
        fake_findings = [
            {
                "label": "этих-вместо-данных",
                "line_no": 3,
                "span": "этих исследований",
                "zone": "body",
            }
        ]
        payload = {"answers": {"verdict": {"type": "choice", "answer": "bug", "confidence": 0.8}}}
        with (
            mock.patch("tools.laya.triage.check_text", return_value=fake_findings),
            mock.patch("tools.laya.client.healthz", return_value={"ok": True}),
            mock.patch("tools.laya.client.systemone", return_value=payload) as sys1,
        ):
            cards = triage.triage_text(self.SAMPLE, "ru", base_url="http://127.0.0.1:8090")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["verdict"], "bug")
        self.assertEqual(sys1.call_args.kwargs["model"], "multilingual")

    def test_filters_non_triage_labels(self) -> None:
        fake_findings = [{"label": "причастная цепочка", "line_no": 1, "span": "x", "zone": "body"}]
        with mock.patch("tools.laya.triage.check_text", return_value=fake_findings):
            cards = triage.triage_text(self.SAMPLE, "ru")
        self.assertEqual(cards, [])

    def test_main_apply_warns_and_exits_zero(self) -> None:
        err = io.StringIO()
        with (
            mock.patch("sys.stderr", err),
            mock.patch("tools.laya.triage.triage_file", return_value=[]),
        ):
            code = triage.main(
                [
                    "--lang",
                    "ru",
                    "--apply",
                    "--base-url",
                    "http://127.0.0.1:1",
                    "chapter.md",
                ]
            )
        self.assertEqual(code, 0)
        self.assertIn("reserved", err.getvalue())


if __name__ == "__main__":
    unittest.main()
