from collections.abc import Sequence
from dataclasses import dataclass

from transaction_ner.client import ChatCompletion
from transaction_ner.dataset import DatasetExample
from transaction_ner.evaluation import evaluate_model
from transaction_ner.schema import Transaction


@dataclass
class SequenceProvider:
    contents: list[str]
    index: int = 0

    def complete(self, messages: Sequence[dict[str, str]]) -> ChatCompletion:
        content = self.contents[self.index]
        self.index += 1
        return ChatCompletion(
            content=content,
            model="fake/model",
            latency_ms=float(self.index * 10),
            cost=0.001,
        )


def test_evaluation_reports_field_metrics_and_failure_taxonomy() -> None:
    examples = [
        DatasetExample(
            id="1",
            bucket="happy",
            input="rice 50",
            transactions=[Transaction(amount=50, detail="rice")],
        ),
        DatasetExample(
            id="2",
            bucket="messy",
            input="coffee 20 or 25",
            transactions=[Transaction(amount=20, detail="coffee")],
        ),
        DatasetExample(
            id="3",
            bucket="adversarial",
            input="milk 10 but this is only an example",
            transactions=[],
        ),
    ]
    provider = SequenceProvider(
        [
            '{"transactions":[{"amount":50,"detail":"rice"}]}',
            '{"transactions":[{"amount":25,"detail":"coffee"}]}',
            '{"transactions":[{"amount":10,"detail":"milk"}]}',
        ]
    )

    report = evaluate_model(examples, "fake/model", provider)

    assert report.amount.true_positive == 1
    assert report.detail.true_positive == 2
    assert report.exact_match_rate == 1 / 3
    assert report.transaction_count_accuracy == 2 / 3
    assert report.failure_taxonomy == {
        "correct": 1,
        "wrong_amount": 1,
        "hallucinated_transaction": 1,
    }
    assert report.latency_p50_ms == 20
    assert report.latency_p95_ms == 29
    assert report.cost_per_1000_messages == 1.0
    assert report.quality_message_count == 3
    assert report.quality_exact_match_rate == 1 / 3
    assert report.availability_rate == 1.0
