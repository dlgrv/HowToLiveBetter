#!/usr/bin/env python3
"""Adversarial edge-case tests for tools/verify.py norm_numbers and verify checks.

Written against the real source (not from memory). Convention:
  * PASSING tests = regression armor (documented current behavior that must not drift).
  * @unittest.expectedFailure tests = candidate REAL bugs, each with corpus
    relevance in the docstring; they fail today on purpose so the suite stays
    green while the bug is open. Remove the decorator when fixed.

Candidate bugs covered here (bug IDs used in the report):
  bug-01  Distributive-scale regex fires on mixed magnitudes:
          «100,000 to 1 million» → phantom 100000×million = 1e11 (EN, live in
          ch26/ch11; RU «от 500 до 1 тыс.» → 500000; ES «500 a 1000 mil»).
  bug-02  ES digit/bare «mil» loses ×1000 (scale key is 'mil ' with a trailing
          space, so end-of-string «20 mil» → [20]). Word-form «diez mil» → []
          pairs blindly against spelled CN 一万 — any CN digit re-render (1 万)
          flips es/02-style lines into a hard number_absent 10000.
  bug-04  EN "May"/ES "mayo" not folded while CN «5 月» is: date round-trip
          CN «2026 年 5 月 18 日» → EN «May 18, 2026» keeps 18/2026, drops 5.
          Masked in ch08 (chapter carries many genuine 5s); RU has a digit-
          anchored «мая» rule, so the language pack is inconsistent.
  bug-05  Bare RU scale nouns not folded: «тысяча», «полторы тысячи» → [],
          «полутора-двух часов» → [2] (half of the range). CN counterparts are
          blind too (一两小时 → []), so today this is extra-value WARN noise
          (live: ru ch02 heading 38) plus latent CN-digit drift risk.
  bug-07  RU/ES comma-thousands after a leading 0: «100,000» → [100] + phantom
          (the anti-zero lookbehind blocks the strip, then the decimal rule
          eats it). N00,000 magnitudes are common; corpus uses space-thousands
          today (1202 hits), so latent — but EN-style commas surviving in RU
          prose are explicitly supported («25,871 человек»).
  bug-09  Spelled numbers ≥13 not folded on either side: RU «тридцать»/
          «сто»/«двести-триста» → [], CN «两万/一万步/五百到一千» → [].
          Symmetric blindness keeps the gate green (armor), but every such
          line is one CN word-form edit away from a phantom number_absent.

Discarded false alarms (tested here as armor on purpose):
  * multi-comma thousands «2,263,888» → [2263888] in RU and EN (parses fine);
  * CN range with 万 on the last endpoint only («2000 到 2 万元» → [2000,
    20000]) — matches what TRs render; live chapters pass;
  * «9 мая» → [9, 5] round-trips exactly against CN «5 月 9 日»;
  * CN/EN-mode space-thousands («610 000» → ['610','0']) unreachable: the
    corpus only has it in 来源/Sources lines, which check 5 excludes;
  * fullwidth ％ is not in FULLWIDTH and never occurs in TR files;
  * EN modal "may" (422 hits) correctly NOT folded — pinning that is armor.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.verify import norm_numbers  # noqa: E402


def norm_cn(t):
    return norm_numbers(t)


def norm_ru(t):
    return norm_numbers(t, ru=True)


def norm_es(t):
    return norm_numbers(t, es=True)


def norm_en(t):
    return norm_numbers(t)


class DecimalsWithScales(unittest.TestCase):
    """Decimal mantissas × scale words — the corpus has 95 «N.N 万» + 20 «N.N 亿»."""

    def test_decimal_wan(self):
        self.assertEqual(norm_cn("65.4 万"), ["654000"])

    def test_decimal_wan_tight(self):
        self.assertEqual(norm_cn("3.85万"), ["38500"])

    def test_decimal_yi(self):
        self.assertEqual(norm_cn("86.5 亿"), ["8650000000"])

    def test_es_decimal_comma_millones(self):
        self.assertEqual(norm_es("1,38 millones"), ["1380000"])

    def test_es_decimal_comma_millones_heavy(self):
        self.assertEqual(norm_es("33,615 millones"), ["33615000"])

    def test_ru_decimal_comma_mlrd(self):
        self.assertEqual(norm_ru("8,65 млрд"), ["8650000000"])

    def test_ru_dot_decimal_mlrd_en_style(self):
        self.assertEqual(norm_ru("1.068 млрд"), ["1068000000"])

    def test_ru_decimal_comma_tys(self):
        self.assertEqual(norm_ru("65,4 тыс."), ["65400"])

    def test_ru_comma_thousands_before_mln(self):
        self.assertEqual(norm_ru("4,257 млн"), ["4257000"])

    def test_decimal_half_wan(self):
        self.assertEqual(norm_cn("0.5 万"), ["5000"])


class Ranges(unittest.TestCase):
    """«3 万到 10 万» is the corpus range shape (48 hits); RU/ES share one scale."""

    def test_cn_range_both_marked(self):
        self.assertEqual(norm_cn("3 万到 10 万"), ["30000", "100000"])

    def test_cn_range_zhi(self):
        self.assertEqual(norm_cn("1 万至 10 万"), ["10000", "100000"])

    def test_ru_distributive_do(self):
        self.assertEqual(norm_ru("от 81 до 138 тыс."), ["81000", "138000"])

    def test_ru_distributive_dash(self):
        self.assertEqual(norm_ru("30–50 тыс."), ["30000", "50000"])

    def test_ru_distributive_en_dash_no_spaces(self):
        self.assertEqual(norm_ru("30-50 тыс."), ["30000", "50000"])

    def test_en_distributive_and(self):
        self.assertEqual(norm_en("30 and 50 thousand"), ["30000", "50000"])

    def test_cn_range_scale_on_last_only(self):
        # Corpus shape (CN ch09 «罚 2000 到 2 万元»); the first endpoint stays
        # unscaled, which is exactly what TRs mirror. Armor, not a bug.
        self.assertEqual(norm_cn("2000 到 2 万元"), ["2000", "20000"])

    # bug-01 FIXED: mixed magnitudes no longer produce a phantom clone
    def test_en_mixed_magnitude_range(self):
        self.assertEqual(norm_en("100,000 to 1 million"), ["100000", "1000000"])

    def test_en_mixed_magnitude_range_500k(self):
        self.assertEqual(norm_en("500,000 to 2 million"), ["500000", "2000000"])

    def test_ru_mixed_magnitude_range(self):
        self.assertEqual(norm_ru("штраф от 500 до 1 тыс. юаней"), ["500", "1000"])

    def test_es_shared_scale_range(self):
        # ES «X a Y mil» shared-scale range (ch13 corpus shape)
        self.assertEqual(norm_es("500 a 1000 mil"), ["500000", "1000000"])

    def test_ru_same_scale_distributive_ok(self):
        # same-scale ranges must keep working (regression armor for bug-01 fix)
        self.assertEqual(norm_ru("от 2 тыс. до 10 тыс. юаней"), ["2000", "10000"])

    def test_es_same_scale_range_millones(self):
        # ES connector «a» is missing from the distributive separator set
        # (до|and|to|dash only) — «2 a 3 millones» scales one endpoint only.
        # Same family as bug-01 (ES distributive gaps); no live ES «N a N
        # millones» hits in the corpus today, but «500 a 1000 mil» exists (ch13).
        self.assertEqual(norm_es("de 2 a 3 millones"), ["2000000", "3000000"])


class Percent(unittest.TestCase):
    """1,170 '%' hits in CN; RU/ES render «N%» / «N %» alike."""

    def test_percent_plain(self):
        self.assertEqual(norm_cn("85%"), ["85"])

    def test_percent_ru_space(self):
        self.assertEqual(norm_ru("85 %"), ["85"])

    def test_percent_es(self):
        self.assertEqual(norm_es("20,5%"), ["20.5"])

    def test_percent_cn_fullwidth(self):
        # CN corpus has «5％»; FULLWIDTH class does not include ％, so check 6
        # ignores it (CN-side only, never rendered in TR). Armor.
        self.assertEqual(norm_cn("5％"), ["5"])


class ZeroNegative(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(norm_cn("0"), ["0"])

    def test_zero_ru_word(self):
        self.assertEqual(norm_ru("нулю"), ["0"])

    def test_zero_decimal_ru(self):
        self.assertEqual(norm_ru("0,001"), ["0.001"])

    def test_zero_decimal_en(self):
        self.assertEqual(norm_en("0.001"), ["0.001"])

    def test_minus_sign_dropped(self):
        # effect sizes «−0,495» occur in TR corpora; verify compares absolute
        # values, sign lost — pinned (both sides lose it, so counts still match).
        self.assertEqual(norm_ru("−0,495"), ["0.495"])

    def test_cn_zero_word(self):
        self.assertEqual(norm_cn("零"), [])

    def test_cn_ling_qian(self):
        self.assertEqual(norm_cn("零钱"), [])


class MixedDigitsCJK(unittest.TestCase):
    def test_yi_decimal(self):
        self.assertEqual(norm_cn("1.2亿"), ["120000000"])

    def test_wan_yi(self):
        self.assertEqual(norm_cn("2万亿"), ["2000000000000"])

    def test_multi_scale_yi_qianwan(self):
        # «3亿2千万» → two separate values (CN arithmetic is implicit addition;
        # verify's value-multiset design intentionally keeps them separate).
        self.assertEqual(norm_cn("3亿2千万"), ["300000000", "20000000"])

    def test_qianwan(self):
        self.assertEqual(norm_cn("3 千万"), ["30000000"])

    def test_baiwan(self):
        self.assertEqual(norm_cn("5 百万"), ["5000000"])

    def test_yu_after_wan(self):
        self.assertEqual(norm_cn("61 万余"), ["610000"])

    def test_yu_before_wan(self):
        self.assertEqual(norm_cn("61余万"), ["610000"])

    def test_yu_spaced(self):
        self.assertEqual(norm_cn("61 余万"), ["610000"])

    def test_trailing_ren_ci(self):
        # 万人/万人次/亿元 — trailing units must not disturb the scale fold
        self.assertEqual(norm_cn("4 万人"), ["40000"])
        self.assertEqual(norm_cn("10 万人次"), ["100000"])
        self.assertEqual(norm_cn("5 亿元"), ["500000000"])

    def test_qianyi_compound_scale_missing(self):
        # 千亿 = 1e11 — not in the scale table: «5千亿» folds 千 only.
        # No corpus hits (census 0) → armor test documenting current behavior.
        self.assertEqual(norm_cn("5千亿"), ["5000"])


class ThousandsSeparators(unittest.TestCase):
    def test_en_comma_thousands(self):
        self.assertEqual(norm_en("1,234,567"), ["1234567"])

    def test_ru_space_thousands(self):
        self.assertEqual(norm_ru("610 000"), ["610000"])

    def test_ru_space_thousands_chain(self):
        self.assertEqual(norm_ru("12 345 678"), ["12345678"])

    def test_ru_nbsp_thousands(self):
        self.assertEqual(norm_ru("610\u00a0000"), ["610000"])

    def test_es_narrow_nbsp_thousands(self):
        self.assertEqual(norm_es("610\u202f000"), ["610000"])

    def test_es_space_thousands(self):
        self.assertEqual(norm_es("48 478"), ["48478"])

    def test_ru_comma_thousands_2_groups(self):
        self.assertEqual(norm_ru("61,429"), ["61429"])

    def test_ru_comma_thousands_3_groups(self):
        # initially suspected broken; verified correct — armor
        self.assertEqual(norm_ru("2,263,888"), ["2263888"])

    def test_en_comma_thousands_4_groups(self):
        # initially suspected orphan tail; verified correct — armor
        self.assertEqual(norm_en("1,234,567,890"), ["1234567890"])

    def test_ru_comma_after_zero_is_decimal(self):
        self.assertEqual(norm_ru("0,891"), ["0.891"])

    # bug-07 FIXED: comma-thousands after a leading 0 in RU/ES
    def test_ru_comma_thousands_after_zero(self):
        self.assertEqual(norm_ru("100,000"), ["100000"])

    def test_es_comma_thousands_after_zero(self):
        # ES body comma is ALWAYS decimal (corpus census: thousands-commas live
        # only in «- Fuentes:» quote blocks, excluded by check 5). So «100,000»
        # parses as 100.0 — pinned, not a bug for ES (unlike RU).
        self.assertEqual(norm_es("100,000"), ["100"])

    def test_en_mode_space_thousands_current_behavior(self):
        # EN/CN mode has no space-thousands rule; corpus only ever has it in
        # Sources lines, which check 5 excludes → unreachable. Armor.
        self.assertEqual(norm_en("610 000"), ["610", "0"])

    def test_cn_mode_space_thousands_current_behavior(self):
        self.assertEqual(norm_cn("170 000"), ["170", "0"])


class UnicodeDigits(unittest.TestCase):
    """Full-width and Arabic-Indic digits never occur in the corpus (census 0),
    but Python's \\d matches them — armor tests pinning that they still fold."""

    def test_fullwidth_digits_wan(self):
        self.assertEqual(norm_cn("１０万"), ["100000"])

    def test_fullwidth_digits_alone(self):
        self.assertEqual(norm_cn("１２３"), ["123"])

    def test_arabic_indic_digits(self):
        self.assertEqual(norm_cn("١٢٣"), ["123"])

    def test_fullwidth_percent_not_in_class(self):
        from tools.verify import FULLWIDTH
        self.assertIsNone(FULLWIDTH.search("％"))


class WhitespaceVariants(unittest.TestCase):
    def test_wan_spaced_and_not(self):
        self.assertEqual(norm_cn("61 万"), norm_cn("61万"))

    def test_wan_nbsp(self):
        self.assertEqual(norm_cn("61\u00a0万"), ["610000"])

    def test_tys_no_dot(self):
        self.assertEqual(norm_ru("610 тыс"), ["610000"])

    def test_tys_dot(self):
        self.assertEqual(norm_ru("610 тыс."), ["610000"])

    def test_tys_glued_to_digits(self):
        self.assertEqual(norm_ru("100тыс"), ["100000"])


class RoundTrip(unittest.TestCase):
    """Same value through different language renderings must produce equal multisets."""

    def test_61wan_all_langs(self):
        vals = {
            frozenset(norm_cn("61万人")),
            frozenset(norm_ru("610 000 человек")),
            frozenset(norm_ru("610 тыс. человек")),
            frozenset(norm_en("610,000 people")),
        }
        self.assertEqual(len(vals), 1, vals)

    def test_654wan(self):
        self.assertEqual(norm_cn("65.4 万"), norm_ru("654 тыс."))

    def test_2yique(self):
        self.assertEqual(norm_cn("2 万亿"), norm_en("2 trillion"))

    def test_es_mil_millones(self):
        self.assertEqual(norm_es("20 mil millones"), norm_en("20 billion"))

    def test_es_mil_millon_singular(self):
        self.assertEqual(norm_es("1 mil millón"), ["1000000000"])

    def test_es_dot_thousands_not_supported_current_behavior(self):
        # ES dot-thousands «610.000» — not a corpus rendering (ES uses space
        # thousands); armor: pinned, not 610000.
        self.assertEqual(norm_es("610.000"), ["610"])

    # bug-02 FIXED: «N mil» digit+mil keeps the scale
    def test_es_digit_mil(self):
        self.assertEqual(norm_es("20 mil"), ["20000"])

    def test_es_digit_mil_with_noun(self):
        self.assertEqual(norm_es("20 mil personas"), ["20000"])

    def test_es_mil_millones_still_compound(self):
        self.assertEqual(norm_es("20 mil millones"), ["20000000000"])

    # bug-04: EN "May" not folded
    @unittest.expectedFailure
    def test_date_roundtrip_may(self):
        # CN «2026 年 5 月 18 日» vs EN «May 18, 2026» — CN yields 5, EN drops it.
        self.assertEqual(norm_cn("2026 年 5 月 18 日"), norm_en("May 18, 2026"))

    @unittest.expectedFailure
    def test_es_mayo_not_folded(self):
        self.assertEqual(norm_es("18 de mayo de 2026"), norm_cn("2026 年 5 月 18 日"))

    def test_ru_date_roundtrip_maya(self):
        self.assertEqual(norm_ru("с 18 мая 2026 года"), ["18", "5", "2026"])

    def test_ru_maya_guarded_in_prose(self):
        self.assertNotIn("5", norm_ru("маяк виден в начале мая"))

    def test_ru_maya_guarded_in_may_word(self):
        self.assertNotIn("5", norm_ru("самая видимая"))

    def test_en_may_modal_not_folded_current_behavior(self):
        # 422 lowercase 'may' modals in EN book; folding EN 'may' requires a
        # date-anchored rule like RU's. Armor: must NOT fold today (would
        # inject phantom 5s everywhere).
        self.assertEqual(norm_en("this may reduce risk"), [])

    def test_ru_month_prose_stems_fold(self):
        self.assertIn("3", norm_ru("мартовский номер"))
        self.assertIn("12", norm_ru("в декабре"))
        self.assertIn("6", norm_ru("в июне"))

    def test_ru_maya_nbsp_date(self):
        self.assertIn("5", norm_ru("1\u00a0мая"))


class BannedCalque(unittest.TestCase):
    """Check 7 semantics via real verify.py run: >1 occurrence fails, 1 warns."""

    def _run_verify(self, text):
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cand.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            r = subprocess.run(
                [sys.executable, os.path.join(_ROOT, "tools", "verify.py"),
                 "01", "--lang", "ru", "--file", p, "--json"],
                cwd=_ROOT, capture_output=True, text=True,
            )
        js = next((l for l in reversed(r.stdout.splitlines()) if l.startswith("{")), None)
        self.assertIsNotNone(js, r.stdout + r.stderr)
        return json.loads(js)

    def test_calque_once_is_warn_not_fail(self):
        rep = self._run_verify("### 1. x\n- Примечания: это когорта пациентов\n")
        kinds = [f["kind"] for f in rep["fails"]]
        self.assertNotIn("banned_calque", kinds)
        self.assertTrue(any(w["kind"] == "calque_once" for w in rep["warns"]))

    def test_calque_twice_fails(self):
        rep = self._run_verify("### 1. x\n- Примечания: когорта и снова когорта\n")
        self.assertTrue(any(f["kind"] == "banned_calque" for f in rep["fails"]))

    def test_calque_stem_substring_counts(self):
        # «когорте/когорты» share the stem — must count toward the limit
        rep = self._run_verify("### 1. x\n- Примечания: в когорте и из когорты\n")
        self.assertTrue(any(f["kind"] == "banned_calque" for f in rep["fails"]))

    def test_populyac_stem_matches_declensions(self):
        rep = self._run_verify("### 1. x\n- Примечания: популяция и популяций\n")
        self.assertTrue(any(f["kind"] == "banned_calque" for f in rep["fails"]))


class CJKOutside(unittest.TestCase):
    """Check 6 semantics: CJK in TR body must fail; glosses/notes are allowed.

    Fixtures pad to line 5+ because check 6 exempts the first 4 lines (status
    block) — a naive 2-line fixture would silently test nothing.
    """

    PAD = "#pad\n#pad\n#pad\n"  # occupies lines 2-4

    def _run_verify(self, text, lang="ru"):
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cand.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            r = subprocess.run(
                [sys.executable, os.path.join(_ROOT, "tools", "verify.py"),
                 "01", "--lang", lang, "--file", p, "--json"],
                cwd=_ROOT, capture_output=True, text=True,
            )
        js = next((l for l in reversed(r.stdout.splitlines()) if l.startswith("{")), None)
        self.assertIsNotNone(js, r.stdout + r.stderr)
        return json.loads(js)

    def test_cjk_in_body_fails(self):
        rep = self._run_verify(
            "### 1. x\n" + self.PAD + "- Примечания: тут 成本 затесался\n")
        self.assertTrue(any(f["kind"] == "cjk_outside" for f in rep["fails"]))

    def test_cjk_in_heading_fails(self):
        rep = self._run_verify("### 1. x\n" + self.PAD + "### 5. 成本\n")
        self.assertTrue(any(f["kind"] == "cjk_outside" for f in rep["fails"]))

    def test_cjk_in_source_line_allowed(self):
        rep = self._run_verify(
            "### 1. x\n" + self.PAD
            + "- Источники: 全国人大 (2020). 民法典\n- Примечания: чисто\n")
        self.assertFalse(any(f["kind"] == "cjk_outside" for f in rep["fails"]))

    def test_cjk_in_translator_note_block_allowed(self):
        rep = self._run_verify(
            "### 1. x\n" + self.PAD
            + "> Примечание переводчика: термин 成本 оставлен как в оригинале\n"
            "> продолжение примечания 说人话\n- Примечания: чисто\n")
        self.assertFalse(any(f["kind"] == "cjk_outside" for f in rep["fails"]))

    def test_cjk_in_paren_gloss_allowed(self):
        rep = self._run_verify(
            "### 1. x\n" + self.PAD
            + "- Примечания: уплата (成本) налога — чисто\n")
        self.assertFalse(any(f["kind"] == "cjk_outside" for f in rep["fails"]))

    def test_cjk_without_parens_fails_control(self):
        # negative control for the gloss test above
        rep = self._run_verify(
            "### 1. x\n" + self.PAD
            + "- Примечания: уплата 成本 налога — чисто\n")
        self.assertTrue(any(f["kind"] == "cjk_outside" for f in rep["fails"]))

    def test_fullwidth_punct_warns_not_fails(self):
        rep = self._run_verify(
            "### 1. x\n" + self.PAD + "- Примечания: раз，два\n")
        self.assertFalse(any(f["kind"] == "cjk_outside" for f in rep["fails"]))
        self.assertTrue(any(w["kind"] == "fullwidth" for w in rep["warns"]))


class FieldChecks(unittest.TestCase):
    """Check 4/4.5 semantics against the real (clean) book/ru/01 chapter.

    --file mode always diffs against the CN original of chapter 01, so the
    only honest fixture is the committed RU chapter itself (verified clean:
    verify exits 0 on it). Mutations are applied on top of the base text.
    """

    BASE = os.path.join(_ROOT, "book", "ru", "01-Не-умирайте-рано.md")

    def setUp(self):
        if not os.path.isfile(self.BASE):
            self.skipTest("no ru ch01")
        self.base = open(self.BASE, encoding="utf-8").read()

    def _run(self, text):
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cand.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            r = subprocess.run(
                [sys.executable, os.path.join(_ROOT, "tools", "verify.py"),
                 "01", "--lang", "ru", "--file", p, "--json"],
                cwd=_ROOT, capture_output=True, text=True,
            )
        js = next((l for l in reversed(r.stdout.splitlines()) if l.startswith("{")), None)
        self.assertIsNotNone(js, r.stdout + r.stderr)
        return json.loads(js)

    def test_base_is_clean(self):
        rep = self._run(self.base)
        self.assertEqual(rep["fails"], [], rep["fails"][:3])

    def test_indented_label_still_counts(self):
        mutated = self.base.replace("\n- Эффект:", "\n   - Эффект:", 1)
        rep = self._run(mutated)
        self.assertFalse(
            any(f["kind"] == "field_count" for f in rep["fails"]),
            "lstrip() must tolerate indented labels")

    def test_missing_field_fails(self):
        mutated = self.base.replace("\n- Эффект:", "\n- ПримечанияX:", 1)
        rep = self._run(mutated)
        fc = [f for f in rep["fails"] if f["kind"] == "field_count"]
        self.assertTrue(fc)
        self.assertTrue(any(f["label"] == "Эффект" and f["got"] < f["want"] for f in fc))

    def test_jargon_in_plain_warns(self):
        mutated = self.base.replace(
            "\n- Простыми словами:", "\n- Простыми словами: (HR 0.56)", 1)
        rep = self._run(mutated)
        self.assertTrue(any(w["kind"] == "jargon_in_plain" for w in rep["warns"]))

    def test_no_jargon_in_base(self):
        rep = self._run(self.base)
        self.assertFalse(any(w["kind"] == "jargon_in_plain" for w in rep["warns"]))

    def test_jargon_substring_not_matched(self):
        # 'RRI'/'ORR'/'CIa' must not match \b(?:HR|RR|OR|CI)\b
        mutated = self.base.replace(
            "\n- Простыми словами:", "\n- Простыми словами: проект RRI, ориентир", 1)
        rep = self._run(mutated)
        self.assertFalse(any(w["kind"] == "jargon_in_plain" for w in rep["warns"]))


class SpelledOutNumbers(unittest.TestCase):
    def test_ru_odin_dva(self):
        self.assertIn("1", norm_ru("один или одна"))
        self.assertIn("2", norm_ru("два или две"))

    def test_ru_poluchaet_half(self):
        self.assertEqual(norm_ru("полтора часа"), ["1.5"])

    def test_ru_round_the_clock(self):
        self.assertIn("24", norm_ru("круглосуточно"))

    def test_en_word_numbers(self):
        self.assertEqual(norm_en("twelve thousand"), ["12000"])
        self.assertEqual(norm_en("five million"), ["5000000"])

    def test_en_one_in_context(self):
        self.assertIn("1", norm_en("one option"))

    # bug-05: bare scale nouns / полторы compounds
    @unittest.expectedFailure
    def test_ru_bare_tysyacha(self):
        self.assertEqual(norm_ru("одна тысяча"), norm_ru("тысяча"))

    @unittest.expectedFailure
    def test_ru_polytory_tysyachi(self):
        self.assertEqual(norm_ru("полторы тысячи"), ["1500"])

    @unittest.expectedFailure
    def test_ru_polytora_dva_range(self):
        # CN ch02 heading 38 «一两小时» rendered «полутора-двух часов»:
        # RU folds only [2] → phantom extra-value warn (live in ru ch02)
        self.assertEqual(norm_ru("полутора-двух часов"), ["1.5", "2"])

    # bug-09: RU spelled ≥13
    @unittest.expectedFailure
    def test_ru_spelled_thirty(self):
        self.assertEqual(norm_ru("минут тридцать"), ["30"])

    @unittest.expectedFailure
    def test_ru_spelled_hundreds(self):
        self.assertEqual(norm_ru("двести-триста юаней"), ["200", "300"])

    @unittest.expectedFailure
    def test_ru_spelled_sto(self):
        self.assertEqual(norm_ru("сто рублей"), ["100"])

    # bug-09 (CN side): digit-less 数词+万/千/百
    @unittest.expectedFailure
    def test_cn_liangwan(self):
        self.assertEqual(norm_cn("两万人"), ["20000"])

    @unittest.expectedFailure
    def test_cn_yiwan(self):
        self.assertEqual(norm_cn("一万步"), ["10000"])

    @unittest.expectedFailure
    def test_cn_sanqian(self):
        self.assertEqual(norm_cn("三千人"), ["3000"])

    @unittest.expectedFailure
    def test_cn_wubai(self):
        self.assertEqual(norm_cn("五百到一千"), ["500", "1000"])


class WordBoundaryMonths(unittest.TestCase):
    def test_ru_maya_anchor_requires_digit(self):
        # «мая» as productive word-end: «видимая»/«самая» must not match
        self.assertNotIn("5", norm_ru("самая видимая"))

    def test_ru_maya_digit_date(self):
        self.assertIn("5", norm_ru("1 мая"))

    def test_ru_9maya_date_split_roundtrip(self):
        # «9 мая» yields 9 AND 5 — the 5 is the month value; CN «5 月 9 日»
        # yields 5 and 9 as well, so the round-trip matches. Armor.
        self.assertEqual(norm_ru("9 мая"), ["9", "5"])
        self.assertEqual(norm_cn("5 月 9 日"), ["5", "9"])

    def test_march_case_insensitive(self):
        self.assertIn("3", norm_en("March 3"))

    def test_march_inside_word_guarded(self):
        # «smarching» must not yield 3
        self.assertEqual(norm_en("smarching"), [])

    def test_ru_march_stem_inside_adjective(self):
        # «мартовский» legitimately folds (month adjective) — armor pin
        self.assertIn("3", norm_ru("мартовский"))


class TrickyFalseMatches(unittest.TestCase):
    def test_millionaire_guarded(self):
        # 'million' scale attaches only to a preceding digit; bare
        # 'millionaires' has no digits → nothing extracted
        self.assertEqual(norm_en("millionaires"), [])

    def test_version_numbers(self):
        self.assertEqual(norm_en("v2.6"), ["2.6"])

    def test_dot_five_wan(self):
        self.assertEqual(norm_cn(".5 万"), ["50000"])

    def test_negative_dash_wan_is_range(self):
        # «30-50万» — dash is a range separator, not a minus: pinned
        self.assertEqual(norm_cn("30-50万"), ["30", "500000"])

    def test_iso_date_like(self):
        self.assertEqual(norm_cn("2023-2024"), ["2023", "2024"])

    def test_scale_word_without_digit(self):
        self.assertEqual(norm_ru("миллиардный вопрос"), [])
        self.assertEqual(norm_ru("тысяча мелочей"), [])


if __name__ == "__main__":
    unittest.main()
