"""Task 1 RED-tests: project config, unit paths, verdict store, text normalisation.

Run: cd ~/github/HowToLiveBetter && python3 -m unittest tools.validate.tests.test_common -v
"""

import os
import shutil
import tempfile
import unittest

from tools.pipeline import config as pconfig
from tools.pipeline import store as pstore
from tools.test_paths import REPO_ROOT


class TestProjectConfig(unittest.TestCase):
    def test_load_config_languages_and_judge(self):
        cfg = pconfig.load_config(REPO_ROOT)
        self.assertNotIn("languages", cfg)
        self.assertEqual(cfg["judge"]["model_id"], "glm-5.3-flash")

    def test_translation_vs_site_langs(self):
        site = pconfig.site_langs(REPO_ROOT)
        tr = pconfig.translation_langs(REPO_ROOT)
        self.assertIn("zh", site)
        self.assertNotIn("zh", tr)
        self.assertNotIn("cn", tr)
        self.assertEqual(set(tr), {"en", "ru", "es"})
        self.assertTrue(set(tr).issubset(set(site)))

    def test_lang_rules_skeleton_keys(self):
        for lang in ("ru", "en", "es"):
            rules = pconfig.load_lang_rules(lang, root=REPO_ROOT)
            for key in ("labels", "banned_calques", "style_markers", "whitelist_zones"):
                self.assertIn(key, rules, f"{lang}.{key} missing")

    def test_cn_units_dir_path_ch01(self):
        expected = os.path.join(REPO_ROOT, "tools", "digest", "01", "units")
        self.assertEqual(pconfig.unit_dir(REPO_ROOT, "cn", 1), expected)

    def test_wave_units_dir_ru_ch01(self):
        expected = os.path.join(REPO_ROOT, "tools", "runs", "active", "ru", "01", "units")
        self.assertEqual(pconfig.unit_dir(REPO_ROOT, "ru", 1), expected)

    def test_wave_units_dir_es_ch01(self):
        expected = os.path.join(REPO_ROOT, "tools", "runs", "active", "es", "01", "units")
        self.assertEqual(pconfig.unit_dir(REPO_ROOT, "es", 1), expected)

    def test_unknown_lang_raises(self):
        with self.assertRaises(ValueError):
            pconfig.unit_dir(REPO_ROOT, "xx", 1)

    def test_missing_langs_json_empty_and_unit_dir_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = os.path.join(tmp, "tools", "rules")
            os.makedirs(rules)
            shutil.copy2(
                os.path.join(REPO_ROOT, "tools", "rules", "project.json"),
                os.path.join(rules, "project.json"),
            )
            self.assertEqual(pconfig.load_langs(tmp), [])
            self.assertEqual(pconfig.translation_langs(tmp), [])
            with self.assertRaises(ValueError) as ctx:
                pconfig.unit_dir(tmp, "ru", 1)
            self.assertIn("unknown language", str(ctx.exception))


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
        with tempfile.NamedTemporaryFile("wb", suffix=".md", delete=False) as f:
            f.write(b"unit body")
            src = f.name
        try:
            payload = pstore.build_payload(
                tool="validate.judge",
                mode="screen",
                model_id="glm-5.3-flash",
                prompt="PROMPT",
                unit_path=src,
                verdict={"verdict": "native", "issues": []},
            )
            for key in (
                "tool",
                "mode",
                "model_id",
                "ts",
                "prompt_hash",
                "unit_sha256",
                "verdict",
            ):
                self.assertIn(key, payload)
            self.assertEqual(payload["unit_sha256"], pstore.unit_sha256(src))
        finally:
            os.unlink(src)

    def test_write_read_verdict_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"verdict": {"verdict": "native"}, "model_id": "m"}
            path = pstore.write_verdict(tmp, "01", "ru", "00", payload)
            self.assertTrue(os.path.isfile(path))
            self.assertIn(os.path.join("tools", "judge", "01", "ru", "00.json"), path)
            self.assertEqual(pstore.read_verdict(path)["model_id"], "m")


if __name__ == "__main__":
    unittest.main()
