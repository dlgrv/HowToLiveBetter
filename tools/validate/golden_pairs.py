#!/usr/bin/env python3
"""Golden set for judge validation (plan Task 5): 60 pairs, 10 decoys.

Composition: 6 chapters x 3 strata x {ru, en} = 36 anchor pairs + 24 fresh
random pairs = 60. 10 of the 60 are decoys (A=B identical texts) measuring
false preference. B-variants = controlled degradations (impersonal calque /
literalisation / bureaucratese / passive chain; numbers untouched) generated
by subagents from the degradation recipes below.

Determinism: chapter/excerpt selection is seeded (seed=42); the generation
prompt list is pinned in the manifest (gen_ref). variant_a IS the original
text; the mapping variant->original lives ONLY here (never in the markup
session). Numbers inside excerpts are excluded from degradation scope.
"""
import argparse
import glob
import hashlib
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(REPO, "tools", "validate", "results")
MANIFEST = os.path.join(RESULTS, "golden_manifest.json")
SEED = 42
GREEN_CHAPTERS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "12",
                  "14", "15", "16", "17", "18", "19", "20", "21", "22", "23",
                  "24", "25", "26", "27", "29", "31", "32"]
DEGRADE_RECIPES = [
    {"name": "impersonal_calque",
     "instruction": "Replace active personal constructions with impersonal/agentless passive phrasing (RU: 'следует осуществлять', 'производится'; EN: 'it is recommended that', 'is to be performed'). Keep every number byte-identical."},
    {"name": "literalisation",
     "instruction": "Make idiomatic phrasing literal/word-by-word while staying grammatical. Keep every number byte-identical."},
    {"name": "bureaucratese",
     "instruction": "Insert officialese: 'является', 'данного', 'в рамках', 'осуществля' (RU) / 'utilize', 'with respect to', 'aforementioned' (EN). Keep every number byte-identical."},
    {"name": "passive_chain",
     "instruction": "Chain two or more passive participle constructions into heavy stacked phrases. Keep every number byte-identical."},
    {"name": "jargonize",
     "instruction": "Swap common words for professional jargon/terminology WITHOUT explanation (medical, legal, financial register), keeping meaning identical and all numbers byte-identical. The variant must stay grammatical — it should read as 'expert-speak' a layperson cannot follow."},
]

CLEAN_GREEN = set(GREEN_CHAPTERS)


def read_chapter(root, nn, lang):
    hits = glob.glob(os.path.join(root, "book", lang, f"{int(nn):02d}-*.md"))
    if not hits:
        raise FileNotFoundError(f"book/{lang}/{int(nn):02d}-*.md")
    return open(hits[0], encoding="utf-8").read()


def excerpt_pool(root, nn, lang):
    """Candidate excerpts: whole item blocks (4-14 lines).

    Tag comments and source lines legitimately contain CJK and are kept:
    they are byte-identical in both variants and do not affect fluency
    comparison. Blocks span from '### ' heading to the next heading/blank.
    """
    text = read_chapter(root, nn, lang)
    blocks, cur = [], []
    for line in text.splitlines():
        if line.startswith("### ") or line.strip() == "":
            if cur:
                blocks.append("\n".join(cur))
            cur = [line] if line.startswith("### ") else []
        elif cur:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in blocks if 4 <= len(b.splitlines()) <= 14]


def select_pairs(root=REPO):
    """Deterministic 60-pair selection. Returns manifest dict (B empty)."""
    rng = random.Random(SEED)
    chapters = rng.sample(GREEN_CHAPTERS, 6)
    pairs, pid = [], 0

    def add(nn, lang, excerpt, stratum, decoy):
        nonlocal pid
        pid += 1
        pairs.append({
            "id": f"g{pid:02d}", "chapter": nn, "lang": lang,
            "stratum": stratum, "decoy": decoy,
            "variant_a": excerpt, "variant_b": "" if not decoy else excerpt,
            "recipe": None if decoy else DEGRADE_RECIPES[pid % len(DEGRADE_RECIPES)]["name"],
            "show_order": "BA" if rng.random() < 0.5 else "AB",
        })

    # anchors: 6 chapters x 3 strata x 2 langs = 36
    for nn in chapters:
        for lang in ("ru", "en"):
            pool = excerpt_pool(root, nn, lang)
            if len(pool) < 3:
                continue
            chosen = sorted(rng.sample(pool, 3), key=len)
            for excerpt, stratum in zip(chosen, ("short", "medium", "long")):
                add(nn, lang, excerpt, stratum, decoy=False)
    # fresh random pairs to reach 60 total, 10 of them decoys
    need = 60 - len(pairs)
    decoy_slots = set(rng.sample(range(need), min(10, need)))  # relative indices
    placed, guard = 0, 0
    while placed < need and guard < 1000:
        guard += 1
        nn, lang = rng.choice(GREEN_CHAPTERS), rng.choice(("ru", "en"))
        pool = excerpt_pool(root, nn, lang)
        if not pool:
            continue
        add(nn, lang, rng.choice(pool), "fresh", decoy=placed in decoy_slots)
        placed += 1
    manifest = {"seed": SEED, "green_chapters": GREEN_CHAPTERS,
                "recipes": DEGRADE_RECIPES,
                "counts": {"pairs": len(pairs), "decoys": sum(p["decoy"] for p in pairs)}}
    gen_payload = json.dumps({"chapters": chapters, "recipes": DEGRADE_RECIPES}, sort_keys=True)
    manifest["gen_ref"] = hashlib.sha256(gen_payload.encode()).hexdigest()
    manifest["pairs"] = pairs
    return manifest


def load_manifest(path=MANIFEST):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_session(root=REPO):
    """Markup session: 6 batches x 10 pairs, no mapping leakage."""
    m = load_manifest()
    batches = []
    for b in range(6):
        chunk = m["pairs"][b * 10:(b + 1) * 10]
        items = []
        for p in chunk:
            first, second = (p["variant_a"], p["variant_b"]) if p["show_order"] == "AB" \
                else (p["variant_b"], p["variant_a"])
            items.append({
                "pair_id": p["id"],
                "rendered": f"VARIANT 1:\n{first}\n\nVARIANT 2:\n{second}",
            })
        batches.append({"batch": b + 1, "pairs": items})
    return {"instruction": "Для каждой пары ответьте 1 / 2 / = (какой вариант написан по-русски/по-английски естественнее). Не ищите «правильный» текст — оценивайте только естественность языка.",
            "batches": batches}


def validate_manifest():
    m = load_manifest()
    problems = []
    if len(m["pairs"]) != 60:
        problems.append(f"pairs {len(m['pairs'])} != 60")
    if sum(p["decoy"] for p in m["pairs"]) != 10:
        problems.append("decoys != 10")
    for p in m["pairs"]:
        if not p["decoy"] and p["variant_b"] and p["variant_b"] == p["variant_a"]:
            problems.append(f"pair {p['id']}: B == A")
        if not p["decoy"] and p.get("variant_b") and not p.get("recipe"):
            problems.append(f"pair {p['id']}: B filled without recipe")
        book = read_chapter(REPO, p["chapter"], p["lang"])
        if p["variant_a"][:80] not in book:
            problems.append(f"pair {p['id']}: variant_a not in book")
    if problems:
        print("MANIFEST INVALID:")
        for x in problems:
            print("  -", x)
        return 1
    print(f"manifest valid: 60 pairs, 10 decoys, gen_ref={m['gen_ref'][:12]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select", help="deterministic selection -> manifest skeleton")
    sub.add_parser("validate", help="validate filled manifest")
    sub.add_parser("session", help="print markup session batches (no mapping)")
    args = ap.parse_args()
    if args.cmd == "select":
        m = select_pairs()
        os.makedirs(RESULTS, exist_ok=True)
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
        print(f"selected {m['counts']['pairs']} pairs "
              f"({m['counts']['decoys']} decoys), gen_ref={m['gen_ref'][:12]}")
    elif args.cmd == "validate":
        sys.exit(validate_manifest())
    else:
        print(json.dumps(build_session(), ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
