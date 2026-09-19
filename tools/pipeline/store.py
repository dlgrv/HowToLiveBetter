"""Verdict persistence: content hashes, audit payloads, tools/judge/ layout.

Every verdict written here carries the reproducibility audit fields
(model_id, ts, prompt_hash, unit_sha256) required by the validation protocol.
"""
import hashlib
import json
import os
import re
import time

# Service placeholder lines injected by make_digest.py; never shown to judges.
_SERVICE_LINE = re.compile(r"^§(?:TAG|SRC)§$")


def norm_text(text):
    """Normalise unit text for matching: drop §TAG§/§SRC§ service lines and
    empty lines, collapse runs of whitespace. Used for span grounding."""
    kept = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _SERVICE_LINE.match(line):
            continue
        kept.append(re.sub(r"\s+", " ", line))
    return "\n".join(kept)


def unit_sha256(path):
    """Byte-exact content hash of a unit/book file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def hash_prompt(prompt):
    """Stable hash of the exact prompt text sent to a judge."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_payload(tool, mode, model_id, prompt, unit_path, verdict):
    """Assemble a verdict payload with mandatory audit fields."""
    return {
        "tool": tool,
        "mode": mode,
        "model_id": model_id,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt_hash": hash_prompt(prompt),
        "unit_sha256": unit_sha256(unit_path),
        "verdict": verdict,
    }


def write_verdict(base, nn, lang, unit, payload):
    """Write one verdict to <base>/tools/judge/<NN>/<lang>/<unit>.json (atomic)."""
    d = os.path.join(base, "tools", "judge", nn, lang)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{unit}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def read_verdict(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
