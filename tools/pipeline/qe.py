"""COMET QE wrapper (reusable core): model from project.yaml, SKIPPED without venv.

Heavy weights (unbabel-comet + torch) live in a dedicated venv (~/.venvs/qe on
the Mac). Everywhere else this module degrades gracefully: `available()` is
False and `run_scores` raises QeUnavailable — callers emit an explicit
SKIPPED status instead of failing the pipeline (pass B is advisory-only).
"""
import json
import os
import re
import shutil
import subprocess

from . import config as _config

DEFAULT_CONFIG_PATH = os.path.join("tools", "validate", "qe_config.json")
DEFAULT_TAU_FLOOR = 0.01


class QeUnavailable(RuntimeError):
    """COMET stack (venv/model) not available on this machine."""


def load_qe_config(root):
    path = os.path.join(root, DEFAULT_CONFIG_PATH)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def venv_python(root):
    """Python executable of the QE venv, or None when absent."""
    cfg = load_qe_config(root)
    venv = cfg.get("venv", "~/.venvs/qe")
    venv = os.path.expanduser(venv)
    exe = os.path.join(venv, "bin", "python")
    return exe if os.path.isfile(exe) else None


def available(root):
    return venv_python(root) is not None


def _runner_source():
    """Inline runner executed by the venv python (imports comet there only)."""
    return r'''
import json, sys
from comet import download_model, load_from_checkpoint
cfg = json.load(sys.stdin)
model_path = download_model(cfg["model"], revision=cfg.get("revision") or None)
model = load_from_checkpoint(model_path)
data = [{"src": d["src"], "mt": d["mt"]} for d in cfg["segments"]]
out = model.predict(data, batch_size=cfg.get("batch_size", 32), gpus=0)
print(json.dumps({"scores": list(out.scores)}))
'''


def run_scores(segments, root=None):
    """Score (src, mt) pairs with the configured COMET QE model.

    Returns list of floats. Raises QeUnavailable when the venv is absent
    (VPS/CI); the caller converts this into an explicit SKIPPED status.
    """
    root = root or _config.default_root()
    exe = venv_python(root)
    if not exe:
        raise QeUnavailable("qe venv not found (~/.venvs/qe); COMET scoring unavailable")
    cfg = load_qe_config(root)
    payload = json.dumps({
        "model": cfg["model"],
        "revision": cfg.get("revision"),
        "batch_size": cfg.get("batch_size", 32),
        "segments": segments,
    })
    proc = subprocess.run(
        [exe, "-c", _runner_source()], input=payload,
        capture_output=True, text=True, timeout=cfg.get("timeout_s", 1800))
    if proc.returncode != 0:
        raise QeUnavailable(f"comet runner failed: {proc.stderr.strip()[-400:]}")
    scores = parse_scores(proc.stdout)
    if scores is None:
        raise QeUnavailable("comet runner produced unparseable output")
    return scores


def parse_scores(stdout):
    """Extract the JSON {"scores": [...]} line from runner output."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"scores"' in line:
            try:
                return json.loads(line)["scores"]
            except (json.JSONDecodeError, KeyError):
                return None
    return None


def parse_comet_cli(stdout):
    """Parse `comet-score ...: 0.8123` style CLI output (fallback path)."""
    m = re.findall(r"([+-]?\d+\.\d+)\s*$", stdout.strip(), re.MULTILINE)
    return float(m[-1]) if m else None


def compute_tau(sigma):
    """Noise threshold: tau = max(3*sigma, 0.01) — plan Task 3."""
    return max(3.0 * float(sigma), DEFAULT_TAU_FLOOR)


def check_model_license(model_name):
    """Guard: only Apache-2.0 COMET models allowed in prod (NC models banned)."""
    banned = ("cometkiwi", "xcomet")
    lowered = model_name.lower()
    if any(b in lowered for b in banned):
        raise ValueError(f"model {model_name} is CC-BY-NC — banned in prod; use wmt20-comet-qe-da / wmt22-comet-da / MetricX")
    return True
