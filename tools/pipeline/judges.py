"""Judge backends: OpenAI-compatible HTTP clients behind one interface.

The default production backend (subagent-glm) calls GLM via the z.ai
OpenAI-compatible endpoint. The z.ai API key is resolved at call time
(`resolve_api_key`) and is NEVER stored in the repo. A local-ollama backend
(Mac fallback) speaks the same protocol against localhost:11434.
"""
import json
import os
import urllib.error
import urllib.request

from . import config as _config

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"


def backend_name(root):
    """Configured default backend name from project.yaml."""
    return _config.load_config(root).get("judge", {}).get("backend", "subagent-glm")


def configured_model_id(root):
    return _config.load_config(root).get("judge", {}).get("model_id", "glm-5.3-flash")


def get_backend(name):
    """Resolve a backend class by name from the registry."""
    try:
        return _BACKENDS[name]
    except KeyError:
        raise ValueError(f"unknown judge backend {name!r}; available: {sorted(_BACKENDS)}") from None


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


class OpenAICompatClient:
    """Minimal OpenAI-compatible chat-completions client (stdlib only).

    Both z.ai (GLM) and Ollama expose this protocol, so one client serves
    both backends; only the base URL and API key differ.
    """

    def __init__(self, model_id, api_key=None, base_url=None, timeout=120):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def build_request(self, prompt, system=None, temperature=0.0, max_tokens=2048):
        """Return (url, headers, body) — pure, unit-testable."""
        if self.base_url:
            url = self.base_url
        elif self.api_key:
            url = "https://api.z.ai/api/paas/v4/chat/completions"
        else:
            url = DEFAULT_OLLAMA_URL
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return url, headers, body

    def complete(self, prompt, system=None, temperature=0.0, max_tokens=2048):
        """Send the prompt and return the assistant message text."""
        url, headers, body = self.build_request(
            prompt, system=system, temperature=temperature, max_tokens=max_tokens)
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"judge API HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"judge API unreachable: {e.reason}") from e
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"unexpected judge API response shape: {e}") from e


class SubagentGLMBackend(OpenAICompatClient):
    """GLM via z.ai OpenAI-compatible API (production default)."""

    name = "subagent-glm"


class LocalOllamaBackend(OpenAICompatClient):
    """Local model on the Mac (fallback when z.ai judge fails validation)."""

    name = "local-ollama"


_BACKENDS = {
    SubagentGLMBackend.name: SubagentGLMBackend,
    LocalOllamaBackend.name: LocalOllamaBackend,
}
