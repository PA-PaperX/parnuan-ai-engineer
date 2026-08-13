"""Provider-independent input, output parsing, and graceful fallback."""

import json
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

from .client import ChatCompletion, OpenRouterError
from .prompts import build_messages
from .schema import ExtractionResponse, empty_response

MAX_INPUT_CHARS = 4_000
ExtractionStatus = Literal[
    "ok",
    "input_empty",
    "input_too_large",
    "provider_error",
    "rate_limited",
    "invalid_model_output",
    "ungrounded_model_output",
]


class ChatProvider(Protocol):
    """The only provider behavior needed by the parser."""

    def complete(self, messages: Sequence[dict[str, str]]) -> ChatCompletion:
        ...


@dataclass(frozen=True)
class ExtractionOutcome:
    """Output plus non-sensitive metadata used by the evaluator."""

    response: ExtractionResponse
    status: ExtractionStatus
    latency_ms: float = 0.0
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None


def parse_model_output(content: str) -> ExtractionResponse:
    """Parse JSON or a fenced JSON response and validate the public contract."""

    if not isinstance(content, str) or not content.strip():
        raise ValueError("model output is empty")

    candidate = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    payload = json.loads(candidate)
    return ExtractionResponse.model_validate(payload)


def validate_grounding(text: str, response: ExtractionResponse) -> ExtractionResponse:
    """Reject model transactions whose amount or detail is not grounded in input."""

    input_amounts = _amounts_in_text(text)
    normalized_input = _normalize_for_match(text)
    for transaction in response.transactions:
        if Decimal(str(transaction.amount)) not in input_amounts:
            raise ValueError("model amount was not found in input")
        if _normalize_for_match(transaction.detail) not in normalized_input:
            raise ValueError("model detail was not found in input")
    return response


def extract_with_provider(text: str | None, provider: ChatProvider) -> ExtractionOutcome:
    """Call a provider only for bounded input and turn every failure into empty output."""

    if not isinstance(text, str) or not text.strip():
        return ExtractionOutcome(empty_response(), "input_empty")
    if len(text) > MAX_INPUT_CHARS:
        return ExtractionOutcome(empty_response(), "input_too_large")

    started = time.perf_counter()
    try:
        completion = provider.complete(build_messages(text))
    except OpenRouterError as error:
        status: ExtractionStatus = (
            "rate_limited" if error.status_code == 429 else "provider_error"
        )
        return ExtractionOutcome(
            empty_response(),
            status,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception:
        return ExtractionOutcome(
            empty_response(),
            "provider_error",
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    latency_ms = completion.latency_ms or (time.perf_counter() - started) * 1000
    try:
        response = parse_model_output(completion.content)
    except (TypeError, ValueError, json.JSONDecodeError):
        return ExtractionOutcome(
            empty_response(),
            "invalid_model_output",
            latency_ms=latency_ms,
            model=completion.model,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            total_tokens=completion.total_tokens,
            cost=completion.cost,
        )

    try:
        response = validate_grounding(text, response)
    except ValueError:
        return ExtractionOutcome(
            empty_response(),
            "ungrounded_model_output",
            latency_ms=latency_ms,
            model=completion.model,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            total_tokens=completion.total_tokens,
            cost=completion.cost,
        )

    return ExtractionOutcome(
        response,
        "ok",
        latency_ms=latency_ms,
        model=completion.model,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        total_tokens=completion.total_tokens,
        cost=completion.cost,
    )


def extract(text: str | None, provider: ChatProvider | None = None) -> ExtractionResponse:
    """Return a valid response for every input; provider is optional for offline use."""

    if provider is None:
        return empty_response()
    return extract_with_provider(text, provider).response


def _amounts_in_text(text: str) -> set[Decimal]:
    values: set[Decimal] = set()
    for token in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", text):
        try:
            values.add(Decimal(token.replace(",", "")))
        except InvalidOperation:
            continue
    return values


def _normalize_for_match(value: str) -> str:
    return "".join(value.split()).casefold()

