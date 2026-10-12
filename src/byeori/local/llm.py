"""Provider boundary for local inference; importing it never initializes AWS."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Protocol
from urllib.parse import urlparse

import httpx

from .locking import inference_lock, runtime_path, try_lock

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
    error_code = "model_error"
    retryable = False


class UnsupportedThinking(ModelError):
    error_code = "unsupported_thinking"


class ModelTimeout(ModelError):
    error_code = "outcome_unknown"


class OutputTruncated(ModelError):
    """The model used every output token it was allowed: what it wrote is incomplete."""
    error_code = "output_truncated"


class AbnormalStop(ModelError):
    error_code = "abnormal_stop"


class RecoveryPending(ModelError):
    """An earlier request on this endpoint may still be computing; nothing was sent."""
    error_code = "recovery_pending"


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    metadata: dict = field(default_factory=dict)

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
                 transport=None, allow_remote=False, truncation_ratio: float = TRUNCATION_RATIO):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Ollama URL must be HTTP(S), without embedded credentials")
        if parsed.hostname not in {"127.0.0.1", "::1", "localhost"} and not allow_remote:
            raise ValueError("Non-loopback Ollama requires explicit --allow-remote-ollama")
        if context < 2048 or output < 1 or output + 2 * RESERVE_TOKENS >= context or timeout <= 0:
            raise ValueError(f"Require context >= 2048, output > 0, context > output + "
                             f"{2 * RESERVE_TOKENS}, timeout > 0")
        if not 0 < truncation_ratio <= 1:
            raise ValueError("Truncation ratio must be between 0 and 1")
        self.model, self.url = model, url.rstrip("/")
        self.context, self.output, self.timeout = context, output, timeout
        self.transport = transport
        self.truncation_ratio = truncation_ratio
        self.endpoint_policy = "loopback" if parsed.hostname in {"127.0.0.1", "::1", "localhost"} else "explicit_remote_endpoint"

    @property
    def blocked_path(self):
        return runtime_path(self.url).with_suffix(".blocked.json")

    @property
    def inflight_path(self):
        return runtime_path(self.url).with_suffix(".inflight.json")

    def recovery_pending(self):
        """Whether a person must confirm the server is idle before the next call.

        A timeout marker always blocks. An in-flight marker blocks only when no process holds the
        endpoint lock: beside a held lock it is a call that is still running, not an abandoned one.
        """
        if self.blocked_path.exists():
            return True
        if not self.inflight_path.exists():
            return False
        with try_lock(runtime_path(self.url)) as acquired:
            return acquired and self.inflight_path.exists()

    def fingerprint(self):
        """What a stored digest depends on in this backend: the exact model and its budget."""
        details = self.doctor()
        if not details["model_available"]:
            raise ModelError("Requested model is not installed")
        return {"model": self.model, "model_digest": details["digest"],
                "template_sha256": details["template_sha256"],
                "server_version": details["server_version"],
                "context": self.context, "output": self.output}

    def recover_runtime(self, *, acknowledge=False):
        if not acknowledge:
            raise ValueError("Confirm the server's previous request has ended with --acknowledge-idle")
        with inference_lock(self.url):
            import uuid
            for path in (self.blocked_path, self.inflight_path):
                if path.exists():
                    path.rename(path.with_suffix(f".resolved-{uuid.uuid4().hex}.json"))
        return {"recovery_pending": False, "acknowledged_server_idle": True}

    def _request(self, method, path, **kwargs):
        try:
            # Loopback services must not be redirected through inherited system proxies.
            with httpx.Client(base_url=self.url, timeout=self.timeout, trust_env=False,
                              transport=self.transport) as client:
                response = client.request(method, path, **kwargs)
                if response.status_code == 400:
                    try:
                        explanation = str(response.json().get("error", "")).lower()
                    except ValueError:
                        explanation = ""
                    if (("think" in explanation) and
                            any(word in explanation for word in ("not support", "unsupported", "unknown"))):
                        raise UnsupportedThinking("Model explicitly rejected the thinking option")
                response.raise_for_status()
                value = response.json()
                if not isinstance(value, dict) or value.get("error"):
                    raise ModelError("Ollama returned an error or invalid response")
                return value
        except httpx.TimeoutException as exc:
            if method == "POST" and path == "/api/chat":
                self.blocked_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                self.blocked_path.write_text(json.dumps({"reason": "outcome_unknown", "model": self.model}))
            raise ModelTimeout("Ollama request timed out; execution outcome is unknown") from exc
        except (httpx.HTTPError, ValueError) as exc:
            # Do not echo server bodies: they may contain paper text.
            raise ModelError(f"Ollama request failed ({type(exc).__name__}); check server, model and timeout") from exc

    @property
    def input_budget(self):
        """Tokens the input may use, leaving the model room to answer."""
        return self.context - self.output - RESERVE_TOKENS

    def fits(self, system, prompt):
        return estimate_tokens(system + prompt) <= self.input_budget

    def _chat(self, body):
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        self.inflight_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Persist before dispatch: SIGKILL releases the OS lock but does not prove that the
        # server stopped computing. A successor must see this marker and require recovery.
        with self.inflight_path.open("x") as stream:
            stream.write(json.dumps({"model": self.model, "payload_sha256": hashlib.sha256(payload).hexdigest()}))
            stream.flush()
            import os
            os.fsync(stream.fileno())
        try:
            response = self._request("POST", "/api/chat", content=payload,
                                     headers={"Content-Type": "application/json"})
        except UnsupportedThinking:
            self.inflight_path.unlink()
            raise
        except ModelError as exc:
            if isinstance(exc.__cause__, httpx.HTTPStatusError):
                self.inflight_path.unlink()
            raise
        else:
            self.inflight_path.unlink()
            return response, payload

    def doctor(self):
        models = self._request("GET", "/api/tags").get("models", [])
        names = [item.get("name", "") for item in models]
        requested = self.model if ":" in self.model else self.model + ":latest"
        found = next((item for item in models if item.get("name") in {self.model, requested}), None)
        show = self._request("POST", "/api/show", json={"model": self.model}) if found else {}
        remote = any(item.get(key) for item in (found or {}, show)
                     for key in ("remote_host", "remote_model"))
        remote = remote or any(part == "cloud" for part in self.model.lower().replace(":", "-").split("-"))
        version = self._request("GET", "/api/version").get("version")
        return {"reachable": True, "model_available": found is not None,
                "model": self.model, "installed_models": names,
                "digest": found.get("digest") if found else None,
                "model_locality": "remote" if remote else ("local" if found else "unknown"),
                "endpoint_policy": self.endpoint_policy, "cloud_disable_verification": "unverified",
                "server_version": version, "capabilities": show.get("capabilities") or [],
                "runtime_lock_path": str(runtime_path(self.url)),
                "template_sha256": hashlib.sha256(str(show.get("template", "")).encode()).hexdigest(),
                "recovery_pending": self.recovery_pending()}

    def generate(self, system, prompt, *, think=None, response_format=None, num_predict=None):
        with inference_lock(self.url):
            # Holding the lock, any marker left here belongs to a process that is gone.
            if self.blocked_path.exists() or self.inflight_path.exists():
                raise RecoveryPending("Endpoint recovery_pending after an unfinished request; "
                                      "confirm the server is idle before retrying")
            return self._generate(system, prompt, think=think, response_format=response_format,
                                  num_predict=num_predict)

    def _generate(self, system, prompt, *, think=None, response_format=None, num_predict=None):
        if not self.model:
            raise ModelError("Set BYEORI_LOCAL_MODEL or --model to an installed Ollama model")
        output = self.output if num_predict is None else int(num_predict)
        if output < 1:
            raise ValueError("num_predict must be positive")
        budget = self.context - output - RESERVE_TOKENS
        estimated = estimate_tokens(system + prompt)
        if estimated > budget:
            raise ModelError(f"Input needs about {estimated} tokens and the budget is "
                             f"{budget} (context {self.context} less output "
                             f"{output} and {RESERVE_TOKENS} reserved). Nothing was "
                             "truncated; write the note in parts or raise the context.")
        details = self.doctor()
        if not details["model_available"]:
            raise ModelError("Requested model is not installed")
        if details["model_locality"] != "local":
            raise ModelError("Remote/cloud model refused by local-only inference policy")
        body = {
            "model": self.model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "options": {"num_ctx": self.context, "num_predict": output, "temperature": 0},
        }
        if think is not None:
            body["think"] = think
        if response_format is not None:
            if response_format != "json" and not isinstance(response_format, dict):
                raise ValueError("Response format must be 'json' or a JSON schema object")
            body["format"] = response_format
        try:
            value, payload = self._chat(body)
        except UnsupportedThinking:
            if think is None:
                raise
            # A model with no thinking to turn off is not a reason to refuse the call.
            body.pop("think", None)
            value, payload = self._chat(body)
        text = (value.get("message") or {}).get("content", "")
        if value.get("done") is not True:
            raise AbnormalStop("Model did not finish normally (no done flag); incomplete output "
                               "was not published")
        if value.get("done_reason") == "length":
            raise OutputTruncated(f"Model did not finish normally: it reached the {output}-token "
                                  "output limit; incomplete output was not published")
        if value.get("done_reason") != "stop":
            raise AbnormalStop(f"Model did not finish normally (done_reason "
                               f"{str(value.get('done_reason'))[:40]!r}); incomplete output "
                               "was not published")
        if not isinstance(text, str) or not text.strip():
            raise ModelError("Model returned no answer text")
        measured = int(value.get("prompt_eval_count", 0))
        if measured and measured < estimated * self.truncation_ratio:
            # The server read far less than this input holds, which is what its silent
            # truncation looks like. A note from part of a paper must not be published.
            raise ModelError(f"The model reported reading {measured} prompt tokens for an input "
                             f"estimated at {estimated}; the input may have been truncated, so "
                             "nothing was published. Lower the input or raise the context.")
        return Generation(text.strip(), value.get("model", self.model),
                          measured, int(value.get("eval_count", 0)), "stop",
                          {"model_digest": details["digest"], "server_version": details["server_version"],
                           "template_sha256": details["template_sha256"],
                           "endpoint_policy": self.endpoint_policy,
                           "payload_sha256": hashlib.sha256(payload).hexdigest(),
                           "think": body.get("think"), "input_estimate": estimated,
                           "done_reason": value.get("done_reason"), "num_predict": output,
                           "truncation_ratio": self.truncation_ratio,
                           "token_accounting": "reported" if measured else "unverified"})
