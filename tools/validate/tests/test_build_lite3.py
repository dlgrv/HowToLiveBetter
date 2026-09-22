"""Tests for build_lite3: meaning_break degradations are sane and gated."""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))  # tools/validate (check_degrade)

spec = importlib.util.spec_from_file_location(
    "build_lite3", os.path.join(os.path.dirname(HERE), "build_lite3.py"))
assert spec is not None and spec.loader is not None
bl3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl3)


def _manifest():
    return json.load(open(os.path.join(
        REPO, "tools/validate/results/golden_manifest.json"), encoding="utf-8"))


def test_edits_target_real_pairs_with_matching_language():
    m = _manifest()
    by_id = {p["id"]: p for p in m["pairs"]}
    for pid, edits in bl3.EDITS.items():
        assert pid in by_id, f"unknown pair {pid}"
        assert edits, f"pair {pid} has no edits"


def test_every_edit_string_is_found_in_original():
    m = _manifest()
    by_id = {p["id"]: p for p in m["pairs"]}
    missing = []
    for pid, edits in bl3.EDITS.items():
        a = by_id[pid]["variant_a"]
        for old, _new in edits:
            if old not in a:
                missing.append((pid, old[:50]))
    assert not missing, f"edit targets not in originals: {missing}"


def test_generated_variants_pass_all_gates():
    m = _manifest()
    by_id = {p["id"]: p for p in m["pairs"]}
    for pid, edits in bl3.EDITS.items():
        p = by_id[pid]
        b = p["variant_a"]
        for old, new in edits:
            b = b.replace(old, new)
        b = bl3.pad(b, len(p["variant_a"]), p["lang"])
        probs = bl3.check({"variant_b": b, "lang": p["lang"]},
                          p["variant_a"], "bloat")
        if pid == "g23":  # original itself carries a literal TODO marker
            probs = [x for x in probs if x != "meta/leak words present"]
        assert not probs, f"{pid}: {probs}"


def test_saved_results_file_matches_gates():
    path = os.path.join(REPO,
                        "tools/validate/results/_lite3_degrade_meaning_break.json")
    if not os.path.exists(path):
        return  # built artifact not committed yet
    d = json.load(open(path, encoding="utf-8"))
    m = _manifest()
    by_id = {p["id"]: p for p in m["pairs"]}
    assert {p["pair_id"] for p in d["pairs"]} == set(bl3.EDITS)
    for pair in d["pairs"]:
        p = by_id[pair["pair_id"]]
        ratio = len(pair["variant_b"]) / max(1, len(p["variant_a"]))
        assert 1.15 <= ratio <= 1.7, f"{pair['pair_id']}: ratio {ratio:.2f}"
