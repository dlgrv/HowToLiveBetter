import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from tools.llm import client
from tools.llm.translate_unit import (
    out_dir_is_under_digest,
    refuse_digest_outdir,
)
from tools.test_paths import REPO_ROOT


class TestLLMClient(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_chat_ok(self):
        os.environ["HTLB_LLM_BASE_URL"] = "http://127.0.0.1:8080/v1"
        os.environ["HTLB_LLM_MODEL"] = "test-model"
        os.environ["HTLB_LLM_API_KEY"] = "local"
        payload = {
            "choices": [{"message": {"content": " translated unit "}}],
        }
        resp = io.BytesIO(json.dumps(payload).encode("utf-8"))

        def fake_urlopen(req, timeout=0):
            assert timeout is not None  # urllib always passes timeout=
            self.assertIn("/chat/completions", req.full_url)
            self.assertEqual(req.get_header("Authorization"), "Bearer local")
            return mock.Mock(
                getcode=lambda: 200, read=resp.read, __enter__=lambda s: s, __exit__=mock.Mock()
            )

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            out = client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(out, "translated unit")

    def test_chat_empty_content_raises(self):
        os.environ["HTLB_LLM_BASE_URL"] = "http://127.0.0.1:8080/v1"
        os.environ["HTLB_LLM_MODEL"] = "m"
        os.environ["HTLB_LLM_API_KEY"] = "k"
        payload = {"choices": [{"message": {"content": "   "}}]}
        resp = io.BytesIO(json.dumps(payload).encode("utf-8"))

        def fake_urlopen(_req, timeout=0):
            assert timeout is not None
            return mock.Mock(
                getcode=lambda: 200, read=resp.read, __enter__=lambda s: s, __exit__=mock.Mock()
            )

        with (
            mock.patch("urllib.request.urlopen", fake_urlopen),
            self.assertRaises(client.LLMError) as ctx,
        ):
            client.chat([{"role": "user", "content": "x"}])
        self.assertIn("empty", str(ctx.exception).lower())

    def test_missing_env_raises(self):
        os.environ.pop("HTLB_LLM_BASE_URL", None)
        os.environ["HTLB_LLM_MODEL"] = "m"
        os.environ["HTLB_LLM_API_KEY"] = "k"
        with mock.patch.object(client, "load_dotenv"), self.assertRaises(client.LLMError):
            client.chat([{"role": "user", "content": "x"}])

    def test_chat_explicit_overrides_omit_bearer(self):
        for key in ("HTLB_LLM_BASE_URL", "HTLB_LLM_MODEL", "HTLB_LLM_API_KEY"):
            os.environ.pop(key, None)
        payload = {"choices": [{"message": {"content": "hi"}}]}
        resp = io.BytesIO(json.dumps(payload).encode("utf-8"))

        def fake_urlopen(req, timeout=0):
            self.assertEqual(timeout, 120)
            self.assertEqual(req.full_url, "http://127.0.0.1:11434/v1/chat/completions")
            self.assertIsNone(req.get_header("Authorization"))
            return mock.Mock(
                getcode=lambda: 200, read=resp.read, __enter__=lambda s: s, __exit__=mock.Mock()
            )

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            out = client.chat(
                [{"role": "user", "content": "x"}],
                base_url="http://127.0.0.1:11434/v1",
                model="llama",
                api_key=None,
                temperature=0.0,
                timeout=120,
            )
        self.assertEqual(out, "hi")


class TestTranslateUnitPaths(unittest.TestCase):
    def test_refuse_digest_outdir(self):
        root = Path(REPO_ROOT)
        digest_child = root / "tools" / "digest" / "01"
        self.assertTrue(out_dir_is_under_digest(digest_child, root))
        with self.assertRaises(SystemExit):
            refuse_digest_outdir(digest_child, root)

    def test_allow_runs_outdir(self):
        root = Path(REPO_ROOT)
        runs = root / "tools" / "runs" / "smoke" / "ru" / "01"
        self.assertFalse(out_dir_is_under_digest(runs, root))
        refuse_digest_outdir(runs, root)


if __name__ == "__main__":
    unittest.main()
