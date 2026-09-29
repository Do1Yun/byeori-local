"""Provider boundary for local inference; importing it never initializes AWS."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Protocol
from urllib.parse import urlparse

import httpx

# Characters per token, or tokens per character, measured against two prompts this workspace
# actually sent to qwen3:8b: a 34,628-character paper that came back as 8,567 prompt tokens
# (4.04 characters each) and a 4,180-character part holding three numeric tables that came back
# as 1,948 (2.15 each). A table's digits and separators each become their own token, so one
# ratio for all text underestimates tables by 40%, which is the direction that silently loses
# half a paper. These weights read 1.4x high on prose and 1.2x high on tables.
LETTER_CHARS_PER_TOKEN = 4.0
SPACE_CHARS_PER_TOKEN = 6.0
DIGIT_TOKENS_PER_CHAR = 1.0
PUNCTUATION_TOKENS_PER_CHAR = 2.0
RESERVE_TOKENS = 512
# A measured prompt this far below the estimate was probably cut down rather than read.
TRUNCATION_RATIO = 0.55


def estimate_tokens(text: str) -> int:
    """Tokens a local model will need for this text, erring high.

    Ollama exposes no tokenizer, and it silently truncates a prompt that does not fit num_ctx:
    one input here reported 3,617 prompt tokens at num_ctx 8192 and 1,026 at 2048, with no error
    either time. An estimate that ran low would let a note be written from part of a paper, so
    this one runs high, and higher still on the numeric text where tokenizers spend the most.
    """
    letters = digits = spaces = punctuation = wide = 0
    for character in text:
        if not character.isascii():
            wide += 1
        elif character.isalpha():
            letters += 1
        elif character.isdigit():
            digits += 1
        elif character.isspace():
            spaces += 1
        else:
            punctuation += 1
    return math.ceil(letters / LETTER_CHARS_PER_TOKEN + spaces / SPACE_CHARS_PER_TOKEN
                     + digits * DIGIT_TOKENS_PER_CHAR
                     + punctuation * PUNCTUATION_TOKENS_PER_CHAR + wide)


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

    @property
    def input_budget(self) -> int: ...

    def fits(self, system: str, prompt: str) -> bool: ...

    def generate(self, system: str, prompt: str) -> Generation: ...


class OllamaBackend:
    def __init__(self, model: str, url: str = "http://127.0.0.1:11434", *,
                 context: int = 32768, output: int = 4096, timeout: float = 600,
                 transport=None):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Ollama URL must be HTTP(S), without embedded credentials")
        if context < 2048 or output < 1 or output + 2 * RESERVE_TOKENS >= context or timeout <= 0:
            raise ValueError(f"Require context >= 2048, output > 0, context > output + "
                             f"{2 * RESERVE_TOKENS}, timeout > 0")
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

    @property
    def input_budget(self):
        """Tokens the input may use, leaving the model room to answer."""
        return self.context - self.output - RESERVE_TOKENS

    def fits(self, system, prompt):
        return estimate_tokens(system + prompt) <= self.input_budget

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
        estimated = estimate_tokens(system + prompt)
        if estimated > self.input_budget:
            raise ModelError(f"Input needs about {estimated} tokens and the budget is "
                             f"{self.input_budget} (context {self.context} less output "
                             f"{self.output} and {RESERVE_TOKENS} reserved). Nothing was "
                             "truncated; write the note in parts or raise the context.")
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
        measured = int(value.get("prompt_eval_count", 0))
        if measured and measured < estimated * TRUNCATION_RATIO:
            # The server read far less than this input holds, which is what its silent
            # truncation looks like. A note from part of a paper must not be published.
            raise ModelError(f"The model reported reading {measured} prompt tokens for an input "
                             f"estimated at {estimated}; the input may have been truncated, so "
                             "nothing was published. Lower the input or raise the context.")
        return Generation(text.strip(), value.get("model", self.model),
                          measured, int(value.get("eval_count", 0)), "stop")
