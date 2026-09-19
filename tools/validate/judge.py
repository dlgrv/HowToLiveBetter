#!/usr/bin/env python3
"""Judge CLI: score one unit with the screen/ab/factcheck prompt.

Contract (plan Task 1):
  python3 tools/validate/judge.py --file <unit.md> --mode screen --json

Judge invocation is model-agnostic:
  - PRIMARY: orchestrated Hermes subagents (z.ai key lives in Hermes config,
    never in env/repo) — the orchestrator writes verdicts via tools/pipeline/store.py.
  - DIRECT:  this CLI calls the OpenAI-compatible HTTP API when ZAI_API_KEY
    (or Z_AI_API_KEY/ZHIPUAI_API_KEY) is present in the environment.
Without a key and without --stdin-response the CLI prints a clear setup note
and exits 2 (so pipelines can detect "judge unavailable" explicitly).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pipeline import judges  # noqa: E402
from tools.pipeline import store   # noqa: E402
from tools.validate.factcheck import parse_verdict  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROMPTS_DIR = os.path.join(REPO, "tools", "prompts")


def load_prompt(mode):
    path = os.path.join(PROMPTS_DIR, f"judge-{mode}.md")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"prompt template missing: {path} (created in plan Task 2)")
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser(description="Score a unit with a judge prompt")
    ap.add_argument("--file", required=True, help="path to the unit .md file")
    ap.add_argument("--mode", default="screen", choices=["screen", "ab", "factcheck"])
    ap.add_argument("--stdin-response", help="use this raw judge reply instead of calling the API (offline/testing)")
    ap.add_argument("--out-unit", default=None, help="unit id for the verdict filename (default: file stem)")
    ap.add_argument("--json", action="store_true", help="print the verdict payload as JSON")
    args = ap.parse_args()

    unit_path = os.path.abspath(args.file)
    if not os.path.isfile(unit_path):
        sys.exit(f"no such file: {unit_path}")
    with open(unit_path, encoding="utf-8") as f:
        unit_text = f.read()

    prompt_template = load_prompt(args.mode)
    prompt = f"{prompt_template}\n\n---\n\n{unit_text}"

    model_id = judges.configured_model_id(REPO)
    if args.stdin_response:
        reply = args.stdin_response
    else:
        api_key = judges.resolve_api_key()
        if not api_key:
            print(json.dumps({
                "error": "judge_unavailable",
                "hint": "judges run via Hermes subagents (primary) or set ZAI_API_KEY for direct HTTP",
                "model_id": model_id,
            }, ensure_ascii=False))
            return 2
        backend_cls = judges.get_backend(judges.backend_name(REPO))
        client = backend_cls(model_id=model_id, api_key=api_key)
        reply = client.complete(prompt)

    try:
        verdict = json.loads(reply)
    except json.JSONDecodeError:
        verdict = parse_verdict(reply)

    payload = store.build_payload(
        tool=f"validate.judge.{args.mode}", mode=args.mode, model_id=model_id,
        prompt=prompt, unit_path=unit_path, verdict=verdict)

    unit_id = args.out_unit or os.path.splitext(os.path.basename(unit_path))[0]
    out = store.write_verdict(REPO, "00", "adhoc", unit_id, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"verdict written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
