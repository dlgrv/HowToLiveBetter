#!/usr/bin/env python3
"""Blind judge AB run against the golden manifest.

For every pair in the subset the judge sees the pair in BOTH presentation
orders (AB and BA) on separate calls; decoding maps the chosen slot back to
variant_a preference. This kills presentation-order leakage (review S2).

Outputs per-call JSON to --out dir (resume-safe: existing files are kept)
plus a summary.json with native_preference / decoy FP / length-bias /
position-bias breakdowns.

Usage:
  python3 tools/validate/judge_blind_run.py \
      --subset tools/validate/results/golden_lite_subset.json \
      --out tools/validate/results/golden_judge_run_lite
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from tools.pipeline import judges  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT_PATH = os.path.join(REPO, "tools", "prompts", "judge-ab.md")


def render(pair, order):
    a, b = pair["variant_a"], pair["variant_b"]
    first, second = (a, b) if order == "AB" else (b, a)
    return f"VARIANT 1:\n{first}\n\nVARIANT 2:\n{second}"


def decode(winner, order):
    """winner string -> 'a' | 'b' | 'tie'."""
    w = str(winner).strip().lower()
    if w in ("tie", "="):
        return "tie"
    slot = 1 if w in ("1", "a", "variant 1") else 2 if w in ("2", "b", "variant 2") else None
    if slot is None:
        return "unparsed"
    chose_first = (slot == 1)
    chose_a = chose_first if order == "AB" else not chose_first
    return "a" if chose_a else "b"


def parse_reply(reply):
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj.get("winner")


def call_judge(cfg, api_key, rendered):
    client = judges.get_backend(cfg["backend"])(
        model_id=cfg["model_id"], api_key=api_key)
    prompt = open(PROMPT_PATH, encoding="utf-8").read()
    return client.complete(prompt + "\n\n" + rendered)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cfg = judges._config.load_config(REPO).get("judge", {})
    cfg.setdefault("backend", judges.backend_name(REPO))
    cfg.setdefault("model_id", judges.configured_model_id(REPO))
    api_key = judges.resolve_api_key()
    if not api_key:
        print(json.dumps({"status": "no_api_key"}))
        return 1

    subset = json.load(open(args.subset, encoding="utf-8"))
    manifest = json.load(open(os.path.join(REPO, "tools/validate/results/golden_manifest.json"),
                              encoding="utf-8"))
    by_id = {p["id"]: p for p in manifest["pairs"]}

    os.makedirs(args.out, exist_ok=True)
    jobs = []
    for pid in subset["ids"]:
        for order in ("AB", "BA"):
            path = os.path.join(args.out, f"{pid}_{order}.json")
            done = False
            if os.path.exists(path):
                try:
                    prev = json.load(open(path, encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    prev = None
                # a valid completed call has a decode; error files are retried
                done = bool(prev) and "error" not in prev and "decoded" in prev
            if not done:
                jobs.append((pid, order, path))

    print(f"todo {len(jobs)} calls (of {2*len(subset['ids'])})", flush=True)

    def work(job):
        pid, order, path = job
        pair = by_id[pid]
        rendered = render(pair, order)
        t0 = time.time()
        reply = None
        for attempt in range(3):
            try:
                reply = call_judge(cfg, api_key, rendered)
                break
            except Exception as e:  # transient network/API errors
                if attempt == 2:
                    result = {"error": f"{type(e).__name__}: {e}"[:300]}
                    json.dump(result, open(path, "w", encoding="utf-8"))
                    return
                time.sleep(3 * (attempt + 1))
        if reply is None:
            return
        winner = parse_reply(reply)
        result = {
            "pair_id": pid, "order": order, "winner_raw": winner,
            "decoded": decode(winner, order) if winner is not None else "unparsed",
            "reply": reply[-400:], "latency_s": round(time.time() - t0, 1),
            "model": cfg["model_id"],
        }
        json.dump(result, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, jobs))

    # ---- aggregate ----
    rows = []
    for pid in subset["ids"]:
        for order in ("AB", "BA"):
            path = os.path.join(args.out, f"{pid}_{order}.json")
            if os.path.exists(path):
                r = json.load(open(path, encoding="utf-8"))
                # failed-call files carry only {"error": ...}
                r.setdefault("decoded", "unparsed")
                r.setdefault("pair_id", pid)
                r.setdefault("order", order)
                r.setdefault("winner_raw", None)
                r["decoy"] = by_id[pid]["decoy"]
                la = len(by_id[pid]["variant_a"] or "")
                lb = len(by_id[pid]["variant_b"] or "")
                r["longer_is_a"] = (la > lb) if la != lb else None
                rows.append(r)
    content = [r for r in rows if not r["decoy"] and r["decoded"] in ("a", "b", "tie")]
    decoys = [r for r in rows if r["decoy"] and r["decoded"] in ("a", "b", "tie")]

    def rate(rs):
        n = len(rs)
        a = sum(1 for r in rs if r["decoded"] == "a")
        return {"rate_a": round(a / n, 3) if n else None, "n": n,
                "a": a, "b": sum(1 for r in rs if r["decoded"] == "b"),
                "tie": sum(1 for r in rs if r["decoded"] == "tie")}

    dec_content = [r for r in content if r["decoded"] != "tie"]
    n_errors = sum(1 for r in rows if "error" in r)
    summary = {
        "model": cfg["model_id"],
        "subset": subset["ids"],
        "failed_calls": n_errors,
        "unparsed": sum(1 for r in rows if r["decoded"] == "unparsed" and "error" not in r),
        "native_preference": rate(content),
        "decoy": rate(decoys),
        "order_bias": {
            o: rate([r for r in content if r["order"] == o]) for o in ("AB", "BA")},
        "length_bias": {
            "picked_longer": sum(1 for r in dec_content
                                 if r["longer_is_a"] is not None
                                 and ((r["decoded"] == "a") == r["longer_is_a"])),
            "decided": len([r for r in dec_content if r["longer_is_a"] is not None])},
        "per_pair": {pid: [r["decoded"] for r in content if r["pair_id"] == pid]
                     for pid in subset["ids"]},
    }
    json.dump(summary, open(os.path.join(args.out, "summary.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: summary[k] for k in
                      ("model", "native_preference", "decoy", "order_bias", "length_bias")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
