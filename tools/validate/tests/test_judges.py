"""Task 1 tests: judge backend registry (offline parts only; live calls smoke-tested in Task 2)."""

import unittest

from tools.pipeline import config as pipeline_config
from tools.pipeline import judges
from tools.test_paths import REPO_ROOT


class TestJudgeRegistry(unittest.TestCase):
    def test_default_backend_from_config(self):
        cfg = pipeline_config.load_config(REPO_ROOT).get("judge", {})
        self.assertEqual(cfg.get("backend", "subagent-glm"), "subagent-glm")

    def test_get_backend_known_names(self):
        for name in ("subagent-glm", "local-ollama"):
            self.assertEqual(judges.get_backend(name), name)

    def test_get_backend_unknown_raises(self):
        with self.assertRaises(ValueError):
            judges.get_backend("nope")

    def test_endpoint_zai_when_key(self):
        self.assertEqual(judges.endpoint("dummy"), judges.ZAI_BASE)

    def test_endpoint_ollama_without_key(self):
        self.assertEqual(judges.endpoint(None), judges.OLLAMA_BASE)

    def test_complete_sends_messages_through_chat(self):
        from unittest import mock

        with mock.patch("tools.pipeline.judges.chat", return_value="ok") as mocked:
            out = judges.complete("PROMPT", model_id="glm-5.3-flash", api_key="dummy", system="SYS")
        self.assertEqual(out, "ok")
        messages = mocked.call_args[0][0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], "PROMPT")
        self.assertEqual(mocked.call_args.kwargs["model"], "glm-5.3-flash")
        self.assertEqual(mocked.call_args.kwargs["base_url"], judges.ZAI_BASE)


if __name__ == "__main__":
    unittest.main()
