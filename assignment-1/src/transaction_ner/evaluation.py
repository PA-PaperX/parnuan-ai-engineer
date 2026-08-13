"""Offline-first evaluation metrics for transaction extraction."""

import argparse
import json
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import OpenRouterClient
from .dataset import DatasetExample, load_dataset
from .parser import ChatProvider, ExtractionOutcome, extract_with_provider
from .schema import Transaction

DEFAULT_MODELS = (
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
)


@dataclass(frozen=True)
class FieldMetrics:
    """Micro-averaged counts for one extracted field."""

    true_positive: int
    predicted: int
    expected: int

    @property
    def precision(self) -> float:
        return _ratio(self.true_positive, self.predicted)

    @property
    def recall(self) -> float:
        return _ratio(self.true_positive, self.expected)

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "true_positive": self.true_positive,
            "predicted": self.predicted,
            "expected": self.expected,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass(frozen=True)
class EvaluationRecord:
    """One result row without storing the original text."""

    example_id: str
    bucket: str
    expected: list[Transaction]
    predicted: list[Transaction]
    outcome: ExtractionOutcome


@dataclass(frozen=True)
class ModelReport:
    """All metrics needed for the assignment's comparison table."""

    model: str
    message_count: int
    amount: FieldMetrics
    detail: FieldMetrics
    exact_match_rate: float
    transaction_count_accuracy: float
    latency_p50_ms: float
    latency_p95_ms: float
    cost_per_1000_messages: float | None
    failure_taxonomy: dict[str, int]
    status_counts: dict[str, int]
    bucket_exact_match: dict[str, float]
    quality_message_count: int
    quality_amount: FieldMetrics
    quality_detail: FieldMetrics
    quality_exact_match_rate: float
    availability_rate: float


def evaluate_model(
    examples: list[DatasetExample],
    model: str,
    provider: ChatProvider | None = None,
) -> ModelReport:
    """Evaluate a model serially to keep rate-limit behavior predictable."""

    client = provider or OpenRouterClient(model=model)
    records: list[EvaluationRecord] = []
    for example in examples:
        outcome = extract_with_provider(example.input, client)
        records.append(
            EvaluationRecord(
                example_id=example.id,
                bucket=example.bucket,
                expected=example.transactions,
                predicted=outcome.response.transactions,
                outcome=outcome,
            )
        )
    return _build_report(model, records)


def _build_report(model: str, records: list[EvaluationRecord]) -> ModelReport:
    amount = _field_metrics(records, "amount")
    detail = _field_metrics(records, "detail")
    exact = [_is_exact(record.predicted, record.expected) for record in records]
    count_correct = [len(record.predicted) == len(record.expected) for record in records]
    latencies = [record.outcome.latency_ms for record in records if record.outcome.latency_ms]
    costs = [record.outcome.cost for record in records if record.outcome.cost is not None]
    quality_records = [record for record in records if record.outcome.status == "ok"]
    eligible_records = [record for record in records if record.outcome.status != "input_empty"]
    quality_exact = [
        _is_exact(record.predicted, record.expected) for record in quality_records
    ]

    bucket_totals: Counter[str] = Counter(record.bucket for record in records)
    bucket_correct: Counter[str] = Counter(
        record.bucket for record, is_exact in zip(records, exact, strict=True) if is_exact
    )
    bucket_exact = {
        bucket: _ratio(bucket_correct[bucket], total)
        for bucket, total in sorted(bucket_totals.items())
    }

    return ModelReport(
        model=model,
        message_count=len(records),
        amount=amount,
        detail=detail,
        exact_match_rate=_ratio(sum(exact), len(records)),
        transaction_count_accuracy=_ratio(sum(count_correct), len(records)),
        latency_p50_ms=_percentile(latencies, 0.50),
        latency_p95_ms=_percentile(latencies, 0.95),
        cost_per_1000_messages=(sum(costs) * 1000 / len(records)) if costs else None,
        failure_taxonomy=dict(Counter(_failure_type(record) for record in records)),
        status_counts=dict(Counter(record.outcome.status for record in records)),
        bucket_exact_match=bucket_exact,
        quality_message_count=len(quality_records),
        quality_amount=_field_metrics(quality_records, "amount"),
        quality_detail=_field_metrics(quality_records, "detail"),
        quality_exact_match_rate=_ratio(sum(quality_exact), len(quality_exact)),
        availability_rate=_ratio(len(quality_records), len(eligible_records)),
    )


def _field_metrics(records: list[EvaluationRecord], field: str) -> FieldMetrics:
    predicted: Counter[Any] = Counter()
    expected: Counter[Any] = Counter()
    for record in records:
        predicted.update(_field_values(record.predicted, field))
        expected.update(_field_values(record.expected, field))
    true_positive = sum((predicted & expected).values())
    return FieldMetrics(true_positive, sum(predicted.values()), sum(expected.values()))


def _field_values(transactions: list[Transaction], field: str) -> list[Any]:
    if field == "amount":
        return [transaction.amount for transaction in transactions]
    return [_normalize_detail(transaction.detail) for transaction in transactions]


def _is_exact(predicted: list[Transaction], expected: list[Transaction]) -> bool:
    return [
        (transaction.amount, _normalize_detail(transaction.detail))
        for transaction in predicted
    ] == [
        (transaction.amount, _normalize_detail(transaction.detail))
        for transaction in expected
    ]


def _failure_type(record: EvaluationRecord) -> str:
    if _is_exact(record.predicted, record.expected):
        return "correct"
    if record.outcome.status != "ok":
        return record.outcome.status
    if not record.predicted and record.expected:
        return "missed_transaction"
    if record.predicted and not record.expected:
        return "hallucinated_transaction"
    if len(record.predicted) < len(record.expected):
        return "merged_transactions"
    if len(record.predicted) > len(record.expected):
        return "extra_transactions"

    amount_matches = _field_metrics(
        [record], "amount"
    ).true_positive == len(record.expected)
    detail_matches = _field_metrics(
        [record], "detail"
    ).true_positive == len(record.expected)
    if amount_matches:
        return "wrong_or_truncated_detail"
    if detail_matches:
        return "wrong_amount"
    return "wrong_amount_and_detail"


def _normalize_detail(detail: str) -> str:
    return " ".join(detail.split()).casefold()


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _get_git_commit() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
                cwd=Path(__file__).parents[2],
            )
            .strip()
        )
    except Exception:
        return "unknown"


def report_to_dict(report: ModelReport) -> dict[str, Any]:
    return {
        "model": report.model,
        "message_count": report.message_count,
        "amount": report.amount.as_dict(),
        "detail": report.detail.as_dict(),
        "exact_match_rate": report.exact_match_rate,
        "transaction_count_accuracy": report.transaction_count_accuracy,
        "latency_p50_ms": report.latency_p50_ms,
        "latency_p95_ms": report.latency_p95_ms,
        "cost_per_1000_messages": report.cost_per_1000_messages,
        "failure_taxonomy": report.failure_taxonomy,
        "status_counts": report.status_counts,
        "bucket_exact_match": report.bucket_exact_match,
        "quality_message_count": report.quality_message_count,
        "quality_amount": report.quality_amount.as_dict(),
        "quality_detail": report.quality_detail.as_dict(),
        "quality_exact_match_rate": report.quality_exact_match_rate,
        "availability_rate": report.availability_rate,
    }


def render_report(reports: list[ModelReport]) -> str:
    """Render a compact human-readable report without raw transaction text."""

    lines = [
        "| Model | Amount F1 | Detail F1 | Exact match | Count accuracy | p50/p95 ms | $/1k |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for report in reports:
        cost = (
            "n/a"
            if report.cost_per_1000_messages is None
            else f"${report.cost_per_1000_messages:.6f}"
        )
        lines.append(
            f"| {report.model} | {report.amount.f1:.3f} | {report.detail.f1:.3f} | "
            f"{report.exact_match_rate:.3f} | {report.transaction_count_accuracy:.3f} | "
            f"{report.latency_p50_ms:.1f}/{report.latency_p95_ms:.1f} | {cost} |"
        )
    for report in reports:
        lines.append(f"\n### {report.model}")
        lines.append(f"Status counts: `{json.dumps(report.status_counts, ensure_ascii=False)}`")
        lines.append(
            f"Failure taxonomy: `{json.dumps(report.failure_taxonomy, ensure_ascii=False)}`"
        )
        lines.append(
            "Exact match by bucket: "
            f"`{json.dumps(report.bucket_exact_match, ensure_ascii=False)}`"
        )
        lines.append(
            "Successful-response quality: "
            f"{report.quality_message_count}/{report.message_count} messages, "
            f"amount F1={report.quality_amount.f1:.3f}, "
            f"detail F1={report.quality_detail.f1:.3f}, "
            f"exact match={report.quality_exact_match_rate:.3f}"
        )
        lines.append(f"Availability excluding empty input: {report.availability_rate:.3f}")
    return "\n".join(lines)


def main() -> None:
    default_models = os.getenv("EVAL_MODELS", ",".join(DEFAULT_MODELS))
    parser = argparse.ArgumentParser(description="Evaluate OpenRouter NER models.")
    parser.add_argument("--data", default="dataset/examples.jsonl")
    parser.add_argument("--models", default=default_models, help="Comma-separated model IDs.")
    parser.add_argument("--limit", type=int, help="Evaluate only the first N examples.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--output", help="Save JSON evaluation report to file path.")
    parser.add_argument("--output-md", help="Save Markdown evaluation report to file path.")
    args = parser.parse_args()

    examples = load_dataset(Path(args.data))
    if args.limit is not None:
        examples = examples[: args.limit]
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    reports = [evaluate_model(examples, model) for model in models]

    total_rate_limits = sum(
        report.status_counts.get("rate_limited", 0) for report in reports
    )
    metadata = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset_size": len(examples),
        "models": models,
        "rate_limit_count": total_rate_limits,
        "git_commit": _get_git_commit(),
    }

    report_payload = {
        "metadata": metadata,
        "reports": [report_to_dict(report) for report in reports],
    }

    markdown_text = render_report(reports)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Evaluation JSON report saved to {out_path}")

    if args.output_md:
        out_md_path = Path(args.output_md)
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        md_header = (
            f"# Evaluation Report Evidence\n\n"
            f"- **Timestamp**: `{metadata['timestamp']}`\n"
            f"- **Git Commit**: `{metadata['git_commit']}`\n"
            f"- **Dataset Size**: {metadata['dataset_size']} examples\n"
            f"- **Rate Limit Count**: {metadata['rate_limit_count']}\n\n"
        )
        out_md_path.write_text(md_header + markdown_text + "\n", encoding="utf-8")
        print(f"Evaluation Markdown report saved to {out_md_path}")

    if args.json:
        print(json.dumps(report_payload, ensure_ascii=False, indent=2))
    elif not args.output and not args.output_md:
        print(markdown_text)


if __name__ == "__main__":
    main()
