"""Task 8 tests: factcheck orchestrator — grounding discipline (plan Task 8).

Programmatic grounding: every cn_span in a judge verdict MUST appear
literally in the CN unit body (§SRC§/来源 service lines excluded). Ungrounded
verdicts are discarded, not repaired. Live judge calls are wave-runner work
(Task 9); everything here uses mock verdicts.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.validate import factcheck as fc  # noqa: E402

CN_UNIT = """# 第 1 章 立即停止这些行为

### 1. 戒烟——越早越好

<!-- 成本标签: 钱=0 时间=少 毅力=是 收益=大 口径=死亡率 -->

- 成本：戒烟期间的意志力（几周到几个月）
- 说人话：吸烟者平均比不吸烟者少活十年以上；40 岁前戒烟可以消除约 90% 的额外死亡风险。
- 收益：美国观察性研究：现在吸烟者的预期寿命比从不吸烟者短 10 年以上。
- 证据等级：A
- 来源：Jha P 等 (2013). 21st-century hazards of smoking. NEJM. <https://doi.org/10.1056/NEJMsa1211128>
- 备注：二手烟同样致命。

§SRC§: book/cn/01-*.md L12-31
"""

GOOD_VERDICT = {
    "assertions": [
        {"claim": "40 岁前戒烟消除约 90% 额外风险",
         "cn_span": "40 岁前戒烟可以消除约 90% 的额外死亡风险",
         "status": "ok"},
        {"claim": "预期寿命短 10 年以上",
         "cn_span": "现在吸烟者的预期寿命比从不吸烟者短 10 年以上",
         "status": "ok"},
    ],
    "unverifiable": [],
}

FAKE_SPAN_VERDICT = {
    "assertions": [
        {"claim": "戒烟降低 95% 风险",
         "cn_span": "戒烟可以将死亡风险降低 95%",  # NOT in the CN unit
         "status": "ok"},
    ],
    "unverifiable": [],
}

SERVICE_SPAN_VERDICT = {
    "assertions": [
        {"claim": "источник NEJM 2013",
         "cn_span": "来源：Jha P 等 (2013)",  # service line (来源 / §SRC§)
         "status": "ok"},
    ],
    "unverifiable": [],
}


class TestGrounding(unittest.TestCase):
    def test_cn_body_filters_service_lines(self):
        body = fc.cn_body(CN_UNIT)
        self.assertIn("90%", body)
        self.assertNotIn("来源：", body)
        self.assertNotIn("§SRC§", body)
        self.assertNotIn("成本标签", body)

    def test_good_verdict_fully_grounded(self):
        report = fc.check_grounding(GOOD_VERDICT, CN_UNIT)
        self.assertTrue(report["grounded"])
        self.assertEqual(report["dropped"], [])

    def test_fake_span_dropped(self):
        report = fc.check_grounding(FAKE_SPAN_VERDICT, CN_UNIT)
        self.assertFalse(report["grounded"])
        self.assertEqual(len(report["dropped"]), 1)
        self.assertIn("95%", report["dropped"][0]["assertion"]["cn_span"])
        self.assertEqual(report["dropped"][0]["reason"], "span_not_found")

    def test_service_line_span_dropped(self):
        report = fc.check_grounding(SERVICE_SPAN_VERDICT, CN_UNIT)
        self.assertFalse(report["grounded"])
        self.assertEqual(report["dropped"][0]["reason"], "service_line")

    def test_grounded_rate(self):
        verdicts = [GOOD_VERDICT, GOOD_VERDICT, FAKE_SPAN_VERDICT]
        self.assertAlmostEqual(fc.grounded_rate(verdicts, CN_UNIT), 2 / 3)


class TestPersist(unittest.TestCase):
    def test_write_result_has_audit_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fc.write_result(
                tmp, nn="01", lang="ru", verdict=GOOD_VERDICT,
                cn_text=CN_UNIT, tr_text="- Простыми словами: тест",
                backend="mock", model_id="mock-1")
            data = json.load(open(path, encoding="utf-8"))
            self.assertEqual(data["chapter"], "01")
            self.assertEqual(data["lang"], "ru")
            self.assertIn("unit_sha256", data)
            self.assertIn("ts", data)
            self.assertTrue(data["grounding"]["grounded"])
            self.assertEqual(data["backend"], "mock")


if __name__ == "__main__":
    unittest.main()
