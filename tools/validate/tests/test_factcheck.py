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

    def test_substring_service_marker_not_dropped(self):
        # 出资来源 = "source of funds" — 来源 inside body text is NOT a service line
        unit = CN_UNIT + "- 成本：按出资来源和比例判归一方并合理补偿\n"
        verdict = {"assertions": [
            {"claim": "дележ по источнику средств",
             "cn_span": "按出资来源和比例判归一方并合理补偿", "status": "ok"}]}
        report = fc.check_grounding(verdict, unit)
        self.assertTrue(report["grounded"], report["dropped"])

    def test_grounded_rate(self):
        verdicts = [GOOD_VERDICT, GOOD_VERDICT, FAKE_SPAN_VERDICT]
        self.assertAlmostEqual(fc.grounded_rate(verdicts, CN_UNIT), 2 / 3)


class TestMajorGate(unittest.TestCase):
    def test_major_class_fails(self):
        for t in ("reversed_logic", "invented", "dropped_condition"):
            v = {"assertions": [{"claim": "c", "cn_span": "40 岁前戒烟可以消除约 90% 的额外死亡风险",
                                 "status": "issue", "issue_type": t}]}
            self.assertEqual(fc.gate_major(v)["gate"], "fail", t)

    def test_minor_class_warns_only(self):
        v = {"assertions": [{"claim": "c", "cn_span": "x", "status": "issue",
                             "issue_type": "softened_claim"}]}
        self.assertEqual(fc.gate_major(v)["gate"], "warn")

    def test_clean_passes(self):
        self.assertEqual(fc.gate_major(GOOD_VERDICT)["gate"], "pass")


class TestMutationEndToEnd(unittest.TestCase):
    """Plan Task 8: Task-4 mutations must be catchable end-to-end (gate logic)."""

    def test_spec_mutations_classify(self):
        spec = json.load(open(os.path.join(
            ROOT, "tools", "validate", "results", "mutations_seed42.json"),
            encoding="utf-8"))
        caught = sum(1 for m in spec["mutations"]
                     if fc.gate_major({"assertions": [
                         {"claim": "c", "cn_span": "x", "status": "issue",
                          "issue_type": m["issue_type"]}]}).get("gate") == "fail")
        # dropped_condition / reversed_logic / invented are major; the rest warn
        self.assertGreaterEqual(caught, 8)  # deterministic type assignment: >=8 of 30


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


class TestGateRobustness(unittest.TestCase):
    """Expert-review fixes: broken judge output must not read as clean."""

    def test_unparseable_verdict_gates_error(self):
        v = {"parse_error": True, "raw_reply": "..."}
        self.assertEqual(fc.gate_major(v)["gate"], "error")

    def test_missing_assertions_gates_error(self):
        self.assertEqual(fc.gate_major({"note": "truncated"})["gate"], "error")

    def test_prompt_schema_mapped_to_status(self):
        # verdict per committed prompt (ru_ok/en_ok, no status): must NOT
        # silently pass — ru_ok=False is a major issue
        v = {"assertions": [{"claim": "c", "cn_span": "不要空腹服药",
                             "ru_ok": False, "en_ok": True,
                             "issue_type": "dropped_condition"}]}
        self.assertEqual(fc.gate_major(v)["gate"], "fail")
        ok = {"assertions": [{"claim": "c", "cn_span": "每天至少30分钟",
                              "ru_ok": True, "en_ok": True, "issue_type": None}]}
        self.assertEqual(fc.gate_major(ok)["gate"], "pass")

    def test_hardened_claim_is_major(self):
        v = {"assertions": [{"claim": "c", "cn_span": "一般不超过",
                             "status": "issue", "issue_type": "hardened_claim"}]}
        self.assertEqual(fc.gate_major(v)["gate"], "fail")

    def test_ellipsis_span_grounds(self):
        # 30-ru-02 / 13-ru-19 class: judge quotes with … between fragments
        verdict = {"assertions": [
            {"claim": "в двух фрагментах", "status": "ok",
             "cn_span": "说人话：吸烟者平均比不吸烟者少活十年以上……40 岁前戒烟可以消除约 90%"}]}
        report = fc.check_grounding(verdict, CN_UNIT)
        self.assertTrue(report["grounded"], report["dropped"])

    def test_multiline_span_touching_service_line_dropped(self):
        verdict = {"assertions": [
            {"claim": "span crosses into service line", "status": "ok",
             "cn_span": "- 收益：美国观察性研究：现在吸烟者的预期寿命比从不吸烟者短 10 年以上。\n- 证据等级：A"}]}
        report = fc.check_grounding(verdict, CN_UNIT)
        self.assertFalse(report["grounded"])
        self.assertEqual(report["dropped"][0]["reason"], "service_line")

    def test_unsupported_claim_dropped(self):
        verdict = {"assertions": [
            {"claim": "c", "status": "ok",
             "cn_span": "40 岁前戒烟可以消除约 90% 的额外死亡风险",
             "span_supports_claim": False}]}
        report = fc.check_grounding(verdict, CN_UNIT)
        self.assertFalse(report["grounded"])
        self.assertEqual(report["dropped"][0]["reason"], "span_does_not_support_claim")


class TestFactcheckCliExit(unittest.TestCase):
    def test_gate_fail_exits_nonzero(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cn = os.path.join(td, "cn.md")
            tr = os.path.join(td, "tr.md")
            with open(cn, "w", encoding="utf-8") as f:
                f.write("说人话：测试\n")
            with open(tr, "w", encoding="utf-8") as f:
                f.write("Простыми словами: тест\n")
            fail_verdict = json.dumps({
                "unit": "1",
                "assertions": [{
                    "claim": "flipped",
                    "cn_span": "测试",
                    "status": "issue",
                    "issue_type": "reversed_logic",
                }],
            })
            proc = subprocess.run(
                [sys.executable, "-m", "tools.validate.factcheck",
                 "--chapter", "01", "--lang", "ru",
                 "--cn-unit", cn, "--tr-unit", tr,
                 "--stdin-verdict", fail_verdict,
                 "--outdir", td],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn('"gate": "fail"', proc.stdout)

    def test_clean_mock_exits_zero(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cn = os.path.join(td, "cn.md")
            tr = os.path.join(td, "tr.md")
            with open(cn, "w", encoding="utf-8") as f:
                f.write("说人话：测试\n")
            with open(tr, "w", encoding="utf-8") as f:
                f.write("Простыми словами: тест\n")
            ok = json.dumps({"unit": "1", "assertions": [], "issues": []})
            proc = subprocess.run(
                [sys.executable, "-m", "tools.validate.factcheck",
                 "--chapter", "01", "--lang", "ru",
                 "--cn-unit", cn, "--tr-unit", tr,
                 "--stdin-verdict", ok,
                 "--outdir", td],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('"gate": "pass"', proc.stdout)
            self.assertIn('"grounded": true', proc.stdout)

    def test_ungrounded_exits_nonzero(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cn = os.path.join(td, "cn.md")
            tr = os.path.join(td, "tr.md")
            with open(cn, "w", encoding="utf-8") as f:
                f.write("说人话：测试\n")
            with open(tr, "w", encoding="utf-8") as f:
                f.write("Простыми словами: тест\n")
            bad = json.dumps({
                "unit": "1",
                "assertions": [{
                    "claim": "fake",
                    "cn_span": "этого текста нет в китайском юните",
                    "status": "ok",
                }],
            })
            proc = subprocess.run(
                [sys.executable, "-m", "tools.validate.factcheck",
                 "--chapter", "01", "--lang", "ru",
                 "--cn-unit", cn, "--tr-unit", tr,
                 "--stdin-verdict", bad,
                 "--outdir", td],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn('"grounded": false', proc.stdout)

    def test_no_verdict_exits_2(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cn = os.path.join(td, "cn.md")
            tr = os.path.join(td, "tr.md")
            with open(cn, "w", encoding="utf-8") as f:
                f.write("说人话：测试\n")
            with open(tr, "w", encoding="utf-8") as f:
                f.write("Простыми словами: тест\n")
            env = os.environ.copy()
            for k in ("ZAI_API_KEY", "Z_AI_API_KEY", "ZHIPUAI_API_KEY"):
                env.pop(k, None)
            proc = subprocess.run(
                [sys.executable, "-m", "tools.validate.factcheck",
                 "--chapter", "01", "--lang", "ru",
                 "--cn-unit", cn, "--tr-unit", tr,
                 "--outdir", td],
                capture_output=True, text=True, cwd=ROOT, env=env)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("judge_unavailable", proc.stdout)


class TestLiveJudgeWiring(unittest.TestCase):
    def test_build_judge_prompt_includes_cn_and_tr(self):
        prompt = fc.build_judge_prompt(
            "说人话：四十岁前戒烟。\n- 来源：ignore\n",
            "- Простыми словами: бросить курить.\n§TAG§\n",
            "ru",
        )
        self.assertIn("CHINESE SOURCE", prompt)
        self.assertIn("四十岁前戒烟", prompt)
        self.assertIn("бросить курить", prompt)
        tr_part = prompt.split("## TRANSLATION", 1)[-1]
        self.assertNotIn("§TAG§", tr_part)
        self.assertNotIn("- 来源：", prompt.split("## CHINESE SOURCE", 1)[-1].split("## TRANSLATION")[0])

    def test_live_judge_mocked_writes_and_exits_0(self):
        import subprocess
        import tempfile
        from unittest import mock

        ok = {"assertions": [], "issues": []}
        with tempfile.TemporaryDirectory() as td:
            cn = os.path.join(td, "cn.md")
            tr = os.path.join(td, "tr.md")
            with open(cn, "w", encoding="utf-8") as f:
                f.write("说人话：测试\n")
            with open(tr, "w", encoding="utf-8") as f:
                f.write("Простыми словами: тест\n")

            seen = []

            class FakeClient:
                def complete(self, prompt, system=None, temperature=0.0, max_tokens=2048):
                    seen.append(prompt)
                    return json.dumps(ok)

            fake = FakeClient()
            with mock.patch.object(fc, "open_live_judge", return_value=(fake, "subagent-glm", "mock-glm")):
                code = fc.run_factcheck_cli(
                    chapter="01",
                    lang="ru",
                    cn_unit=cn,
                    tr_unit=tr,
                    outdir=td,
                    stdin_verdict=None,
                )
            self.assertEqual(code, 0)
            self.assertTrue(seen and "测试" in seen[0])
            written = os.path.join(td, "01-ru.json")
            self.assertTrue(os.path.isfile(written))
            data = json.load(open(written, encoding="utf-8"))
            self.assertEqual(data["backend"], "subagent-glm")
            self.assertEqual(data["model_id"], "mock-glm")


if __name__ == "__main__":
    unittest.main()
