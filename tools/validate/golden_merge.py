#!/usr/bin/env python3
"""Merge subagent B-variant files into the golden manifest (plan Task 11 prep).

Applies the hard rules as REJECTIONS (not repairs): a pair whose B-variant
changes numbers, breaks markdown structure, or touches immutable lines is
rejected with a reason and left empty for re-generation.
"""
import glob
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(REPO, "tools", "validate", "results")
MANIFEST = os.path.join(RESULTS, "golden_manifest.json")

IMMUTABLE_PREFIXES = ("### ", "<!--", "- Источники:", "- Sources:")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def validate_pair(a, b):
    """Return None if B is acceptable, else a rejection reason."""
    if not b or not b.strip():
        return "empty"
    if a == b:
        return "b_equals_a"
    if sorted(NUM_RE.findall(a)) != sorted(NUM_RE.findall(b)):
        return "numbers_changed"
    la, lb = a.splitlines(), b.splitlines()
    if len(la) != len(lb):
        return "line_count_changed"
    for i, (xa, xb) in enumerate(zip(la, lb)):
        if xa.startswith(IMMUTABLE_PREFIXES) and xa != xb:
            return f"immutable_line_{i}"
    return None


def merge():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    by_id = {p["id"]: p for p in m["pairs"]}
    filled, rejected = 0, []
    for path in sorted(glob.glob(os.path.join(RESULTS, "_golden_b_*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        for item in data:
            p = by_id.get(item["pair_id"])
            if p is None:
                rejected.append({"pair_id": item["pair_id"], "reason": "unknown_pair"})
                continue
            if p["decoy"]:
                rejected.append({"pair_id": p["id"], "reason": "decoy_untouchable"})
                continue
            reason = validate_pair(p["variant_a"], item["variant_b"])
            if reason:
                rejected.append({"pair_id": p["id"], "reason": reason})
                continue
            p["variant_b"] = item["variant_b"]
            filled += 1
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    return {"filled": filled, "rejected": rejected,
            "still_empty": [p["id"] for p in m["pairs"]
                            if not p["decoy"] and not p["variant_b"]]}


def main():
    print(json.dumps(merge(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
