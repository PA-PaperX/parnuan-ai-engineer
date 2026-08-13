from pathlib import Path

from transaction_ner.dataset import load_dataset
from transaction_ner.parser import extract
from transaction_ner.schema import ExtractionResponse, Transaction

DATASET_PATH = Path(__file__).parents[1] / "dataset" / "examples.jsonl"


def test_empty_input_always_returns_contract() -> None:
    assert extract("").model_dump() == {"transactions": []}
    assert extract(None).model_dump() == {"transactions": []}


def test_contract_rejects_unknown_fields() -> None:
    response = ExtractionResponse.model_validate({"transactions": []})
    assert response.model_dump() == {"transactions": []}


def test_transaction_strips_detail_whitespace() -> None:
    transaction = Transaction(amount=50.0, detail=" rice ")
    assert transaction.detail == "rice"


def test_dataset_has_required_size_and_buckets() -> None:
    examples = load_dataset(DATASET_PATH)
    assert len(examples) == 80
    assert {example.bucket for example in examples} == {
        "happy",
        "messy",
        "non_transaction",
        "adversarial",
    }


def test_dataset_contains_required_demo_cases() -> None:
    examples = {example.id: example for example in load_dataset(DATASET_PATH)}
    assert examples["h001"].input is not None
    assert len(examples["h014"].transactions) == 2
    assert examples["n001"].transactions == []
    assert examples["a003"].transactions == []
