"""Task 1 RED-tests: project config, unit paths, verdict store, text normalisation.

Run: cd ~/github/HowToLiveBetter && python3 -m unittest tools.validate.tests.test_common -v
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.pipeline import config as pconfig  # noqa: E402
from tools.pipeline import store as pstore    # noqa: E402
from tools.validate import common as vcommon  # noqa: E402


class TestProjectConfig(unittest.TestCase):
    def test_load_config_languages_and_judge(self):
        cfg = pconfig.load_config(ROOT)
        self.assertEqual(cfg["languages"], ["ru", "en"])
        self.assertEqual(cfg["judge"]["model_id"], "glm-5.3-flash")

    def test_lang_rules_skeleton_keys(self):
        for lang in ("ru", "en"):
            rules = pconfig.load_lang_rules(lang, root=ROOT)
            for key in ("labels", "banned_calques", "style_markers", "whitelist_zones"):
                self.assertIn(key, rules, f"{lang}.{key} missing")

    def test_cn_units_dir_exists_ch01(self):
        self.assertTrue(os.path.isdir(pconfig.unit_dir(ROOT, "cn", 1)))

    def test_wave_units_dir_ru_ch01(self):
        self.assertEqual(pconfig.unit_dir(ROOT, "ru", 1), "/root/htlb-run-ru/01/units")

    def test_unknown_lang_raises(self):
        with self.assertRaises(ValueError):
            pconfig.unit_dir(ROOT, "es", 1)


class TestVerdictStore(unittest.TestCase):
    def test_norm_text_filters_service_lines(self):
        text = "Заголовок\n\n§TAG§\n§SRC§\nтекст  с   пробелами\n"
        self.assertEqual(pstore.norm_text(text), "Заголовок\nтекст с пробелами")

    def test_unit_sha256_is_bytes_hash(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".md", delete=False) as f:
            f.write(b"abc")
        try:
            import hashlib
            self.assertEqual(
                pstore.unit_sha256(f.name),
                hashlib.sha256(b"abc").hexdigest(),
            )
        finally:
            os.unlink(f.name)

    def test_payload_has_audit_fields(self):
        src = os.path.join(ROOT, "tools", "digest", "01", "units", "00.md")
        payload = pstore.build_payload(
            tool="validate.judge", mode="screen", model_id="glm-5.3-flash",
            prompt="PROMPT", unit_path=src,
            verdict={"verdict": "native", "issues": []},
        )
        for key in ("tool", "mode", "model_id", "ts", "prompt_hash", "unit_sha256", "verdict"):
            self.assertIn(key, payload)
        self.assertEqual(payload["unit_sha256"], pstore.unit_sha256(src))
        self.assertEqual(payload["prompt_hash"], pstore.hash_prompt("PROMPT"))

    def test_write_read_verdict_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"verdict": {"verdict": "native"}, "model_id": "m"}
            path = pstore.write_verdict(tmp, "01", "ru", "00", payload)
            self.assertTrue(os.path.isfile(path))
            self.assertIn(os.path.join("tools", "judge", "01", "ru", "00.json"), path)
            self.assertEqual(pstore.read_verdict(path)["model_id"], "m")


class TestValidateCommon(unittest.TestCase):
    def test_load_unit_cn(self):
        text = vcommon.load_unit(ROOT, 1, "cn", "01")
        self.assertIn("§SRC§", text)  # body units keep the source placeholder

    def test_load_book_ru_ch01(self):
        text = vcommon.load_book(ROOT, 1, "ru")
        self.assertIn("Не умирайте рано", text[:400])  # chapter title in header zone
        self.assertGreater(len(text), 500)

    def test_unit_sha256_reexport(self):
        self.assertIs(vcommon.unit_sha256, pstore.unit_sha256)


if __name__ == "__main__":
    unittest.main()
