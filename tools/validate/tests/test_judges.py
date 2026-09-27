"""Task 1 tests: judge backend registry (offline parts only; live calls smoke-tested in Task 2)."""

import unittest

from tools.pipeline import judges
from tools.test_paths import ROOT


class TestJudgeRegistry(unittest.TestCase):
    def test_default_backend_from_config(self):
        self.assertEqual(judges.backend_name(ROOT), "subagent-glm")

    def test_get_backend_known_names(self):
        for name in ("subagent-glm", "local-ollama"):
            cls = judges.get_backend(name)
            self.assertTrue(callable(cls))

    def test_get_backend_unknown_raises(self):
        with self.assertRaises(ValueError):
            judges.get_backend("nope")

    def test_zai_client_builds_request(self):
        cls = judges.get_backend("subagent-glm")
        client = cls(model_id="glm-5.3-flash", api_key="dummy")
        url, _headers, body = client.build_request("PROMPT", system="SYS")
        self.assertIn("chat/completions", url)
        self.assertEqual(body["model"], "glm-5.3-flash")
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][1]["content"], "PROMPT")


if __name__ == "__main__":
    unittest.main()
