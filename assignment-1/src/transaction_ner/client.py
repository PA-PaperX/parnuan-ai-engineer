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

from .schema import ExtractionResponse

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"


class OpenRouterError(RuntimeError):
    """A safe, user-facing category for an OpenRouter request failure."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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

        structured_payload = self._build_payload(messages, structured=True)
        request = self._request(structured_payload)

        started = time.perf_counter()
        try:
            body = self._send_with_retries(request)
        except OpenRouterError as error:
            if error.status_code not in {400, 422}:
                raise
            # Some free endpoints support JSON but not JSON Schema. Keep the
            # provider and privacy policy, but relax only the output format.
            body = self._send_with_retries(
                self._request(self._build_payload(messages, structured=False))
            )

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

    def _build_payload(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        structured: bool,
    ) -> dict[str, Any]:
        """Build either strict JSON Schema or compatible JSON mode payload."""

        provider: dict[str, Any] = {"data_collection": self.data_collection}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": 0,
            "max_tokens": 256,
            "provider": provider,
        }

        if structured:
            provider["require_parameters"] = True
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "transaction_extraction",
                    "strict": True,
                    "schema": ExtractionResponse.model_json_schema(),
                },
            }
        else:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _request(self, payload: dict[str, Any]) -> Request:
        return Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

    def _send_with_retries(self, request: Request) -> str:
        """Retry transient provider failures while preserving typed errors."""

        backoff_delays = [2.0, 4.0, 8.0]
        for attempt in range(len(backoff_delays) + 1):
            try:
                return self._send(request)
            except HTTPError as error:
                if error.code in {429, 503} and attempt < len(backoff_delays):
                    time.sleep(_retry_after(error) or backoff_delays[attempt])
                    continue
                if error.code == 429:
                    raise OpenRouterError(
                        "OpenRouter rate limit reached", status_code=429
                    ) from error
                raise OpenRouterError(
                    f"OpenRouter returned HTTP {error.code}", status_code=error.code
                ) from error
            except (URLError, TimeoutError) as error:
                raise OpenRouterError("OpenRouter request failed or timed out") from error
        raise OpenRouterError("OpenRouter retry budget was exhausted")

    def _send(self, request: Request) -> str:
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8")

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


def _retry_after(error: HTTPError) -> float | None:
    """Read OpenRouter's optional Retry-After header in seconds."""

    value = error.headers.get("Retry-After")
    try:
        seconds = float(value) if value is not None else 0.0
    except ValueError:
        return None
    return seconds if seconds > 0 else None
