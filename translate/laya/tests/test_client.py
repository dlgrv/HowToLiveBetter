"""Laya client — mock HTTP; never hit a live server in CI."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from typing import Self
from unittest import mock

from translate.laya import client as laya_client

FIX_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class TestLayaHealthz(unittest.TestCase):
    def test_health_up_via_health_path(self) -> None:
        body = json.dumps({"status": "ok", "device": "cpu"}).encode()

        def fake_urlopen(req, timeout=0):
            _ = timeout
            self.assertIn("/health", req.full_url)
            return _FakeResp(body)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            got = laya_client.healthz("http://127.0.0.1:8090", timeout=1.0)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got["status"], "ok")
        self.assertEqual(got["path"], "/health")

    def test_health_down_returns_none(self) -> None:
        got = laya_client.healthz("http://127.0.0.1:1", timeout=0.3)
        self.assertIsNone(got)


class TestLayaSystemone(unittest.TestCase):
    def test_mocked_round_trip(self) -> None:
        fixture = json.loads((FIX_DIR / "ru-data-noun-01.json").read_text(encoding="utf-8"))
        answer = {
            "answers": {
                "noun_or_demonstrative": {
                    "type": "choice",
                    "answer": "data_noun",
                    "confidence": 0.9,
                }
            },
            "usage": {"input_tokens": 12, "output_tokens": 0},
        }
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout=0):
            _ = timeout
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeResp(json.dumps(answer).encode())

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            got = laya_client.systemone(
                fixture["state"],
                fixture["questions"],
                base_url="http://127.0.0.1:8090",
                model="multilingual",
                timeout=1.0,
            )
        self.assertEqual(got, answer)
        self.assertEqual(captured["url"], "http://127.0.0.1:8090/v1/systemone")
        body = captured["body"]
        assert isinstance(body, dict)
        self.assertEqual(body["model"], "multilingual")

    def test_rejects_english_model(self) -> None:
        with self.assertRaises(laya_client.LayaError):
            laya_client.systemone(
                "x",
                {"q": {"type": "noul", "instructions": "yes?"}},
                model="english",
            )

    def test_server_down_returns_none(self) -> None:
        got = laya_client.systemone(
            "x",
            {"q": {"type": "noul", "instructions": "yes?"}},
            base_url="http://127.0.0.1:1",
            model="multilingual",
            timeout=0.3,
        )
        self.assertIsNone(got)


class TestLayaMainSkip(unittest.TestCase):
    def test_main_exits_zero_when_down(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stderr", buf):
            code = laya_client.main(["--base-url", "http://127.0.0.1:1", "--timeout", "0.3"])
        self.assertEqual(code, 0)
        self.assertIn("server_down", buf.getvalue())


class TestFixturesPresent(unittest.TestCase):
    def test_five_fixtures(self) -> None:
        files = sorted(FIX_DIR.glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        self.assertLessEqual(len(files), 5)
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("state", data)
            self.assertIn("questions", data)
            self.assertIn("expected", data)


if __name__ == "__main__":
    unittest.main()
