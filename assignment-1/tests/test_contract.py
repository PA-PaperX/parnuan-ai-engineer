from transaction_ner.parser import extract
from transaction_ner.schema import ExtractionResponse, Transaction


def test_empty_input_always_returns_contract() -> None:
    assert extract("").model_dump() == {"transactions": []}
    assert extract(None).model_dump() == {"transactions": []}


def test_contract_rejects_unknown_fields() -> None:
    response = ExtractionResponse.model_validate({"transactions": []})
    assert response.model_dump() == {"transactions": []}


def test_transaction_strips_detail_whitespace() -> None:
    transaction = Transaction(amount=50.0, detail=" ข้าวมันไก่ ")
    assert transaction.detail == "ข้าวมันไก่"

