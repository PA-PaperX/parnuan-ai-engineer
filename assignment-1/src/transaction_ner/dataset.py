"""Load and sanity-check the labeled JSONL evaluation dataset."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .schema import Transaction

Bucket = Literal["happy", "messy", "non_transaction", "adversarial"]


class DatasetExample(BaseModel):
    """One labeled input used by the evaluator."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1)
    bucket: Bucket
    input: str | None
    transactions: list[Transaction] = Field(default_factory=list)


def load_dataset(path: str | Path) -> list[DatasetExample]:
    """Read JSONL and fail early when a label violates the output contract."""

    examples: list[DatasetExample] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            example = DatasetExample.model_validate(json.loads(line))
        except Exception as error:
            raise ValueError(f"Invalid dataset row at line {line_number}: {error}") from error
        if example.id in seen_ids:
            raise ValueError(f"Duplicate dataset id: {example.id}")
        seen_ids.add(example.id)
        examples.append(example)

    if len(examples) < 50:
        raise ValueError(f"Dataset needs at least 50 examples, found {len(examples)}")

    buckets = {example.bucket for example in examples}
    required_buckets = {"happy", "messy", "non_transaction", "adversarial"}
    missing = required_buckets - buckets
    if missing:
        raise ValueError(f"Dataset is missing buckets: {sorted(missing)}")
    return examples


def main() -> None:
    path = Path(__file__).parents[2] / "dataset" / "examples.jsonl"
    examples = load_dataset(path)
    counts: dict[str, int] = {}
    for example in examples:
        counts[example.bucket] = counts.get(example.bucket, 0) + 1
    print(f"validated {len(examples)} examples: {counts}")


if __name__ == "__main__":
    main()

