"""Thin HTTP client for self-hosted Laya (Jev-compatible /v1/systemone).

Server down → skip (exit 0), same habit as LanguageTool. Always pin
``model=multilingual`` — never fall back to English.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tools.llm.client import load_dotenv

DEFAULT_BASE_URL = "http://127.0.0.1:8090"
DEFAULT_MODEL = "multilingual"
DEFAULT_TIMEOUT = 30.0
# Current laya[serve] exposes /health; older laya-serve used /healthz.
_HEALTH_PATHS = ("/health", "/healthz")


class LayaError(Exception):
    pass


def base_url_from_env() -> str:
    load_dotenv()
    raw = os.environ.get("HTLB_LAYA_BASE_URL", "").strip()
    if raw:
        return raw.rstrip("/")
    port = os.environ.get("HTLB_LAYA_PORT", "8090").strip() or "8090"
    return f"http://127.0.0.1:{port}"


def model_from_env() -> str:
    load_dotenv()
    model = os.environ.get("HTLB_LAYA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if model != "multilingual":
        raise LayaError(f"HTLB_LAYA_MODEL must be multilingual (got {model!r})")
    return model


def healthz(
    base_url: str | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    """GET /health (or /healthz). Return JSON body, or None if unreachable."""
    load_dotenv()
    root = (base_url or base_url_from_env()).rstrip("/")
    last_err: Exception | None = None
    for path in _HEALTH_PATHS:
        url = root + path
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
                if not raw.strip():
                    return {"ok": True, "path": path}
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    return {"ok": True, "path": path, "raw": raw[:200]}
                if isinstance(data, dict):
                    data.setdefault("path", path)
                    return data
                return {"ok": True, "path": path, "body": data}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_err = e
            continue
    _ = last_err
    return None


def systemone(
    state: str | dict[str, Any],
    questions: dict[str, Any],
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    """POST /v1/systemone. Return parsed JSON, or None if unreachable."""
    load_dotenv()
    pinned = model or model_from_env()
    if pinned != "multilingual":
        raise LayaError(f"model must be multilingual (got {pinned!r})")
    root = (base_url or base_url_from_env()).rstrip("/")
    url = root + "/v1/systemone"
    body = json.dumps(
        {"state": state, "model": pinned, "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ):
        return None


def _demo_questions() -> dict[str, Any]:
    return {
        "noun_or_demonstrative": {
            "type": "choice",
            "instructions": (
                "In this Russian fragment, is the flagged word the noun "
                "«данные» (data) or the demonstrative «эти/этих»?"
            ),
            "criteria": {
                "data_noun": "Noun meaning data / datasets / statistics",
                "demonstrative": "Demonstrative these / those",
                "unclear": "Cannot tell from the fragment",
            },
        }
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Laya System-1 probe (skip if server down)")
    ap.add_argument("--base-url", default=None, help="Override HTLB_LAYA_BASE_URL")
    ap.add_argument(
        "--state",
        default="Согласно этим данным риск ниже.",
        help="State text for one /v1/systemone call",
    )
    ap.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Optional JSON fixture with state + questions (+ expected)",
    )
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = ap.parse_args(argv)

    base = args.base_url or base_url_from_env()
    health = healthz(base, timeout=args.timeout)
    if health is None:
        print("laya: skip (server_down)", file=sys.stderr)
        return 0

    print(f"laya: health ok via {health.get('path', '?')}")

    state: str | dict[str, Any] = args.state
    questions = _demo_questions()
    if args.fixture is not None:
        payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        state = payload["state"]
        questions = payload["questions"]

    result = systemone(state, questions, base_url=base, timeout=args.timeout)
    if result is None:
        print("laya: skip (systemone unreachable)", file=sys.stderr)
        return 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
