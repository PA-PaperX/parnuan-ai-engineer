from collections.abc import Sequence

from transaction_ner.client import ChatCompletion
from transaction_ner.web import build_extraction_payload, render_page


class FakeProvider:
    def complete(self, messages: Sequence[dict[str, str]]) -> ChatCompletion:
        return ChatCompletion(
            content='{"transactions":[{"amount":50,"detail":"ข้าวมันไก่"}]}',
            model="fake/model",
            latency_ms=12.3,
        )


def test_web_payload_uses_the_same_extraction_core() -> None:
    response = build_extraction_payload({"text": "ข้าวมันไก่ 50"}, FakeProvider())

    assert response["status"] == "ok"
    assert response["model"] == "fake/model"
    assert response["transactions"] == [{"amount": 50.0, "detail": "ข้าวมันไก่"}]


def test_offline_web_payload_never_calls_a_provider() -> None:
    response = build_extraction_payload({"text": "ข้าวมันไก่ 50"}, None, "offline")

    assert response["status"] == "offline"
    assert response["transactions"] == []


def test_page_is_readable_and_does_not_echo_user_input() -> None:
    page = render_page("google/example:free")

    assert "สรุปรายการใช้จ่าย" in page
    assert "เดโมทำงานบนเครื่องนี้" in page
    assert "google/example:free" in page
    assert "textContent" in page
