"""Published-book gates must stay green in `make test` (same as CI content step)."""

import unittest

from forge.ops import check_content


class CheckContentRepoTest(unittest.TestCase):
    def test_repo_content_gates_pass(self):
        self.assertEqual(check_content.main(), 0)
