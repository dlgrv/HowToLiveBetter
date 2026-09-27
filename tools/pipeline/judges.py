"""Judge backend names and z.ai / Ollama URL policy.

HTTP lives in ``tools.llm.client.chat``. This module only picks the endpoint
and API key: z.ai when a key is present, local Ollama otherwise.
"""

import os

from tools.llm.client import chat

ZAI_BASE = "https://api.z.ai/api/paas/v4"
OLLAMA_BASE = "http://127.0.0.1:11434/v1"

_BACKENDS = frozenset({"subagent-glm", "local-ollama"})


def get_backend(name):
    """Validate a backend name. Returns the name so callers can store it."""
    if name not in _BACKENDS:
        raise ValueError(f"unknown judge backend {name!r}; available: {sorted(_BACKENDS)}")
    return name


def resolve_api_key(env=None):
    """Find a z.ai API key in the environment without logging it.

    Accepted variable names, in order: ZAI_API_KEY, Z_AI_API_KEY,
    ZHIPUAI_API_KEY. Returns None when absent (caller decides policy).
    """
    env = env if env is not None else os.environ
    for var in ("ZAI_API_KEY", "Z_AI_API_KEY", "ZHIPUAI_API_KEY"):
        if env.get(var):
            return env[var]
    return None


def endpoint(api_key=None, base_url=None):
    if base_url:
        return base_url
    if api_key:
        return ZAI_BASE
    return OLLAMA_BASE


def complete(
    prompt,
    *,
    model_id,
    api_key=None,
    base_url=None,
    system=None,
    temperature=0.0,
    max_tokens=2048,
    timeout=120,
):
    """Send a judge prompt through the shared LLM client."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return chat(
        messages,
        max_tokens=max_tokens,
        base_url=endpoint(api_key, base_url),
        model=model_id,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout,
    )
