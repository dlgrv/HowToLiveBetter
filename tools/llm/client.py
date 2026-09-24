#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

TIMEOUT_SEC = 300
MAX_RETRIES = 2


class LLMError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_dotenv(path: Path | None = None) -> None:
    if path is None:
        path = repo_root() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise LLMError(f"missing or empty required env: {name}")
    return val


def _temperature() -> float:
    raw = os.environ.get("HTLB_LLM_TEMPERATURE", "0.2").strip() or "0.2"
    try:
        return float(raw)
    except ValueError as e:
        raise LLMError(f"HTLB_LLM_TEMPERATURE must be a number, got {raw!r}") from e


def chat(messages: list[dict[str, str]], *, max_tokens: int = 4096) -> str:
    load_dotenv()
    base = _require_env("HTLB_LLM_BASE_URL").rstrip("/")
    model = _require_env("HTLB_LLM_MODEL")
    api_key = _require_env("HTLB_LLM_API_KEY")
    url = f"{base}/chat/completions"

    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": _temperature(),
            "top_p": 1.0,
            "max_tokens": max_tokens,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                status = resp.getcode()
                raw = resp.read().decode("utf-8")
        except (TimeoutError, urllib.error.URLError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise LLMError(f"LLM request failed after retries: {e}") from e

        if status < 200 or status >= 300:
            snippet = raw[:500] if raw else "(empty body)"
            raise LLMError(f"LLM HTTP {status}: {snippet}")

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM response is not JSON: {e}") from e

        choices = data.get("choices") or []
        if not choices:
            raise LLMError("LLM response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content is None:
            raise LLMError("LLM response missing choices[0].message.content")
        text = content if isinstance(content, str) else str(content).strip()
        if not text.strip():
            raise LLMError("LLM returned empty message content")
        return text.strip()

    raise LLMError(f"LLM request failed: {last_err}")
