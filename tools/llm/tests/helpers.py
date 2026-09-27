"""Shared CLI helpers for llm/validate tests."""

import os
import subprocess
import sys
import tempfile

from tools.llm.verify_issues import parse_verify_json
from tools.test_paths import REPO_ROOT


def run_cli(args, *, cwd=REPO_ROOT, env=None, timeout=30):
    """Run argv list; returns CompletedProcess (text, capture_output)."""
    run_env = os.environ.copy()
    run_env.setdefault("PYTHONPATH", cwd)
    if env:
        run_env.update(env)
    return subprocess.run(
        args,
        cwd=cwd,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_verify_json(text, *, lang="ru", chapter="01", cwd=REPO_ROOT):
    """Write text to a temp file, run tools/verify.py --json, return parsed dict."""
    fd, path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        proc = run_cli(
            [
                sys.executable,
                os.path.join(cwd, "tools", "verify.py"),
                str(chapter),
                "--lang",
                lang,
                "--file",
                path,
                "--json",
            ],
            cwd=cwd,
        )
        return parse_verify_json(proc.stdout), proc
    finally:
        os.unlink(path)
