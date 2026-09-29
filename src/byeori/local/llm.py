"""Provider boundary for local inference; importing it never initializes AWS."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx


class ModelError(RuntimeError):
    pass


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str

    def receipt(self):
        return asdict(self) | {"text": None}


class LLMBackend(Protocol):
    model: str
    context: int
    output: int

    def generate(self, system: str, prompt: str) -> Generation: ...


class OllamaBackend:
    def __init__(self, model: str, url: str = "http://127.0.0.1:11434", *,
                 context: int = 32768, output: int = 4096, timeout: float = 600,
                 transport=None):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Ollama URL must be HTTP(S), without embedded credentials")
        if context < 2048 or output < 1 or output + 1024 >= context or timeout <= 0:
            raise ValueError("Require context >= 2048, output > 0, context > output + 1024, timeout > 0")
        self.model, self.url = model, url.rstrip("/")
        self.context, self.output, self.timeout = context, output, timeout
        self.transport = transport

    def _request(self, method, path, **kwargs):
        try:
            # Loopback services must not be redirected through inherited system proxies.
            with httpx.Client(base_url=self.url, timeout=self.timeout, trust_env=False,
                              transport=self.transport) as client:
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                value = response.json()
                if not isinstance(value, dict) or value.get("error"):
                    raise ModelError("Ollama returned an error or invalid response")
                return value
        except (httpx.HTTPError, ValueError) as exc:
            # Do not echo server bodies: they may contain paper text.
            raise ModelError(f"Ollama request failed ({type(exc).__name__}); check server, model and timeout") from exc

    def doctor(self):
        models = self._request("GET", "/api/tags").get("models", [])
        names = [item.get("name", "") for item in models]
        requested = self.model if ":" in self.model else self.model + ":latest"
        found = next((item for item in models if item.get("name") in {self.model, requested}), None)
        return {"reachable": True, "model_available": found is not None,
                "model": self.model, "installed_models": names,
                "digest": found.get("digest") if found else None}

    def generate(self, system, prompt):
        if not self.model:
            raise ModelError("Set BYEORI_LOCAL_MODEL or --model to an installed Ollama model")
        # Conservative byte budget, not a provider tokenizer. Reject rather than trim inputs.
        if len((system + prompt).encode("utf-8")) + 1024 + self.output > self.context:
            raise ModelError("Input exceeds conservative context budget; increase context or use a shorter paper. No text was truncated.")
        value = self._request("POST", "/api/chat", json={
            "model": self.model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "options": {"num_ctx": self.context, "num_predict": self.output, "temperature": 0},
        })
        text = (value.get("message") or {}).get("content", "")
        if value.get("done") is not True or value.get("done_reason") != "stop":
            raise ModelError("Model did not finish normally; incomplete output was not published")
        if not isinstance(text, str) or not text.strip():
            raise ModelError("Model returned no answer text")
        return Generation(text.strip(), value.get("model", self.model),
                          int(value.get("prompt_eval_count", 0)), int(value.get("eval_count", 0)), "stop")
