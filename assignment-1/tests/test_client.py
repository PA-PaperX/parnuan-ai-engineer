import json
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

from transaction_ner.client import OpenRouterClient


def test_structured_payload_uses_schema_and_requires_parameters() -> None:
    client = OpenRouterClient(api_key="test-key", model="fake/model")

    payload = client._build_payload([], structured=True)

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["provider"]["require_parameters"] is True
    assert payload["provider"]["data_collection"] == "deny"
    assert payload["max_tokens"] == 256


def test_json_mode_payload_is_available_for_compatible_fallbacks() -> None:
    client = OpenRouterClient(api_key="test-key", model="fake/model")

    payload = client._build_payload([], structured=False)

    assert payload["response_format"] == {"type": "json_object"}
    assert "require_parameters" not in payload["provider"]


def test_client_falls_back_from_schema_to_json_mode(monkeypatch) -> None:
    client = OpenRouterClient(api_key="test-key", model="fake/model")
    responses = [
        HTTPError("https://example.test", 400, "unsupported", Message(), None),
        json.dumps(
            {
                "model": "fake/model",
                "choices": [{"message": {"content": '{"transactions": []}'}}],
                "usage": {},
            }
        ),
    ]
    payloads: list[dict] = []

    def fake_send(request) -> str:
        payloads.append(json.loads(request.data.decode("utf-8")))
        response = responses.pop(0)
        if isinstance(response, HTTPError):
            raise response
        return response

    monkeypatch.setattr(client, "_send", fake_send)
    completion = client.complete([])

    assert completion.content == '{"transactions": []}'
    assert payloads[0]["response_format"]["type"] == "json_schema"
    assert payloads[1]["response_format"] == {"type": "json_object"}


def test_retry_after_header_controls_backoff(monkeypatch) -> None:
    client = OpenRouterClient(api_key="test-key", model="fake/model")
    calls = 0
    delays: list[float] = []

    limited_error = HTTPError(
        "https://example.test",
        429,
        "limited",
        Message(),
        None,
    )
    limited_error.headers["Retry-After"] = "7"

    def fake_send_with_header(request: Request) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise limited_error
        return "ok"

    monkeypatch.setattr(client, "_send", fake_send_with_header)
    monkeypatch.setattr("transaction_ner.client.time.sleep", delays.append)

    assert client._send_with_retries(Request("https://example.test")) == "ok"
    assert delays == [7.0]
