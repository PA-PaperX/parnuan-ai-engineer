"""Small, dependency-free OpenRouter HTTP client.

The rest of the application depends on this result object, not on OpenRouter's
wire format. That keeps the parser easy to test with a fake provider.
"""

import json
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"


class OpenRouterError(RuntimeError):
    """A safe, user-facing category for an OpenRouter request failure."""


@dataclass(frozen=True)
class ChatCompletion:
    """The provider response fields used by extraction and evaluation."""

    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    latency_ms: float = 0.0


class OpenRouterClient:
    """Call one OpenRouter chat model without exposing secrets to callers."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        data_collection: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("MODEL_NAME", DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds
        self.data_collection = data_collection or os.getenv(
            "OPENROUTER_DATA_COLLECTION", "deny"
        )

    def complete(self, messages: Sequence[Mapping[str, str]]) -> ChatCompletion:
        """Send a JSON-mode chat request and return normalized usage metadata."""

        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not set")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "provider": {"data_collection": self.data_collection},
        }
        request = Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        started = time.perf_counter()
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            raise OpenRouterError(f"OpenRouter returned HTTP {error.code}") from error
        except (URLError, TimeoutError) as error:
            raise OpenRouterError("OpenRouter request failed or timed out") from error

        latency_ms = (time.perf_counter() - started) * 1000
        try:
            data = json.loads(body)
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise OpenRouterError("OpenRouter returned an unexpected response") from error

        if not isinstance(content, str):
            raise OpenRouterError("OpenRouter returned non-text content")

        usage = data.get("usage") or {}
        return ChatCompletion(
            content=content,
            model=str(data.get("model") or self.model),
            prompt_tokens=_optional_int(usage.get("prompt_tokens")),
            completion_tokens=_optional_int(usage.get("completion_tokens")),
            total_tokens=_optional_int(usage.get("total_tokens")),
            cost=_optional_float(usage.get("cost")),
            latency_ms=latency_ms,
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://localhost"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "Parnuan Transaction NER"),
        }
        return headers


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_float(value: object) -> float | None:
    return value if isinstance(value, (float, int)) else None
